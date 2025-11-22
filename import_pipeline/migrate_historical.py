"""
Migrate historical transaction data from CSV to database
"""
import pandas as pd
import hashlib
from datetime import datetime
from database.db import db
from import_pipeline.exchange_rates import exchange_rate_fetcher


def generate_uuid(row):
    """Generate UUID from transaction data"""
    # Use date, description, and amount to create unique ID
    unique_string = f"{row['DATE']}{row['DESCRIPTION']}{row['AMOUNT']}"
    return hashlib.md5(unique_string.encode()).hexdigest()


def parse_date(date_str: str) -> datetime:
    """Parse date from DD.MM.YYYY format"""
    return datetime.strptime(date_str.strip(), '%d.%m.%Y')


def parse_amount(amount_str: str) -> float:
    """Parse amount from European format (e.g., '1.234,56 €')"""
    # Remove € symbol and whitespace
    amount_str = amount_str.replace('€', '').strip()
    # Replace German decimal separator
    amount_str = amount_str.replace('.', '').replace(',', '.')
    return float(amount_str)


def migrate_historical_data(csv_path: str):
    """
    Migrate historical transaction data from CSV
    
    Args:
        csv_path: Path to the historical transactions CSV file
    """
    print("=" * 60)
    print("📥 MIGRATING HISTORICAL DATA")
    print("=" * 60)
    
    # Read CSV
    print(f"\n📖 Reading CSV from: {csv_path}")
    df = pd.read_csv(csv_path)  # Comma-separated
    print(f"✅ Loaded {len(df)} transactions")
    
    # Parse dates
    print("\n📅 Parsing dates...")
    df['date_parsed'] = df['DATE'].apply(parse_date)
    
    # Parse amounts
    print("💰 Parsing amounts...")
    df['amount_parsed'] = df['AMOUNT'].apply(parse_amount)
    
    # Generate UUIDs
    print("🔑 Generating UUIDs...")
    df['uuid'] = df.apply(generate_uuid, axis=1)
    
    # Check for duplicates
    duplicates = df[df.duplicated(subset=['uuid'], keep=False)]
    if len(duplicates) > 0:
        print(f"⚠️  Found {len(duplicates)} duplicate transactions (will keep first occurrence)")
        df = df.drop_duplicates(subset=['uuid'], keep='first')
    
    # Identify Quorum transactions
    print("\n🏦 Identifying Quorum transactions...")
    df['is_quorum'] = df['SUBCATEGORY'] == 'Quorum'
    quorum_count = df['is_quorum'].sum()
    print(f"   Found {quorum_count} Quorum transactions")
    
    # Get category mappings
    print("\n📋 Mapping categories...")
    category_map = get_category_mappings()
    df = df.merge(
        category_map,
        left_on='SUBCATEGORY',
        right_on='subcategory',
        how='left'
    )
    
    # Handle unmapped categories - set defaults based on is_quorum
    unmapped = df[df['budget_type'].isna()]
    if len(unmapped) > 0:
        print(f"⚠️  Warning: {len(unmapped)} transactions have unmapped categories:")
        for _, row in unmapped.head(10).iterrows():  # Show max 10
            print(f"   - {row['DESCRIPTION']}: {row['SUBCATEGORY']}")
        
        # Set defaults for unmapped
        print("\n🔧 Setting defaults for unmapped transactions...")
        df.loc[df['is_quorum'], 'budget_type'] = df.loc[df['is_quorum'], 'budget_type'].fillna('Additional')
        df.loc[df['is_quorum'], 'category'] = df.loc[df['is_quorum'], 'category'].fillna('Quorum')
        df.loc[~df['is_quorum'], 'budget_type'] = df.loc[~df['is_quorum'], 'budget_type'].fillna('Unexpected')
        df.loc[~df['is_quorum'], 'category'] = df.loc[~df['is_quorum'], 'category'].fillna('Unexpected')
    
    # Process currency for each transaction
    print("\n💱 Processing currency...")
    
    # For Quorum: amount is USD, no conversion needed
    # For others: amount is EUR, need to fetch exchange rates
    
    non_quorum = df[~df['is_quorum']]
    unique_dates = non_quorum['date_parsed'].unique()
    
    if len(unique_dates) > 0:
        print(f"   Fetching exchange rates for {len(unique_dates)} unique dates...")
        rates = exchange_rate_fetcher.fetch_bulk(unique_dates)
        
        # Map rates to transactions
        df['exchange_rate'] = df.apply(
            lambda row: rates.get(row['date_parsed'].strftime('%Y-%m-%d')) if not row['is_quorum'] else None,
            axis=1
        )
    else:
        df['exchange_rate'] = None
    
    # Set original_currency and amounts
    df['original_currency'] = df['is_quorum'].map({True: 'USD', False: 'EUR'})
    df['original_amount'] = df['amount_parsed']
    
    # Calculate EUR and USD amounts
    df['amount_eur'] = df.apply(
        lambda row: row['amount_parsed'] if not row['is_quorum'] else None,
        axis=1
    )
    
    df['amount_usd'] = df.apply(
        lambda row: (
            row['amount_parsed'] if row['is_quorum']  # Quorum: already USD
            else (row['amount_parsed'] * row['exchange_rate'] if pd.notna(row['exchange_rate']) else None)
        ),
        axis=1
    )
    
    # Prepare data for insertion
    print("\n💾 Preparing data for database...")
    transactions = []
    
    for _, row in df.iterrows():
        transaction = {
            'uuid': row['uuid'],
            'date': row['date_parsed'].strftime('%Y-%m-%d'),
            'description': row['DESCRIPTION'],
            'original_amount': row['original_amount'],
            'original_currency': row['original_currency'],
            'amount_eur': row['amount_eur'],
            'amount_usd': row['amount_usd'],
            'exchange_rate': row['exchange_rate'],
            'subcategory': row['SUBCATEGORY'],
            'category': row['CATEGORY'],
            'budget_type': row['budget_type'],
            'card_number': None,  # Not available in historical data
            'is_quorum': row['is_quorum'],
            'notes': None,
        }
        transactions.append(transaction)
    
    # Insert into database
    print(f"\n✍️  Inserting {len(transactions)} transactions into database...")
    
    conn = db.connect()
    inserted = 0
    skipped = 0
    
    for tx in transactions:
        try:
            conn.execute("""
                INSERT INTO transactions (
                    uuid, date, description, original_amount, original_currency,
                    amount_eur, amount_usd, exchange_rate, subcategory, category,
                    budget_type, card_number, is_quorum, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tx['uuid'], tx['date'], tx['description'], tx['original_amount'],
                tx['original_currency'], tx['amount_eur'], tx['amount_usd'],
                tx['exchange_rate'], tx['subcategory'], tx['category'],
                tx['budget_type'], tx['card_number'], tx['is_quorum'], tx['notes']
            ))
            inserted += 1
        except Exception as e:
            if 'UNIQUE constraint' in str(e):
                skipped += 1
            else:
                print(f"❌ Error inserting transaction: {e}")
                print(f"   Transaction: {tx['date']} - {tx['description']}")
    
    print(f"✅ Inserted: {inserted}")
    if skipped > 0:
        print(f"⏭️  Skipped (duplicates): {skipped}")
    
    # Calculate and store monthly Quorum totals
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
            EXTRACT(YEAR FROM date) as year,
            EXTRACT(MONTH FROM date) as month,
            SUM(amount_usd) as total_usd
        FROM transactions
        WHERE is_quorum = TRUE
        GROUP BY year, month
    """
    
    results = db.fetch_all(query)
    conn = db.connect()
    
    for year, month, total_usd in results:
        try:
            conn.execute("""
                INSERT OR REPLACE INTO reimbursements (year, month, total_quorum_usd)
                VALUES (?, ?, ?)
            """, (int(year), int(month), float(total_usd)))
        except Exception as e:
            print(f"Warning: Could not insert reimbursement for {year}-{month}: {e}")
    
    print(f"✅ Stored {len(results)} monthly Quorum totals")


def print_summary_stats():
    """Print summary statistics"""
    conn = db.connect()
    
    # Total transactions
    total = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    
    # Date range
    date_range = conn.execute("""
        SELECT MIN(date), MAX(date) FROM transactions
    """).fetchone()
    
    # Total amounts
    totals = conn.execute("""
        SELECT 
            SUM(CASE WHEN is_quorum = FALSE THEN amount_eur ELSE 0 END) as total_eur,
            SUM(amount_usd) as total_usd,
            SUM(CASE WHEN is_quorum = TRUE THEN amount_usd ELSE 0 END) as quorum_usd
        FROM transactions
    """).fetchone()
    
    print("\n📊 SUMMARY:")
    print(f"   Total transactions: {total}")
    print(f"   Date range: {date_range[0]} to {date_range[1]}")
    print(f"   Your expenses: €{totals[0]:,.2f}")
    print(f"   Total USD charges: ${totals[1]:,.2f}")
    print(f"   Quorum (reimbursable): ${totals[2]:,.2f}")
    print(f"   Net expenses: ${totals[1] - totals[2]:,.2f}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python migrate_historical.py <path_to_csv>")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    migrate_historical_data(csv_path)
