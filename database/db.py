"""
SQLite database connection and query manager
"""

import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd


class Database:
    """Database connection manager for SQLite"""

    def __init__(self, db_path: str = "data/finance.db"):
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None

        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        """
        Get or create database connection with optimizations for concurrent access
        """
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0,
            )

            self._connection.execute("PRAGMA journal_mode=WAL")

            self._connection.execute("PRAGMA foreign_keys=ON")

            self._connection.row_factory = sqlite3.Row

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

    def write_execute(self, query: str, params: tuple = None):
        """
        Execute a write query and commit

        Use this for INSERT, UPDATE, DELETE operations.
        """
        conn = self.connect()
        try:
            if params:
                cursor = conn.execute(query, params)
            else:
                cursor = conn.execute(query)
            conn.commit()
            return cursor
        except Exception as e:
            conn.rollback()
            raise e

    def fetch_df(self, query: str, params: tuple = None) -> pd.DataFrame:
        """Execute query and return as DataFrame"""
        conn = self.connect()
        return pd.read_sql_query(query, conn, params=params)

    def fetch_one(self, query: str, params: tuple = None):
        """Execute query and return single row"""
        result = self.execute(query, params)
        row = result.fetchone()
        return row if row is None else tuple(row)

    def fetch_all(self, query: str, params: tuple = None):
        """Execute query and return all rows"""
        result = self.execute(query, params)
        return [tuple(row) for row in result.fetchall()]

    def insert_df(self, table: str, df: pd.DataFrame):
        """Insert DataFrame into table"""
        conn = self.connect()
        df.to_sql(table, conn, if_exists="append", index=False)
        conn.commit()

    def __enter__(self):
        """Context manager entry"""
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if exc_type is None:
            self._connection.commit()
        else:
            self._connection.rollback()
        self.close()


db = Database()
