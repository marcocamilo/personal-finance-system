"""
DuckDB database connection and query manager
"""

from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd


class Database:
    """Database connection manager for DuckDB"""

    def __init__(self, db_path: str = "data/finance.db"):
        self.db_path = db_path
        self._connection: Optional[duckdb.DuckDBPyConnection] = None

        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> duckdb.DuckDBPyConnection:
        """Get or create database connection"""
        if self._connection is None:
            self._connection = duckdb.connect(self.db_path)
        return self._connection

    def close(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None

    def execute(self, query: str, params: tuple = None):
        """Execute a query"""
        conn = self.connect()
        if params:
            return conn.execute(query, params)
        return conn.execute(query)

    def fetch_df(self, query: str, params: tuple = None) -> pd.DataFrame:
        """Execute query and return as DataFrame"""
        result = self.execute(query, params)
        return result.df()

    def fetch_one(self, query: str, params: tuple = None):
        """Execute query and return single row"""
        result = self.execute(query, params)
        return result.fetchone()

    def fetch_all(self, query: str, params: tuple = None):
        """Execute query and return all rows"""
        result = self.execute(query, params)
        return result.fetchall()

    def insert_df(self, table: str, df: pd.DataFrame):
        """Insert DataFrame into table"""
        conn = self.connect()
        conn.execute(f"INSERT INTO {table} SELECT * FROM df")

    def __enter__(self):
        """Context manager entry"""
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


db = Database()
