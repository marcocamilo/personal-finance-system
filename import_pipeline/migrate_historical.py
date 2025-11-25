"""
Migrate historical transaction data from CSV to database (SQLite)
"""

import hashlib
from datetime import datetime

import pandas as pd

from database.db import db
from import_pipeline.exchange_rates import exchange_rate_fetcher

EU_BILL_PATTERNS = [
    "RENT",
    "O2",
    "D-TICKET",
    "RUNDFUNK",
]


def is_eu_bill(description: str) -> bool:
    """Check if transaction is an EU bill (actually in EUR)"""
    desc_upper = description.upper()
    for pattern in EU_BILL_PATTERNS:
        if pattern in desc_upper:
            return True
    return False


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

    print("\n🇪🇺 Identifying EU bills (ACTUAL EUR amounts)...")
    df["is_eu_bill"] = df["DESCRIPTION"].apply(is_eu_bill)
    eu_bill_count = df["is_eu_bill"].sum()
    print(f"   Found {eu_bill_count} EU bill transactions")
    if eu_bill_count > 0:
        print("   These are the ONLY transactions where CSV amount is actually EUR:")
        for desc in df[df["is_eu_bill"]]["DESCRIPTION"].unique()[:5]:
            print(f"      • {desc}")

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
    print("   CRITICAL: CSV 'AMOUNT €' is misleading!")
    print("   • Most values are USD (what Capital One charged)")
    print("   • Only EU bills are actual EUR")

    non_quorum_non_eu = df[~df["is_quorum"] & ~df["is_eu_bill"]]
    unique_dates = non_quorum_non_eu["date_parsed"].unique()

    if len(unique_dates) > 0:
        print(f"   Fetching exchange rates for {len(unique_dates)} unique dates...")
        rates = exchange_rate_fetcher.fetch_bulk(unique_dates)

        df["exchange_rate"] = df.apply(
            lambda row: rates.get(row["date_parsed"].strftime("%Y-%m-%d"))
            if not row["is_quorum"] and not row["is_eu_bill"]
            else None,
            axis=1,
        )
    else:
        df["exchange_rate"] = None

    print("\n🔢 Calculating correct amounts...")
    print("   Logic:")
    print("   • Quorum: amount_parsed is USD → store as-is")
    print("   • EU Bills: amount_parsed is EUR → store as-is")
    print("   • Regular: amount_parsed is USD → calculate EUR = USD / rate")

    def calculate_original_amount(row):
        if row["is_quorum"]:
            return row["amount_parsed"]
        elif row["is_eu_bill"]:
            return row["amount_parsed"]
        else:
            if pd.notna(row["exchange_rate"]) and row["exchange_rate"] > 0:
                return row["amount_parsed"] / row["exchange_rate"]
            else:
                return row["amount_parsed"]

    df["original_amount"] = df.apply(calculate_original_amount, axis=1)

    def get_original_currency(row):
        if row["is_quorum"]:
            return "USD"
        else:
            return "EUR"

    df["original_currency"] = df.apply(get_original_currency, axis=1)

    def calculate_amount_eur(row):
        if row["is_quorum"]:
            return None
        elif row["is_eu_bill"]:
            return row["amount_parsed"]
        else:
            return row["original_amount"]

    df["amount_eur"] = df.apply(calculate_amount_eur, axis=1)

    def calculate_amount_usd(row):
        if row["is_quorum"]:
            return row["amount_parsed"]
        elif row["is_eu_bill"]:
            return None
        else:
            return row["amount_parsed"]

    df["amount_usd"] = df.apply(calculate_amount_usd, axis=1)

    print("\n💾 Preparing data for database...")

    print("\n📊 Examples of each transaction type:")

    regular_example = df[~df["is_quorum"] & ~df["is_eu_bill"]].head(1)
    if not regular_example.empty:
        row = regular_example.iloc[0]
        print(f"\n   Regular EUR Purchase: {row['DESCRIPTION'][:40]}")
        print(f"      CSV amount (USD): ${row['amount_parsed']:.2f}")
        print(
            f"      Calculated EUR: €{row['amount_eur']:.2f} (${row['amount_parsed']:.2f} / {row['exchange_rate']:.4f})"
        )
        print(
            f"      Stored: original_amount={row['original_amount']:.2f} EUR, amount_usd={row['amount_usd']:.2f}"
        )

    eu_example = df[df["is_eu_bill"]].head(1)
    if not eu_example.empty:
        row = eu_example.iloc[0]
        print(f"\n   EU Bill: {row['DESCRIPTION'][:40]}")
        print(f"      CSV amount (EUR): €{row['amount_parsed']:.2f}")
        print(
            f"      Stored: original_amount={row['original_amount']:.2f} EUR, amount_usd=NULL"
        )

    quorum_example = df[df["is_quorum"]].head(1)
    if not quorum_example.empty:
        row = quorum_example.iloc[0]
        print(f"\n   Quorum: {row['DESCRIPTION'][:40]}")
        print(f"      CSV amount (USD): ${row['amount_parsed']:.2f}")
        print(
            f"      Stored: original_amount={row['original_amount']:.2f} USD, amount_eur=NULL"
        )

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

    quorum = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE is_quorum = 1"
    ).fetchone()[0]

    eu_bills = conn.execute("""
        SELECT COUNT(*) FROM transactions 
        WHERE is_quorum = 0 
        AND amount_usd IS NULL 
        AND amount_eur IS NOT NULL
    """).fetchone()[0]

    regular = conn.execute("""
        SELECT COUNT(*) FROM transactions 
        WHERE is_quorum = 0 
        AND amount_usd IS NOT NULL 
        AND amount_eur IS NOT NULL
    """).fetchone()[0]

    totals = conn.execute("""
        SELECT 
            SUM(CASE WHEN is_quorum = 0 THEN amount_eur ELSE 0 END) as total_eur,
            SUM(CASE WHEN is_quorum = 0 AND amount_usd IS NOT NULL THEN amount_usd ELSE 0 END) as your_usd,
            SUM(CASE WHEN is_quorum = 1 THEN amount_usd ELSE 0 END) as quorum_usd
        FROM transactions
    """).fetchone()

    print("\n📊 SUMMARY:")
    print(f"   Total transactions: {total}")
    print(f"   Date range: {date_range[0]} to {date_range[1]}")
    print("\n   Transaction Types:")
    print(f"   • Regular EUR purchases: {regular}")
    print("     (CSV shows USD, calculated EUR = USD / rate)")
    print(f"   • EU Bills (actual EUR): {eu_bills}")
    print("     (CSV shows EUR, stored as-is)")
    print(f"   • Quorum (USD only): {quorum}")
    print("     (CSV shows USD, stored as-is)")
    print("\n   Financial Totals:")
    print(f"   • Your EUR expenses: €{totals[0]:,.2f}")
    print(f"   • Your credit card (USD): ${totals[1]:,.2f}")
    print(f"   • Quorum (reimbursable): ${totals[2]:,.2f}")
    print(f"   • Total credit card: ${totals[1] + totals[2]:,.2f}")
    print(f"   • Net you pay (after Quorum): ${totals[1]:,.2f}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python migrate_historical.py <path_to_csv>")
        sys.exit(1)

    csv_path = sys.argv[1]
    migrate_historical_data(csv_path)
