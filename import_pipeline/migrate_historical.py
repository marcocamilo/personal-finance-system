"""
Migrate historical transaction data from CSV to database (SQLite)
"""

import hashlib
from datetime import datetime

import pandas as pd

from database.db import db
from import_pipeline.exchange_rates import exchange_rate_fetcher


def generate_uuid(row):
    """Generate UUID from transaction data"""
    unique_string = f"{row['DATE']}{row['DESCRIPTION']}{row['AMOUNT']}"
    return hashlib.md5(unique_string.encode()).hexdigest()


def parse_date(date_str: str) -> datetime:
    """Parse date from DD.MM.YYYY format"""
    return datetime.strptime(date_str.strip(), "%d.%m.%Y")


def parse_amount(amount_str: str) -> float:
    """Parse amount from European format (e.g., '1.234,56 €')"""
    amount_str = amount_str.replace("€", "").strip()
    amount_str = amount_str.replace(".", "").replace(",", ".")
    return float(amount_str)


def migrate_historical_data(csv_path: str):
    """Migrate historical transaction data from CSV"""
    print("=" * 60)
    print("📥 MIGRATING HISTORICAL DATA")
    print("=" * 60)

    print(f"\n📖 Reading CSV from: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"✅ Loaded {len(df)} transactions")

    print("\n📅 Parsing dates...")
    df["date_parsed"] = df["DATE"].apply(parse_date)

    print("💰 Parsing amounts...")
    df["amount_parsed"] = df["AMOUNT"].apply(parse_amount)

    print("🔑 Generating UUIDs...")
    df["uuid"] = df.apply(generate_uuid, axis=1)

    duplicates = df[df.duplicated(subset=["uuid"], keep=False)]
    if len(duplicates) > 0:
        print(
            f"⚠️  Found {len(duplicates)} duplicate transactions (will keep first occurrence)"
        )
        df = df.drop_duplicates(subset=["uuid"], keep="first")

    print("\n🏦 Identifying Quorum transactions...")
    df["is_quorum"] = df["SUBCATEGORY"] == "Quorum"
    quorum_count = df["is_quorum"].sum()
    print(f"   Found {quorum_count} Quorum transactions")

    print("\n📋 Mapping categories...")
    category_map = get_category_mappings()

    df = df.merge(
        category_map, left_on="SUBCATEGORY", right_on="subcategory", how="left"
    )

    print("\n🔧 Handling unmapped categories...")
    unmapped = df[df["budget_type"].isna()]
    if len(unmapped) > 0:
        print(f"⚠️  Found {len(unmapped)} unmapped transactions")
        print("   Setting defaults...")

    df.loc[df["is_quorum"] & df["budget_type"].isna(), "budget_type"] = "Additional"
    df.loc[df["is_quorum"] & df["category"].isna(), "category"] = "Quorum"

    df.loc[~df["is_quorum"] & df["budget_type"].isna(), "budget_type"] = "Unexpected"
    df.loc[~df["is_quorum"] & df["category"].isna(), "category"] = "Unexpected"

    remaining_nan = df["budget_type"].isna().sum()
    if remaining_nan > 0:
        print(f"❌ ERROR: Still have {remaining_nan} NaN values in budget_type!")
        print("   This should not happen. Stopping migration.")
        return
    else:
        print("✅ All budget_type values are valid")

    print("\n💱 Processing currency...")
    non_quorum = df[~df["is_quorum"]]
    unique_dates = non_quorum["date_parsed"].unique()

    if len(unique_dates) > 0:
        print(f"   Fetching exchange rates for {len(unique_dates)} unique dates...")
        rates = exchange_rate_fetcher.fetch_bulk(unique_dates)

        df["exchange_rate"] = df.apply(
            lambda row: rates.get(row["date_parsed"].strftime("%Y-%m-%d"))
            if not row["is_quorum"]
            else None,
            axis=1,
        )
    else:
        df["exchange_rate"] = None

    df["original_currency"] = df["is_quorum"].map({True: "USD", False: "EUR"})
    df["original_amount"] = df["amount_parsed"]

    df["amount_usd"] = df["amount_parsed"]

    df["amount_eur"] = df.apply(
        lambda row: (
            None
            if row["is_quorum"]
            else (
                row["amount_parsed"] / row["exchange_rate"]
                if pd.notna(row["exchange_rate"])
                else None
            )
        ),
        axis=1,
    )

    print("\n💾 Preparing data for database...")
    transactions = []

    for _, row in df.iterrows():
        transaction = {
            "uuid": str(row["uuid"]),
            "date": row["date_parsed"].strftime("%Y-%m-%d"),
            "description": str(row["DESCRIPTION"]),
            "original_amount": float(row["original_amount"]),
            "original_currency": str(row["original_currency"]),
            "amount_eur": float(row["amount_eur"])
            if pd.notna(row["amount_eur"])
            else None,
            "amount_usd": float(row["amount_usd"])
            if pd.notna(row["amount_usd"])
            else None,
            "exchange_rate": float(row["exchange_rate"])
            if pd.notna(row["exchange_rate"])
            else None,
            "subcategory": str(row["SUBCATEGORY"]),
            "category": str(row["category"]),
            "budget_type": str(row["budget_type"]),
            "card_number": None,
            "is_quorum": 1 if bool(row["is_quorum"]) else 0,
            "notes": None,
        }
        transactions.append(transaction)

    print(f"\n✍️  Inserting {len(transactions)} transactions into database...")

    conn = db.connect()
    inserted = 0
    skipped = 0
    errors = []

    for tx in transactions:
        try:
            conn.execute(
                """
                INSERT INTO transactions (
                    uuid, date, description, original_amount, original_currency,
                    amount_eur, amount_usd, exchange_rate, subcategory, category,
                    budget_type, card_number, is_quorum, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    tx["uuid"],
                    tx["date"],
                    tx["description"],
                    tx["original_amount"],
                    tx["original_currency"],
                    tx["amount_eur"],
                    tx["amount_usd"],
                    tx["exchange_rate"],
                    tx["subcategory"],
                    tx["category"],
                    tx["budget_type"],
                    tx["card_number"],
                    tx["is_quorum"],
                    tx["notes"],
                ),
            )
            inserted += 1
        except Exception as e:
            if "UNIQUE constraint" in str(e):
                skipped += 1
            else:
                errors.append((tx, str(e)))
                if len(errors) <= 5:
                    print(f"❌ Error inserting transaction: {e}")
                    print(f"   Transaction: {tx['date']} - {tx['description']}")
                    print(
                        f"   Budget Type: {tx['budget_type']}, Is Quorum: {tx['is_quorum']}"
                    )

    if len(errors) > 5:
        print(f"   ... and {len(errors) - 5} more errors")

    conn.commit()

    print(f"✅ Inserted: {inserted}")
    if skipped > 0:
        print(f"⏭️  Skipped (duplicates): {skipped}")
    if errors:
        print(f"❌ Failed: {len(errors)}")

    if inserted > 0:
        print("\n💵 Calculating monthly Quorum totals...")
        calculate_monthly_quorum_totals()

    print("\n" + "=" * 60)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 60)
    print_summary_stats()


def get_category_mappings():
    """Get category mappings from database"""
    query = """
        SELECT DISTINCT subcategory, category, budget_type
        FROM categories
        WHERE subcategory IS NOT NULL
    """
    return db.fetch_df(query)


def calculate_monthly_quorum_totals():
    """Calculate and store monthly Quorum totals"""

    query = """
        SELECT 
            CAST(strftime('%Y', date) AS INTEGER) as year,
            CAST(strftime('%m', date) AS INTEGER) as month,
            SUM(amount_usd) as total_usd
        FROM transactions
        WHERE is_quorum = 1
        GROUP BY year, month
    """

    results = db.fetch_all(query)
    conn = db.connect()

    for year, month, total_usd in results:
        try:
            conn.execute(
                """
                INSERT INTO reimbursements (year, month, total_quorum_usd)
                VALUES (?, ?, ?)
                ON CONFLICT (year, month) DO UPDATE SET total_quorum_usd = excluded.total_quorum_usd
            """,
                (int(year), int(month), float(total_usd)),
            )
        except Exception as e:
            print(f"Warning: Could not insert reimbursement for {year}-{month}: {e}")

    conn.commit()
    print(f"✅ Stored {len(results)} monthly Quorum totals")


def print_summary_stats():
    """Print summary statistics"""
    conn = db.connect()

    total = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    date_range = conn.execute(
        "SELECT MIN(date), MAX(date) FROM transactions"
    ).fetchone()

    totals = conn.execute("""
        SELECT 
            SUM(CASE WHEN is_quorum = 0 THEN amount_eur ELSE 0 END) as total_eur,
            SUM(amount_usd) as total_usd,
            SUM(CASE WHEN is_quorum = 1 THEN amount_usd ELSE 0 END) as quorum_usd
        FROM transactions
    """).fetchone()

    print("\n📊 SUMMARY:")
    print(f"   Total transactions: {total}")
    print(f"   Date range: {date_range[0]} to {date_range[1]}")
    print(f"   Your expenses (original EUR): €{totals[0]:,.2f}")
    print(f"   Your expenses (bank USD): ${totals[1] - totals[2]:,.2f}")
    print(f"   Quorum (reimbursable USD): ${totals[2]:,.2f}")
    print(f"   Total credit card charges: ${totals[1]:,.2f}")
    print(f"   Net you pay (after Quorum): ${totals[1] - totals[2]:,.2f}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python migrate_historical.py <path_to_csv>")
        sys.exit(1)

    csv_path = sys.argv[1]
    migrate_historical_data(csv_path)
