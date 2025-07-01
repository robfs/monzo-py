#!/usr/bin/env python3
"""Unit tests for MonzoTransactions functionality using mocked Google Sheets API.

These tests use mocks instead of live external services to ensure:
- Fast execution
- Reliable results
- No external dependencies
- Predictable test data
- Isolated testing of core functionality
"""

from unittest.mock import Mock
from unittest.mock import patch

import pytest

from monzo_py import MonzoTransactions


class TestMonzoTransactionsMocked:
    """Unit tests for MonzoTransactions with mocked Google Sheets API."""

    @patch("monzo_py.monzo_transactions.build")
    def test_data_fetch_mocked(self, mock_build, mock_google_sheets_service):
        """Test data fetching with mocked Google Sheets API."""
        mock_build.return_value = mock_google_sheets_service

        monzo = MonzoTransactions("test_spreadsheet_id")
        data = monzo.data

        assert len(data) == 4, "Should return header + 3 data rows"
        assert data[0][0] == "Transaction ID", "First column should be Transaction ID"
        assert data[1][4] == "Costa Coffee", "Should have correct merchant name"
        assert data[2][7] == "2500.00", "Should have correct amount"

    @patch("monzo_py.monzo_transactions.build")
    def test_duckdb_integration_mocked(self, mock_build, mock_google_sheets_service):
        """Test DuckDB integration with mocked data."""
        mock_build.return_value = mock_google_sheets_service
        monzo = MonzoTransactions("test_spreadsheet_id")
        db_conn = monzo.duck_db()

        try:
            # Test basic queries
            count_result = db_conn.execute(
                "SELECT COUNT(*) FROM transactions"
            ).fetchone()
            assert count_result is not None, "Count query should return a result"
            assert count_result[0] == 3, "Should have 3 data rows (excluding header)"

            # Test schema
            schema_result = db_conn.execute("DESCRIBE transactions").fetchall()
            assert len(schema_result) >= 10, "Should have expected number of columns"

            # Test specific data
            coffee_result = db_conn.execute("""
                SELECT name, amount FROM transactions
                WHERE name = 'Costa Coffee'
            """).fetchone()
            assert coffee_result is not None, "Coffee query should return a result"
            assert coffee_result[0] == "Costa Coffee"
            assert coffee_result[1] == -4.50

            salary_result = db_conn.execute("""
                SELECT name, amount FROM transactions
                WHERE name = 'ACME Corp Ltd'
            """).fetchone()
            assert salary_result is not None, "Salary query should return a result"
            assert salary_result[0] == "ACME Corp Ltd"
            assert salary_result[1] == 2500.00

        finally:
            db_conn.close()

    @patch("monzo_py.monzo_transactions.build")
    def test_analytical_queries_mocked(self, mock_build, mock_google_sheets_service):
        """Test analytical queries with mocked Google Sheets data."""
        mock_build.return_value = mock_google_sheets_service

        monzo = MonzoTransactions("test_spreadsheet_id")
        db_conn = monzo.duck_db()

        try:
            # Test date range
            date_range = db_conn.execute("""
                SELECT MIN(date) as earliest, MAX(date) as latest
                FROM transactions
                WHERE date IS NOT NULL
            """).fetchone()
            assert date_range is not None, "Date range query should return a result"
            assert str(date_range[0]) == "2025-06-15"
            assert str(date_range[1]) == "2025-06-17"

            # Test transaction types
            types = db_conn.execute("""
                SELECT type, COUNT(*) as count
                FROM transactions
                WHERE type IS NOT NULL AND type != ''
                GROUP BY type
                ORDER BY count DESC
            """).fetchall()

            type_names = [t[0] for t in types]
            assert "Card payment" in type_names
            assert "Faster payment" in type_names

            # Test categories
            categories = db_conn.execute("""
                SELECT category, COUNT(*) as count
                FROM transactions
                WHERE category IS NOT NULL AND category != ''
                GROUP BY category
                ORDER BY count DESC
            """).fetchall()

            category_names = [c[0] for c in categories]
            assert "Coffee shop" in category_names
            assert "Income" in category_names
            assert "Groceries" in category_names

            # Test amount statistics
            amount_stats = db_conn.execute("""
                SELECT
                    COUNT(*) as total_rows,
                    COUNT(amount) as non_null_amounts,
                    SUM(CASE WHEN amount > 0 THEN 1 ELSE 0 END) as positive_amounts,
                    SUM(CASE WHEN amount < 0 THEN 1 ELSE 0 END) as negative_amounts
                FROM transactions
            """).fetchone()
            assert amount_stats is not None, "Amount stats query should return a result"

            assert amount_stats[0] == 3  # total rows
            assert amount_stats[1] == 3  # non-null amounts
            assert amount_stats[2] == 1  # positive amounts (salary)
            assert amount_stats[3] == 2  # negative amounts (coffee + groceries)

        finally:
            db_conn.close()

    @patch("monzo_py.monzo_transactions.build")
    def test_empty_data_handling(self, mock_build):
        """Test handling of empty or minimal data."""
        mock_service = Mock()
        mock_sheet = Mock()
        mock_values = Mock()

        mock_build.return_value = mock_service
        mock_service.spreadsheets.return_value = mock_sheet
        mock_sheet.values.return_value = mock_values
        mock_values.get.return_value.execute.return_value = {
            "values": [["Header1", "Header2", "Header3"]]
        }

        monzo = MonzoTransactions("test_spreadsheet_id")
        data = monzo.data

        assert len(data) == 1, "Should handle empty data gracefully"
        assert data[0] == ["Header1", "Header2", "Header3"]

        # Test DuckDB with empty data
        db_conn = monzo.duck_db()
        try:
            count_result = db_conn.execute(
                "SELECT COUNT(*) FROM transactions"
            ).fetchone()
            assert count_result is not None, "Count query should return a result"
            assert count_result[0] == 0, "Should have no data rows"
        finally:
            db_conn.close()

    @patch("monzo_py.monzo_transactions.build")
    def test_api_error_handling(self, mock_build):
        """Test handling of API errors."""
        mock_service = Mock()
        mock_sheet = Mock()
        mock_values = Mock()

        mock_build.return_value = mock_service
        mock_service.spreadsheets.return_value = mock_sheet
        mock_sheet.values.return_value = mock_values
        mock_values.get.return_value.execute.side_effect = Exception("API Error")

        monzo = MonzoTransactions("test_spreadsheet_id")
        with pytest.raises(Exception, match="API Error"):
            _ = monzo.data

    @patch("monzo_py.monzo_transactions.build")
    def test_malformed_data_handling(self, mock_build):
        """Test handling of malformed data."""
        malformed_data = [
            ["Header1", "Header2", "Header3", "Header4"],
            ["Data1", "Data2"],
            ["Data3", "Data4", "Data5", "Data6", "Data7"],
        ]

        mock_service = Mock()
        mock_sheet = Mock()
        mock_values = Mock()

        mock_build.return_value = mock_service
        mock_service.spreadsheets.return_value = mock_sheet
        mock_sheet.values.return_value = mock_values
        mock_values.get.return_value.execute.return_value = {"values": malformed_data}

        monzo = MonzoTransactions("test_spreadsheet_id")
        data = monzo.data

        assert len(data) == 3, "Should handle malformed data"

        db_conn = monzo.duck_db()
        try:
            count_result = db_conn.execute(
                "SELECT COUNT(*) FROM transactions"
            ).fetchone()
            assert count_result is not None, "Count query should return a result"
            assert count_result[0] == 2, "Should have 2 data rows"
        finally:
            db_conn.close()

    def test_multiple_instances_independence(self, sample_transaction_data):
        """Test that multiple instances work independently."""
        with patch("monzo_py.monzo_transactions.build") as mock_build:
            mock_service1 = Mock()
            mock_sheet1 = Mock()
            mock_values1 = Mock()
            mock_values1.get.return_value.execute.return_value = {
                "values": sample_transaction_data
            }
            mock_service1.spreadsheets.return_value = mock_sheet1
            mock_sheet1.values.return_value = mock_values1

            mock_service2 = Mock()
            mock_sheet2 = Mock()
            mock_values2 = Mock()
            mock_values2.get.return_value.execute.return_value = {
                "values": [["Different", "Data"], ["Row1", "Row2"]]
            }
            mock_service2.spreadsheets.return_value = mock_sheet2
            mock_sheet2.values.return_value = mock_values2

            mock_build.side_effect = [mock_service1, mock_service2]

            monzo1 = MonzoTransactions("spreadsheet1")
            monzo2 = MonzoTransactions("spreadsheet2")

            data1 = monzo1.data
            data2 = monzo2.data

            assert len(data1) == 4
            assert len(data2) == 2
            assert data1[0][0] == "Transaction ID"
            assert data2[0][0] == "Different"
