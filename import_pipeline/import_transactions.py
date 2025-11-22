"""
Transaction import orchestrator
Handles the complete import workflow: CSV → Process → Categorize → Review → Import
"""

from typing import Dict, List, Tuple

import pandas as pd

from database.db import db
from import_pipeline.categorizer import Categorizer
from import_pipeline.csv_processor import CSVProcessor
from import_pipeline.exchange_rates import exchange_rate_fetcher


class TransactionImporter:
    """Orchestrate the complete import workflow"""

    def __init__(self):
        self.processor = CSVProcessor()
        self.categorizer = Categorizer()
        self.processed_data = None
        self.categorized_data = None
        self.import_preview = None

    def load_and_process(self, csv_files: List[str]) -> pd.DataFrame:
        """
        Step 1: Load and process CSV files

        Args:
            csv_files: List of CSV file paths

        Returns:
            Processed DataFrame
        """
        print("=" * 60)
        print("STEP 1: LOAD & PROCESS CSV FILES")
        print("=" * 60)

        self.processor.load_csv_files(csv_files)
        self.processed_data = self.processor.process()

        return self.processed_data

    def auto_categorize(self) -> pd.DataFrame:
        """
        Step 2: Auto-categorize transactions

        Returns:
            Categorized DataFrame
        """
        if self.processed_data is None:
            raise ValueError("No processed data. Run load_and_process first.")

        print("\n" + "=" * 60)
        print("STEP 2: AUTO-CATEGORIZE TRANSACTIONS")
        print("=" * 60)

        self.categorized_data = self.categorizer.categorize_batch(self.processed_data)

        return self.categorized_data

    def check_duplicates(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Step 3: Check for duplicates against database

        Returns:
            Tuple of (new_transactions, duplicate_transactions)
        """
        if self.categorized_data is None:
            raise ValueError("No categorized data. Run auto_categorize first.")

        print("\n" + "=" * 60)
        print("STEP 3: CHECK FOR DUPLICATES")
        print("=" * 60)

        existing_uuids = set(
            row[0] for row in db.fetch_all("SELECT uuid FROM transactions")
        )

        new_mask = ~self.categorized_data["UUID"].isin(existing_uuids)

        new_transactions = self.categorized_data[new_mask].copy()
        duplicates = self.categorized_data[~new_mask].copy()

        print(f"   ✅ New transactions: {len(new_transactions)}")
        print(f"   ⏭️  Duplicates (will skip): {len(duplicates)}")

        return new_transactions, duplicates

    def fetch_exchange_rates(self, transactions: pd.DataFrame) -> pd.DataFrame:
        """
        Step 4: Fetch exchange rates for new transactions

        Args:
            transactions: DataFrame with new transactions

        Returns:
            DataFrame with exchange rates added
        """
        print("\n" + "=" * 60)
        print("STEP 4: FETCH EXCHANGE RATES")
        print("=" * 60)

        non_quorum = transactions[~transactions["IS_QUORUM"]]
        unique_dates = non_quorum["DATE"].unique()

        if len(unique_dates) == 0:
            print("   ℹ️  No exchange rates needed (all Quorum)")
            transactions["EXCHANGE_RATE"] = None
            return transactions

        print(f"   Fetching rates for {len(unique_dates)} unique dates...")

        rates = {}
        for date in unique_dates:
            date_str = pd.to_datetime(date).strftime("%Y-%m-%d")
            rate = exchange_rate_fetcher.get_rate(
                pd.to_datetime(date), allow_manual=False
            )
            if rate:
                rates[date_str] = rate

        transactions["EXCHANGE_RATE"] = transactions.apply(
            lambda row: rates.get(pd.to_datetime(row["DATE"]).strftime("%Y-%m-%d"))
            if not row["IS_QUORUM"]
            else None,
            axis=1,
        )

        missing_rates = transactions[
            ~transactions["IS_QUORUM"] & transactions["EXCHANGE_RATE"].isna()
        ]

        if len(missing_rates) > 0:
            print(
                f"   ⚠️  Warning: {len(missing_rates)} transactions missing exchange rates"
            )
            print("   These will be skipped during import")
        else:
            print("   ✅ All exchange rates fetched")

        return transactions

    def prepare_import(self, transactions: pd.DataFrame) -> pd.DataFrame:
        """
        Step 5: Prepare final data for import

        Args:
            transactions: DataFrame with categorized, de-duped transactions

        Returns:
            DataFrame ready for database insertion
        """
        print("\n" + "=" * 60)
        print("STEP 5: PREPARE FOR IMPORT")
        print("=" * 60)

        transactions["AMOUNT_USD"] = transactions["AMOUNT"]

        transactions["AMOUNT_EUR"] = transactions.apply(
            lambda row: (
                None
                if row["IS_QUORUM"]
                else (
                    row["AMOUNT"] / row["EXCHANGE_RATE"]
                    if pd.notna(row["EXCHANGE_RATE"])
                    else None
                )
            ),
            axis=1,
        )

        transactions.loc[
            transactions["IS_QUORUM"] & transactions["BUDGET_TYPE"].isna(),
            "BUDGET_TYPE",
        ] = "Additional"
        transactions.loc[
            transactions["IS_QUORUM"] & transactions["CATEGORY"].isna(), "CATEGORY"
        ] = "Quorum"
        transactions.loc[
            transactions["IS_QUORUM"] & transactions["SUBCATEGORY"].isna(),
            "SUBCATEGORY",
        ] = "Quorum"

        transactions.loc[
            ~transactions["IS_QUORUM"] & transactions["BUDGET_TYPE"].isna(),
            "BUDGET_TYPE",
        ] = "Unexpected"
        transactions.loc[
            ~transactions["IS_QUORUM"] & transactions["CATEGORY"].isna(), "CATEGORY"
        ] = "Unexpected"
        transactions.loc[
            ~transactions["IS_QUORUM"] & transactions["SUBCATEGORY"].isna(),
            "SUBCATEGORY",
        ] = "Uncategorized"

        self.import_preview = transactions

        ready = transactions[
            transactions["AMOUNT_USD"].notna()
            & (transactions["IS_QUORUM"] | transactions["AMOUNT_EUR"].notna())
        ]

        print(f"   ✅ Ready for import: {len(ready)}")
        print(
            f"   ⚠️  Need manual categorization: {(transactions['CONFIDENCE'] == 0).sum()}"
        )

        return transactions

    def get_preview_summary(self) -> Dict:
        """Get summary of transactions ready for import"""
        if self.import_preview is None:
            return {}

        df = self.import_preview

        return {
            "total": len(df),
            "new": len(df),
            "quorum": df["IS_QUORUM"].sum(),
            "auto_categorized": (df["CONFIDENCE"] > 0).sum(),
            "needs_review": (df["CONFIDENCE"] == 0).sum(),
            "total_usd": df["AMOUNT_USD"].sum(),
            "quorum_usd": df[df["IS_QUORUM"]]["AMOUNT_USD"].sum(),
            "date_range": (df["DATE"].min(), df["DATE"].max()),
        }

    def import_to_database(
        self, transactions: pd.DataFrame = None
    ) -> Tuple[int, int, List]:
        """
        Step 6: Import transactions to database

        Args:
            transactions: DataFrame to import (uses self.import_preview if None)

        Returns:
            Tuple of (inserted_count, skipped_count, errors)
        """
        if transactions is None:
            transactions = self.import_preview

        if transactions is None:
            raise ValueError("No data to import")

        print("\n" + "=" * 60)
        print("STEP 6: IMPORT TO DATABASE")
        print("=" * 60)

        inserted = 0
        skipped = 0
        errors = []

        for _, row in transactions.iterrows():
            try:
                if pd.isna(row["AMOUNT_USD"]):
                    skipped += 1
                    continue

                if not row["IS_QUORUM"] and pd.isna(row["AMOUNT_EUR"]):
                    skipped += 1
                    continue

                db.write_execute(
                    """
                    INSERT INTO transactions (
                        uuid, date, description, original_amount, original_currency,
                        amount_eur, amount_usd, exchange_rate, subcategory, category,
                        budget_type, card_number, is_quorum, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        str(row["UUID"]),
                        pd.to_datetime(row["DATE"]).strftime("%Y-%m-%d"),
                        str(row["DESCRIPTION"]),
                        float(row["AMOUNT"]),
                        "USD",
                        float(row["AMOUNT_EUR"])
                        if pd.notna(row["AMOUNT_EUR"])
                        else None,
                        float(row["AMOUNT_USD"]),
                        float(row["EXCHANGE_RATE"])
                        if pd.notna(row["EXCHANGE_RATE"])
                        else None,
                        str(row["SUBCATEGORY"])
                        if pd.notna(row["SUBCATEGORY"])
                        else None,
                        str(row["CATEGORY"]) if pd.notna(row["CATEGORY"]) else None,
                        str(row["BUDGET_TYPE"])
                        if pd.notna(row["BUDGET_TYPE"])
                        else None,
                        str(row["CARD_NUMBER"])
                        if pd.notna(row["CARD_NUMBER"])
                        else None,
                        bool(row["IS_QUORUM"]),
                        None,
                    ),
                )
                inserted += 1

                if row["CONFIDENCE"] > 0:
                    self.categorizer.learn_from_transaction(
                        row["DESCRIPTION"], row["SUBCATEGORY"]
                    )

            except Exception as e:
                if "UNIQUE constraint" in str(e) or "Duplicate" in str(e):
                    skipped += 1
                else:
                    errors.append({"transaction": row["DESCRIPTION"], "error": str(e)})

        print(f"\n   ✅ Inserted: {inserted}")
        if skipped > 0:
            print(f"   ⏭️  Skipped: {skipped}")
        if errors:
            print(f"   ❌ Errors: {len(errors)}")
            for err in errors[:5]:
                print(f"      - {err['transaction']}: {err['error']}")

        if inserted > 0:
            self._update_quorum_totals()

        return inserted, skipped, errors

    def _update_quorum_totals(self):
        """Update monthly Quorum totals"""
        print("\n   💵 Updating Quorum totals...")

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

        for year, month, total_usd in results:
            try:
                db.write_execute(
                    """
                    INSERT INTO reimbursements (year, month, total_quorum_usd)
                    VALUES (?, ?, ?)
                    ON CONFLICT (year, month) DO UPDATE 
                    SET total_quorum_usd = EXCLUDED.total_quorum_usd
                """,
                    (int(year), int(month), float(total_usd)),
                )
            except Exception as e:
                print(f"      Warning: Could not update {year}-{month}: {e}")

        print("   ✅ Updated Quorum totals")

    def run_full_import(self, csv_files: List[str], auto_confirm: bool = False) -> Dict:
        """
        Run the complete import workflow

        Args:
            csv_files: List of CSV file paths
            auto_confirm: If True, skip confirmation and import automatically

        Returns:
            Dict with import summary
        """
        self.load_and_process(csv_files)
        self.auto_categorize()
        new_transactions, duplicates = self.check_duplicates()

        if len(new_transactions) == 0:
            print("\n" + "=" * 60)
            print("ℹ️  NO NEW TRANSACTIONS TO IMPORT")
            print("=" * 60)
            return {"imported": 0, "skipped": len(duplicates), "errors": []}

        new_transactions = self.fetch_exchange_rates(new_transactions)
        new_transactions = self.prepare_import(new_transactions)

        preview = self.get_preview_summary()
        print("\n" + "=" * 60)
        print("📋 IMPORT PREVIEW")
        print("=" * 60)
        print(f"   Total new transactions: {preview['total']}")
        print(
            f"   Date range: {preview['date_range'][0]} to {preview['date_range'][1]}"
        )
        print(f"   Your transactions: {preview['total'] - preview['quorum']}")
        print(f"   Quorum transactions: {preview['quorum']}")
        print(f"   Auto-categorized: {preview['auto_categorized']}")
        print(f"   Need review: {preview['needs_review']}")
        print(f"   Total amount: ${preview['total_usd']:,.2f}")

        if not auto_confirm:
            print("\n" + "=" * 60)
            response = input("Proceed with import? (yes/no): ").strip().lower()
            if response != "yes":
                print("❌ Import cancelled")
                return {"imported": 0, "skipped": 0, "errors": [], "cancelled": True}

        inserted, skipped, errors = self.import_to_database(new_transactions)

        print("\n" + "=" * 60)
        print("✅ IMPORT COMPLETE!")
        print("=" * 60)

        return {
            "imported": inserted,
            "skipped": skipped + len(duplicates),
            "errors": errors,
        }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python import_transactions.py <csv_file1> [csv_file2] ...")
        sys.exit(1)

    importer = TransactionImporter()
    result = importer.run_full_import(sys.argv[1:])

    print("\n📊 Final Summary:")
    print(f"   Imported: {result['imported']}")
    print(f"   Skipped: {result['skipped']}")
    if result.get("errors"):
        print(f"   Errors: {len(result['errors'])}")
