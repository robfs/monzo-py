"""Monzo Transactions Analysis Package.

A Python package for analyzing Monzo transaction data using Google Sheets API
and DuckDB for high-performance analytical queries.

This package provides tools to:
- Connect to Google Sheets containing Monzo transaction exports
- Load data efficiently using PyArrow and DuckDB
- Perform complex financial analysis with SQL queries
- Handle proper data type conversions for dates, times, and amounts
"""

from .monzo_transactions import MonzoTransactions

__version__ = "0.1.0"
__author__ = "Monzo Py Team"
__email__ = "contact@monzo-py.com"

__all__ = ["MonzoTransactions"]
