"""
CSV processor for credit card statements
Handles Capital One format and auto-detects Quorum transactions
Excludes EU bills (Rent, O2, D-Ticket) from USD conversion
"""

import glob
import hashlib
from typing import Dict, List

import pandas as pd


class CSVProcessor:
    """Process credit card CSV files"""

    QUORUM_CARDS = [7575, 4479]

    EU_BILL_PATTERNS = [
        "RENT",
        "O2",
        "D-TICKET",
        "RUNDFUNK",
    ]

    def __init__(self):
        self.processed_data = None
        self.raw_data = None

    def load_csv_files(self, file_paths: List[str]) -> pd.DataFrame:
        """
        Load one or more CSV files

        Args:
            file_paths: List of paths to CSV files

        Returns:
            Combined DataFrame with all transactions
        """
        print(f"📂 Loading {len(file_paths)} CSV file(s)...")

        dataframes = []
        for file_path in file_paths:
            try:
                df = pd.read_csv(file_path)
                dataframes.append(df)
                print(f"   ✅ Loaded {len(df)} rows from {file_path}")
            except Exception as e:
                print(f"   ❌ Error loading {file_path}: {e}")

        if not dataframes:
            raise ValueError("No CSV files loaded successfully")

        combined = pd.concat(dataframes, ignore_index=True)
        self.raw_data = combined
        print(f"✅ Total rows loaded: {len(combined)}")

        return combined

    def is_eu_bill(self, description: str) -> bool:
        """Check if transaction is an EU bill that should stay in EUR"""
        desc_upper = description.upper()
        for pattern in self.EU_BILL_PATTERNS:
            if pattern in desc_upper:
                return True
        return False

    def process(self, df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Process credit card CSV data

        Args:
            df: DataFrame to process (uses self.raw_data if None)

        Returns:
            Processed DataFrame ready for import
        """
        if df is None:
            df = self.raw_data

        if df is None:
            raise ValueError("No data to process. Load CSV files first.")

        print("\n🔄 Processing transactions...")

        print("   Filtering credits...")
        original_count = len(df)
        df = df.query("Credit.isna()").copy()
        filtered_count = len(df)
        print(
            f"   Kept {filtered_count} debits (removed {original_count - filtered_count} credits)"
        )

        print("   Identifying Quorum transactions...")
        df["is_quorum"] = df["Card No."].isin(self.QUORUM_CARDS)
        quorum_count = df["is_quorum"].sum()
        print(f"   Found {quorum_count} Quorum transactions")

        print("   Identifying EU bills (non-convertible)...")
        df["is_eu_bill"] = df["Description"].apply(self.is_eu_bill)
        eu_bill_count = df["is_eu_bill"].sum()
        print(f"   Found {eu_bill_count} EU bill transactions")

        print("   Generating UUIDs...")
        df["uuid"] = df.apply(self._generate_uuid, axis=1)

        duplicates = df.duplicated(subset=["uuid"], keep="first")
        if duplicates.any():
            dup_count = duplicates.sum()
            print(f"   ⚠️  Found {dup_count} duplicate(s) - keeping first occurrence")
            df = df[~duplicates]

        print("   Parsing dates...")
        df["parsed_date"] = pd.to_datetime(df["Transaction Date"])

        print("   Formatting output...")
        df_clean = pd.DataFrame(
            {
                "DATE": df["parsed_date"],
                "DESCRIPTION": df["Description"],
                "AMOUNT": df["Debit"],
                "CARD_NUMBER": df["Card No."].astype(str).str[-4:],
                "IS_QUORUM": df["is_quorum"],
                "IS_EU_BILL": df["is_eu_bill"],
                "UUID": df["uuid"],
                "CATEGORY": df["Category"],
            }
        )

        df_clean = df_clean.sort_values("DATE").reset_index(drop=True)

        self.processed_data = df_clean
        print(f"✅ Processing complete: {len(df_clean)} transactions ready")
        print(f"   • Your transactions: {(~df_clean['IS_QUORUM']).sum()}")
        print(f"   • Quorum (USD): {df_clean['IS_QUORUM'].sum()}")
        print(f"   • EU Bills (EUR, non-convertible): {df_clean['IS_EU_BILL'].sum()}")

        return df_clean

    def _generate_uuid(self, row) -> str:
        """Generate UUID from transaction data"""
        unique_string = f"{row['Transaction Date']}{row['Description']}{row['Debit']}"
        return hashlib.md5(unique_string.encode()).hexdigest()

    def get_summary(self) -> Dict:
        """Get summary statistics of processed data"""
        if self.processed_data is None:
            return {}

        df = self.processed_data

        return {
            "total_transactions": len(df),
            "date_range": (df["DATE"].min(), df["DATE"].max()),
            "quorum_count": df["IS_QUORUM"].sum(),
            "your_count": (~df["IS_QUORUM"]).sum(),
            "eu_bill_count": df["IS_EU_BILL"].sum(),
            "total_amount": df["AMOUNT"].sum(),
            "quorum_amount": df[df["IS_QUORUM"]]["AMOUNT"].sum(),
            "your_amount": df[~df["IS_QUORUM"]]["AMOUNT"].sum(),
            "eu_bill_amount": df[df["IS_EU_BILL"]]["AMOUNT"].sum(),
        }

    def export_for_manual_review(self, output_path: str):
        """Export processed data to CSV for manual review"""
        if self.processed_data is None:
            raise ValueError("No processed data to export")

        self.processed_data.to_csv(output_path, index=False)
        print(f"✅ Exported to {output_path}")

    @staticmethod
    def load_from_directory(directory: str, pattern: str = "*.csv") -> "CSVProcessor":
        """
        Convenience method to load all CSVs from a directory

        Args:
            directory: Path to directory containing CSV files
            pattern: Glob pattern for CSV files (default: *.csv)

        Returns:
            CSVProcessor with loaded and processed data
        """
        file_paths = glob.glob(f"{directory}/{pattern}")

        if not file_paths:
            raise ValueError(f"No CSV files found in {directory}")

        processor = CSVProcessor()
        processor.load_csv_files(file_paths)
        processor.process()

        return processor
