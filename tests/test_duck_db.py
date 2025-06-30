#!/usr/bin/env python3
"""Unit tests for the duck_db method of MonzoTransactions."""

from decimal import Decimal
from unittest.mock import patch

import pytest


class TestMonzoTransactionsDuckDB:
    """Test cases for the duck_db method."""

    def test_duck_db_with_sample_data(self, monzo_instance, sample_transaction_data):
        """Test duck_db method with sample data."""
        # Add one more row to the sample data for this test
        extended_data = [
            *sample_transaction_data,
            [
                "tx_125",
                "2024-01-03",
                "15:20",
                "Payment",
                "Grocery Store",
                "🛒",
                "Shopping",
                "-45.67",
                "GBP",
                "-45.67",
                "GBP",
                "",
                "",
                "",
                "Weekly shopping",
                "cat_shopping",
            ],
        ]

        with patch.object(
            type(monzo_instance),
            "data",
            new_callable=lambda: property(lambda self: extended_data),
        ):
            # Call duck_db method
            db_conn = monzo_instance.duck_db()

            # Verify the connection is created
            assert db_conn is not None

            # Verify table exists
            tables = db_conn.execute("SHOW TABLES").fetchall()
            assert len(tables) == 1
            assert tables[0][0] == "transactions"

            # Verify column structure
            schema = db_conn.execute("DESCRIBE transactions").fetchall()
            expected_columns = [
                "transaction_id",
                "date",
                "time",
                "type",
                "name",
                "emoji",
                "category",
                "amount",
                "currency",
                "local_amount",
                "local_currency",
                "notes_and_tags",
                "address",
                "receipt",
                "description",
                "category_split",
            ]
            actual_columns = [row[0] for row in schema]
            assert actual_columns == expected_columns

            # Verify row count (excluding header)
            count = db_conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            assert count == 4

            # Verify data content
            rows = db_conn.execute(
                "SELECT * FROM transactions ORDER BY date"
            ).fetchall()
            assert len(rows) == 4

            # Check that we have the expected data (without assuming specific order)
            names = [row[4] for row in rows]
            assert "Costa Coffee" in names
            assert "ACME Corp Ltd" in names
            assert "Tesco Express" in names
            assert "Grocery Store" in names

            # Check for specific amounts
            amounts = [row[7] for row in rows]
            assert Decimal("2500.00") in amounts  # Salary
            assert Decimal("-4.50") in amounts  # Coffee
            assert Decimal("-25.67") in amounts  # Groceries
            assert Decimal("-45.67") in amounts  # Added grocery store

            db_conn.close()

    def test_duck_db_with_empty_data(self, monzo_instance):
        """Test duck_db method with empty data."""
        with (
            patch.object(
                type(monzo_instance),
                "data",
                new_callable=lambda: property(lambda self: []),
            ),
            pytest.raises(ValueError, match="No data available"),
        ):
            monzo_instance.duck_db()

    def test_duck_db_with_headers_only(self, monzo_instance):
        """Test duck_db method with headers only (no data rows)."""
        sample_data = [
            [
                "Transaction ID",
                "Date",
                "Time",
                "Type",
                "Name",
                "Emoji",
                "Category",
                "Amount",
                "Currency",
                "Local amount",
                "Local currency",
                "Notes and #tags",
                "Address",
                "Receipt",
                "Description",
                "Category ID",
            ]
        ]

        with patch.object(
            type(monzo_instance),
            "data",
            new_callable=lambda: property(lambda self: sample_data),
        ):
            db_conn = monzo_instance.duck_db()

            # Verify table exists but is empty
            count = db_conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            assert count == 0

            # Verify columns exist
            schema = db_conn.execute("DESCRIBE transactions").fetchall()
            expected_columns = [
                "transaction_id",
                "date",
                "time",
                "type",
                "name",
                "emoji",
                "category",
                "amount",
                "currency",
                "local_amount",
                "local_currency",
                "notes_and_tags",
                "address",
                "receipt",
                "description",
                "category_split",
            ]
            actual_columns = [row[0] for row in schema]
            assert actual_columns == expected_columns

            db_conn.close()

    def test_duck_db_with_standard_columns(self, monzo_instance):
        """Test duck_db method uses standard hardcoded column names."""
        sample_data = [
            [
                "Transaction ID",
                "Date",
                "Time",
                "Type",
                "Name",
                "Emoji",
                "Category",
                "Amount",
                "Currency",
                "Local amount",
                "Local currency",
                "Notes and #tags",
                "Address",
                "Receipt",
                "Description",
                "Category ID",
            ],
            [
                "TXN123",
                "2024-01-01",
                "10:30",
                "Payment",
                "Coffee Shop",
                "☕",
                "Food",
                "4.50",
                "GBP",
                "4.50",
                "GBP",
                "#breakfast",
                "",
                "",
                "Morning coffee",
                "cat_food",
            ],
        ]

        with patch.object(
            type(monzo_instance),
            "data",
            new_callable=lambda: property(lambda self: sample_data),
        ):
            db_conn = monzo_instance.duck_db()

            # Verify columns use standard names regardless of input headers
            schema = db_conn.execute("DESCRIBE transactions").fetchall()
            actual_columns = [row[0] for row in schema]
            expected_columns = [
                "transaction_id",
                "date",
                "time",
                "type",
                "name",
                "emoji",
                "category",
                "amount",
                "currency",
                "local_amount",
                "local_currency",
                "notes_and_tags",
                "address",
                "receipt",
                "description",
                "category_split",
            ]
            assert actual_columns == expected_columns

            # Verify data is accessible
            count = db_conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            assert count == 1

            db_conn.close()

    def test_duck_db_with_any_headers(self, monzo_instance):
        """Test duck_db method ignores input headers and uses standard columns."""
        sample_data = [
            [
                "ID",
                "Date",
                "Time",
                "Type",
                "Name",
                "Emoji",
                "Category",
                "Amount",
                "Currency",
                "Amount2",
                "Currency2",
                "Notes",
                "Address",
                "Receipt",
                "Description",
                "CategoryID",
            ],
            [
                "tx_1",
                "2024-01-01",
                "10:00",
                "Payment",
                "Coffee",
                "☕",
                "Food",
                "4.50",
                "GBP",
                "5.00",
                "GBP",
                "test",
                "",
                "",
                "Coffee purchase",
                "cat_food",
            ],
        ]

        with patch.object(
            type(monzo_instance),
            "data",
            new_callable=lambda: property(lambda self: sample_data),
        ):
            db_conn = monzo_instance.duck_db()

            # Verify columns use standard names regardless of duplicates
            schema = db_conn.execute("DESCRIBE transactions").fetchall()
            actual_columns = [row[0] for row in schema]
            expected_columns = [
                "transaction_id",
                "date",
                "time",
                "type",
                "name",
                "emoji",
                "category",
                "amount",
                "currency",
                "local_amount",
                "local_currency",
                "notes_and_tags",
                "address",
                "receipt",
                "description",
                "category_split",
            ]
            assert actual_columns == expected_columns

            db_conn.close()

    def test_duck_db_with_missing_columns(self, monzo_instance):
        """Test duck_db method handles rows with missing columns."""
        sample_data = [
            [
                "ID",
                "Date",
                "Time",
                "Type",
                "Name",
                "Emoji",
                "Category",
                "Amount",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ],
            [
                "tx_1",
                "2024-01-01",
                "10:00",
                "Payment",
                "Coffee",
                "☕",
                "Food",
                "4.50",
                "GBP",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ],
        ]

        with patch.object(
            type(monzo_instance),
            "data",
            new_callable=lambda: property(lambda self: sample_data),
        ):
            db_conn = monzo_instance.duck_db()

            # Verify standard column structure is always used
            schema = db_conn.execute("DESCRIBE transactions").fetchall()
            actual_columns = [row[0] for row in schema]
            expected_columns = [
                "transaction_id",
                "date",
                "time",
                "type",
                "name",
                "emoji",
                "category",
                "amount",
                "currency",
                "local_amount",
                "local_currency",
                "notes_and_tags",
                "address",
                "receipt",
                "description",
                "category_split",
            ]
            assert actual_columns == expected_columns

            db_conn.close()

    def test_duck_db_with_irregular_row_lengths(self, monzo_instance):
        """Test duck_db method with rows of different lengths."""
        sample_data = [
            [
                "ID",
                "Date",
                "Time",
                "Type",
                "Name",
                "Emoji",
                "Category",
                "Amount",
                "Currency",
                "Local",
                "LocalCurr",
                "Notes",
                "Address",
                "Receipt",
                "Desc",
                "CatID",
            ],
            ["tx_1", "2024-01-01"],  # Short row
            [
                "tx_2",
                "2024-01-02",
                "09:00",
                "Transfer",
                "Salary",
                "💰",
                "Income",
                "2500.00",
                "GBP",
                "2500.00",
                "GBP",
                "",
                "",
                "",
                "Monthly salary",
                "cat_income",
                "Extra",
                "TooManyColumns",
            ],  # Long row
            [
                "tx_3",
                "2024-01-03",
                "15:00",
                "Payment",
                "Store",
                "🛒",
                "Shopping",
                "-45.67",
                "GBP",
                "-45.67",
                "GBP",
                "",
                "",
                "",
                "Shopping",
                "cat_shopping",
            ],  # Normal row
        ]

        with patch.object(
            type(monzo_instance),
            "data",
            new_callable=lambda: property(lambda self: sample_data),
        ):
            db_conn = monzo_instance.duck_db()

            # Verify all rows are handled
            count = db_conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            assert count == 3

            # Verify data integrity
            rows = db_conn.execute(
                "SELECT * FROM transactions ORDER BY date"
            ).fetchall()
            assert len(rows) == 3

            # Short row should be padded with None
            assert rows[0][7] is None  # Amount column should be None

            # Long row should be truncated to match 16 standard columns
            assert len(rows[1]) == 16  # Should only have 16 columns

            db_conn.close()
