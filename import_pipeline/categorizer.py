"""
Auto-categorization engine
Learns from past transactions and suggests categories for new ones
"""

from typing import Dict, List, Optional

import pandas as pd

from database.db import db


class Categorizer:
    """Auto-categorize transactions based on merchant patterns"""

    def __init__(self):
        self.merchant_patterns = {}
        self.category_map = {}
        self._load_patterns()
        self._load_categories()

    def _load_patterns(self):
        """Load merchant patterns from database"""
        try:
            patterns = db.fetch_df("""
                SELECT merchant_pattern, subcategory, confidence
                FROM merchant_mapping
                ORDER BY confidence DESC
            """)

            if len(patterns) > 0:
                self.merchant_patterns = {
                    row["merchant_pattern"]: {
                        "subcategory": row["subcategory"],
                        "confidence": row["confidence"],
                    }
                    for _, row in patterns.iterrows()
                }
                print(f"📚 Loaded {len(self.merchant_patterns)} merchant patterns")
            else:
                print(
                    "📚 No merchant patterns found (will learn from existing transactions)"
                )
                self._learn_from_history()
        except Exception as e:
            print(f"⚠️  Could not load merchant patterns: {e}")
            self._learn_from_history()

    def _learn_from_history(self):
        """Learn patterns from historical transactions"""
        try:
            transactions = db.fetch_df("""
                SELECT description, subcategory, COUNT(*) as count
                FROM transactions
                WHERE subcategory IS NOT NULL 
                  AND subcategory != ''
                  AND is_quorum = FALSE
                GROUP BY description, subcategory
                HAVING COUNT(*) >= 2
                ORDER BY count DESC
            """)

            if len(transactions) > 0:
                print(f"🧠 Learning from {len(transactions)} historical patterns...")

                for _, row in transactions.iterrows():
                    pattern = self._extract_merchant_pattern(row["description"])
                    self.merchant_patterns[pattern] = {
                        "subcategory": row["subcategory"],
                        "confidence": int(row["count"]),
                    }

                    self._save_pattern(pattern, row["subcategory"], int(row["count"]))

                print(f"✅ Learned {len(self.merchant_patterns)} patterns")
        except Exception as e:
            print(f"⚠️  Could not learn from history: {e}")

    def _load_categories(self):
        """Load category mappings from database"""
        categories = db.fetch_df("""
            SELECT subcategory, category, budget_type
            FROM categories
            WHERE subcategory IS NOT NULL
        """)

        self.category_map = {
            row["subcategory"]: {
                "category": row["category"],
                "budget_type": row["budget_type"],
            }
            for _, row in categories.iterrows()
        }

    def categorize(self, description: str, is_quorum: bool = False) -> Dict:
        """
        Suggest category for a transaction

        Args:
            description: Transaction description (merchant name)
            is_quorum: Whether this is a Quorum transaction

        Returns:
            Dict with subcategory, category, budget_type, and confidence
        """
        if is_quorum:
            return {
                "subcategory": "Quorum",
                "category": "Quorum",
                "budget_type": "Additional",
                "confidence": 100,
                "method": "auto",
            }

        for pattern, info in self.merchant_patterns.items():
            if pattern.lower() in description.lower():
                subcategory = info["subcategory"]

                if subcategory in self.category_map:
                    cat_info = self.category_map[subcategory]
                    return {
                        "subcategory": subcategory,
                        "category": cat_info["category"],
                        "budget_type": cat_info["budget_type"],
                        "confidence": min(info["confidence"] * 10, 90),
                        "method": "pattern",
                    }

        suggestions = self._fuzzy_match(description)
        if suggestions:
            return suggestions

        return {
            "subcategory": None,
            "category": None,
            "budget_type": None,
            "confidence": 0,
            "method": "none",
        }

    def _fuzzy_match(self, description: str) -> Optional[Dict]:
        """Try fuzzy matching on common keywords"""
        desc_lower = description.lower()

        fuzzy_rules = {
            "rewe": "Supermarket",
            "netto": "Supermarket",
            "lidl": "Supermarket",
            "edeka": "Supermarket",
            "aldi": "Supermarket",
            "combi": "Supermarket",
            "mcdonalds": "Fast Food",
            "burger": "Fast Food",
            "pizza": "Fast Food",
            "crobag": "Fast Food",
            "rossmann": "Household expenses",
            "dm-": "Household expenses",
            "apotheke": "Pharmacy",
            "barber": "Haircut",
            "db vertrieb": "Train ticket",
            "bolt": "Transportation",
            "uber": "Transportation",
        }

        for keyword, subcategory in fuzzy_rules.items():
            if keyword in desc_lower:
                if subcategory in self.category_map:
                    cat_info = self.category_map[subcategory]
                    return {
                        "subcategory": subcategory,
                        "category": cat_info["category"],
                        "budget_type": cat_info["budget_type"],
                        "confidence": 50,
                        "method": "fuzzy",
                    }

        return None

    def _extract_merchant_pattern(self, description: str) -> str:
        """Extract merchant name pattern from description"""
        import re

        parts = re.split(r"[\s\d]+", description)

        for part in parts:
            if len(part) >= 3:
                return part.upper()

        return description.split()[0].upper() if description else description

    def categorize_batch(self, transactions: pd.DataFrame) -> pd.DataFrame:
        """
        Categorize a batch of transactions

        Args:
            transactions: DataFrame with columns: DESCRIPTION, IS_QUORUM

        Returns:
            DataFrame with added columns: SUBCATEGORY, CATEGORY, BUDGET_TYPE, CONFIDENCE
        """
        print("🏷️  Auto-categorizing transactions...")

        results = []
        for _, row in transactions.iterrows():
            result = self.categorize(row["DESCRIPTION"], row.get("IS_QUORUM", False))
            results.append(result)

        transactions["SUBCATEGORY"] = [r["subcategory"] for r in results]
        transactions["CATEGORY"] = [r["category"] for r in results]
        transactions["BUDGET_TYPE"] = [r["budget_type"] for r in results]
        transactions["CONFIDENCE"] = [r["confidence"] for r in results]
        transactions["METHOD"] = [r["method"] for r in results]

        auto_count = sum(1 for r in results if r["confidence"] > 0)
        manual_count = len(results) - auto_count

        print(f"   ✅ Auto-categorized: {auto_count}")
        print(f"   ⚠️  Need manual review: {manual_count}")

        return transactions

    def learn_from_transaction(self, description: str, subcategory: str):
        """
        Learn a new pattern from a manually categorized transaction

        Args:
            description: Transaction description
            subcategory: The subcategory assigned
        """
        pattern = self._extract_merchant_pattern(description)

        if pattern in self.merchant_patterns:
            self.merchant_patterns[pattern]["confidence"] += 1
        else:
            self.merchant_patterns[pattern] = {
                "subcategory": subcategory,
                "confidence": 1,
            }

        self._save_pattern(
            pattern, subcategory, self.merchant_patterns[pattern]["confidence"]
        )

    def _save_pattern(self, pattern: str, subcategory: str, confidence: int):
        """Save pattern to database"""
        try:
            from datetime import datetime

            now = datetime.now().isoformat()

            db.write_execute(
                """
                INSERT INTO merchant_mapping (merchant_pattern, subcategory, confidence, last_used)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (merchant_pattern) DO UPDATE 
                SET subcategory = EXCLUDED.subcategory,
                    confidence = EXCLUDED.confidence,
                    last_used = EXCLUDED.last_used
            """,
                (pattern, subcategory, confidence, now),
            )
        except Exception as e:
            print(f"⚠️  Could not save pattern: {e}")

    def get_suggestions(self, description: str, top_n: int = 3) -> List[Dict]:
        """
        Get multiple category suggestions for a description

        Args:
            description: Transaction description
            top_n: Number of suggestions to return

        Returns:
            List of dicts with subcategory suggestions and confidence scores
        """
        result = self.categorize(description)

        if result["confidence"] > 0:
            return [result]

        return []


if __name__ == "__main__":
    categorizer = Categorizer()

    test_descriptions = [
        "REWE Frank Glawe o",
        "MCDONALDS 01446",
        "DB Vertrieb GmbH",
        "DIRECTV",
        "Unknown Merchant XYZ",
    ]

    print("\n" + "=" * 60)
    print("🧪 TESTING CATEGORIZER")
    print("=" * 60)

    for desc in test_descriptions:
        result = categorizer.categorize(desc)
        print(f"\n{desc}")
        print(f"   → {result['subcategory'] or 'UNCATEGORIZED'}")
        print(f"   Category: {result['category']}")
        print(f"   Confidence: {result['confidence']}%")
        print(f"   Method: {result['method']}")
