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
        self._read_only: bool = False

        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def connect(self, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        """
        Get or create database connection

        Args:
            read_only: If True, open in read-only mode (prevents lock conflicts)
        """
        if self._connection is not None and self._read_only != read_only:
            self.close()

        if self._connection is None:
            self._connection = duckdb.connect(self.db_path, read_only=read_only)
            self._read_only = read_only

        return self._connection

    def close(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None
            self._read_only = False

    def execute(self, query: str, params: tuple = None, read_only: bool = False):
        """Execute a query"""
        conn = self.connect(read_only=read_only)
        if params:
            return conn.execute(query, params)
        return conn.execute(query)

    def write_execute(self, query: str, params: tuple = None):
        """
        Execute a write query with a fresh connection

        This method closes any existing connection and creates a new write connection.
        Use this for INSERT, UPDATE, DELETE operations in web contexts.
        """
        self.close()

        conn = duckdb.connect(self.db_path, read_only=False)

        try:
            if params:
                result = conn.execute(query, params)
            else:
                result = conn.execute(query)
            return result
        finally:
            conn.close()

    def fetch_df(self, query: str, params: tuple = None) -> pd.DataFrame:
        """Execute query and return as DataFrame (read-only)"""
        result = self.execute(query, params, read_only=True)
        return result.df()

    def fetch_one(self, query: str, params: tuple = None):
        """Execute query and return single row (read-only)"""
        result = self.execute(query, params, read_only=True)
        return result.fetchone()

    def fetch_all(self, query: str, params: tuple = None):
        """Execute query and return all rows (read-only)"""
        result = self.execute(query, params, read_only=True)
        return result.fetchall()

    def insert_df(self, table: str, df: pd.DataFrame):
        """Insert DataFrame into table (write mode)"""
        conn = self.connect(read_only=False)
        conn.execute(f"INSERT INTO {table} SELECT * FROM df")

    def __enter__(self):
        """Context manager entry"""
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


db = Database()
