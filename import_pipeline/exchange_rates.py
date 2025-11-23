"""
Exchange rate fetcher using Frankfurter API (European Central Bank data)
"""

from datetime import datetime, timedelta
from typing import Dict, Optional

import requests

from database.db import db


class ExchangeRateFetcher:
    """Fetch and cache EUR/USD exchange rates"""

    BASE_URL = "https://api.frankfurter.app"

    def __init__(self):
        self.cache: Dict[str, float] = {}
        self._load_cache_from_db()

    def _load_cache_from_db(self):
        """Load cached rates from database"""
        try:
            result = db.fetch_all("SELECT date, eur_to_usd FROM exchange_rates")
            self.cache = {str(row[0]): float(row[1]) for row in result}
        except Exception as e:
            print(f"Warning: Could not load exchange rate cache: {e}")
            self.cache = {}

    def get_rate(self, date: datetime, allow_manual: bool = True) -> Optional[float]:
        """
        Get EUR/USD exchange rate for a specific date

        Args:
            date: The date to fetch rate for
            allow_manual: If True, prompts user for manual entry if API fails

        Returns:
            Exchange rate (EUR to USD) or None if unavailable
        """
        date_str = date.strftime("%Y-%m-%d")

        if date_str in self.cache:
            return self.cache[date_str]

        rate = self._fetch_from_api(date)

        if rate:
            self._save_to_cache(date_str, rate)
            return rate

        print(f"⚠️  Rate not available for {date_str}, trying nearby dates...")
        for offset in range(1, 4):
            for delta in [offset, -offset]:
                nearby_date = date + timedelta(days=delta)
                rate = self._fetch_from_api(nearby_date)
                if rate:
                    print(f"✅ Using rate from {nearby_date.strftime('%Y-%m-%d')}")
                    self._save_to_cache(date_str, rate)
                    return rate

        if allow_manual:
            print(f"\n❌ Could not fetch rate for {date_str} from API")
            rate = self._prompt_manual_entry(date_str)
            if rate:
                self._save_to_cache(date_str, rate)
                return rate

        return None

    def _fetch_from_api(self, date: datetime) -> Optional[float]:
        """Fetch rate from Frankfurter API"""
        date_str = date.strftime("%Y-%m-%d")

        try:
            url = f"{self.BASE_URL}/{date_str}?from=EUR&to=USD"
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                rate = data["rates"]["USD"]
                return float(rate)

        except Exception as e:
            print(f"API error for {date_str}: {e}")

        return None

    def _prompt_manual_entry(self, date_str: str) -> Optional[float]:
        """Prompt user for manual rate entry"""
        try:
            rate_input = input(
                f"Enter EUR/USD rate for {date_str} (or 'skip'): "
            ).strip()

            if rate_input.lower() == "skip":
                return None

            rate = float(rate_input)

            if rate <= 0:
                print("Invalid rate (must be positive)")
                return None

            return rate

        except ValueError:
            print("Invalid input")
            return None

    def _save_to_cache(self, date_str: str, rate: float):
        """Save rate to cache and database"""
        self.cache[date_str] = rate

        try:
            db.write_execute(
                """
                INSERT OR REPLACE INTO exchange_rates (date, eur_to_usd)
                VALUES (?, ?)
            """,
                (date_str, rate),
            )
        except Exception as e:
            print(f"Warning: Could not save rate to database: {e}")

    def fetch_bulk(self, dates: list) -> Dict[str, float]:
        """
        Fetch rates for multiple dates (optimized for historical migration)

        Args:
            dates: List of datetime objects

        Returns:
            Dictionary mapping date strings to rates
        """
        unique_dates = sorted(set(d.strftime("%Y-%m-%d") for d in dates))
        rates = {}

        print(f"📊 Fetching exchange rates for {len(unique_dates)} unique dates...")

        for i, date_str in enumerate(unique_dates):
            if (i + 1) % 10 == 0:
                print(f"   Progress: {i + 1}/{len(unique_dates)}")

            date = datetime.strptime(date_str, "%Y-%m-%d")
            rate = self.get_rate(date, allow_manual=False)

            if rate:
                rates[date_str] = rate
            else:
                if i > 0:
                    prev_rate = rates.get(unique_dates[i - 1])
                    if prev_rate:
                        print(f"⚠️  Using previous rate for {date_str}")
                        rates[date_str] = prev_rate
                        self._save_to_cache(date_str, prev_rate)

        print(f"✅ Fetched {len(rates)} rates")
        return rates


exchange_rate_fetcher = ExchangeRateFetcher()
