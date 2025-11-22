"""
Setup script to initialize database and migrate historical data
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from database.init_db import init_database
from import_pipeline.migrate_historical import migrate_historical_data


def setup():
    """Run complete setup"""
    print("\n" + "=" * 60)
    print("🚀 FINANCE TRACKER SETUP")
    print("=" * 60)
    
    # Step 1: Initialize database
    print("\n📦 Step 1: Initialize Database")
    print("-" * 60)
    init_database()
    
    # Step 2: Migrate historical data
    print("\n📦 Step 2: Migrate Historical Data")
    print("-" * 60)
    
    # Check if historical CSV exists
    historical_csv = Path("./uploads/historical_transactions.csv")
    
    if not historical_csv.exists():
        print("⚠️  Historical transactions file not found at:")
        print(f"   {historical_csv}")
        print("\n💡 You can run migration later with:")
        print("   python import_pipeline/migrate_historical.py <path_to_csv>")
    else:
        migrate_historical_data(str(historical_csv))
    
    print("\n" + "=" * 60)
    print("✅ SETUP COMPLETE!")
    print("=" * 60)
    print("\n📝 Next steps:")
    print("   1. Review the database: data/finance.db")
    print("   2. Run the app: python app.py")
    print("   3. Start importing new transactions!")


if __name__ == "__main__":
    setup()
