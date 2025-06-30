#!/usr/bin/env python3
"""Tests to validate live data characteristics from the Google Spreadsheet.

These tests run against the actual live data to ensure the data structure
and content meet expectations for the MonzoTransactions class.
"""

import os
from datetime import date

import pytest

from monzo_py import MonzoTransactions


class TestLiveDataValidation:
    """Tests to validate live data structure and content."""

    @pytest.fixture(scope="class")
    def live_spreadsheet_id(self):
        """Get the live spreadsheet ID."""
        return os.getenv("TEST_SPREADSHEET_ID")

    @pytest.fixture(scope="class")
    def live_monzo_instance(self, live_spreadsheet_id):
        """Create a MonzoTransactions instance for live data testing."""
        return MonzoTransactions(live_spreadsheet_id)

    @pytest.fixture(scope="class")
    def live_data(self, live_monzo_instance):
        """Fetch live data once for all tests."""
        return live_monzo_instance.data

    @pytest.fixture(scope="class")
    def live_db_conn(self, live_monzo_instance):
        """Create a DuckDB connection with live data."""
        conn = live_monzo_instance.duck_db()
        yield conn
        conn.close()

    @pytest.mark.skipif(
        not os.getenv("ENABLE_LIVE_TESTS"),
        reason="Live tests disabled - set ENABLE_LIVE_TESTS=1 to enable",
    )
    def test_live_data_structure(self, live_data):
        """Test that live data has the expected structure."""
        assert len(live_data) > 0, "Should have at least header row"

        # Check header structure
        headers = live_data[0]
        expected_headers = [
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
            "Category split",
        ]

        assert len(headers) == 16, f"Expected 16 headers, got {len(headers)}"

        for i, (actual, expected) in enumerate(
            zip(headers, expected_headers, strict=False)
        ):
            assert actual == expected, (
                f"Header {i + 1} mismatch: '{actual}' != '{expected}'"
            )

    @pytest.mark.skipif(
        not os.getenv("ENABLE_LIVE_TESTS"),
        reason="Live tests disabled - set ENABLE_LIVE_TESTS=1 to enable",
    )
    def test_live_data_content(self, live_data):
        """Test that live data contains valid transaction data."""
        assert len(live_data) > 1, "Should have data rows beyond header"

        # Test data rows
        data_rows = live_data[1:]
        assert len(data_rows) > 100, (
            "Should have substantial amount of transaction data"
        )

        # Test that most rows have transaction IDs
        rows_with_tx_id = sum(1 for row in data_rows if len(row) > 0 and row[0])
        assert rows_with_tx_id > len(data_rows) * 0.99, (
            "Most rows should have transaction IDs"
        )

    @pytest.mark.skipif(
        not os.getenv("ENABLE_LIVE_TESTS"),
        reason="Live tests disabled - set ENABLE_LIVE_TESTS=1 to enable",
    )
    def test_live_duckdb_schema(self, live_db_conn):
        """Test that DuckDB schema matches expectations."""
        schema = live_db_conn.execute("DESCRIBE transactions").fetchall()

        expected_schema = [
            ("transaction_id", "VARCHAR"),
            ("date", "DATE"),
            ("time", "TIME"),
            ("type", "VARCHAR"),
            ("name", "VARCHAR"),
            ("emoji", "VARCHAR"),
            ("category", "VARCHAR"),
            ("amount", "DECIMAL(10,2)"),
            ("currency", "VARCHAR"),
            ("local_amount", "DECIMAL(10,2)"),
            ("local_currency", "VARCHAR"),
            ("notes_and_tags", "VARCHAR"),
            ("address", "VARCHAR"),
            ("receipt", "VARCHAR"),
            ("description", "VARCHAR"),
            (
                "category_split",
                "VARCHAR",
            ),  # Note: DuckDB uses category_split to match live data header
        ]

        assert len(schema) == len(expected_schema), (
            f"Expected {len(expected_schema)} columns, got {len(schema)}"
        )

        for i, (actual, expected) in enumerate(
            zip(schema, expected_schema, strict=False)
        ):
            assert actual[0] == expected[0], (
                f"Column {i + 1} name mismatch: '{actual[0]}' != '{expected[0]}'"
            )
            assert actual[1] == expected[1], (
                f"Column {i + 1} type mismatch: '{actual[1]}' != '{expected[1]}'"
            )

    @pytest.mark.skipif(
        not os.getenv("ENABLE_LIVE_TESTS"),
        reason="Live tests disabled - set ENABLE_LIVE_TESTS=1 to enable",
    )
    def test_live_transaction_types(self, live_db_conn):
        """Test that live data contains expected transaction types."""
        types = live_db_conn.execute("""
            SELECT type, COUNT(*) as count
            FROM transactions
            WHERE type IS NOT NULL AND type != ''
            GROUP BY type
            ORDER BY count DESC
        """).fetchall()

        assert len(types) > 0, "Should have transaction types"

        type_names = [t[0] for t in types]

        # Expected transaction types based on live data analysis
        expected_types = [
            "Card payment",
            "Faster payment",
            "Monzo-to-Monzo",
        ]

        for expected_type in expected_types:
            assert expected_type in type_names, (
                f"Expected transaction type '{expected_type}' not found"
            )

        # Most common type should be Card payment
        assert types[0][0] == "Card payment", (
            "Card payment should be most common transaction type"
        )
        assert types[0][1] > 1000, "Should have many card payments"

    @pytest.mark.skipif(
        not os.getenv("ENABLE_LIVE_TESTS"),
        reason="Live tests disabled - set ENABLE_LIVE_TESTS=1 to enable",
    )
    def test_live_categories(self, live_db_conn):
        """Test that live data contains expected categories."""
        categories = live_db_conn.execute("""
            SELECT category, COUNT(*) as count
            FROM transactions
            WHERE category IS NOT NULL AND category != ''
            GROUP BY category
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()

        assert len(categories) > 0, "Should have transaction categories"

        category_names = [c[0] for c in categories]

        # Expected categories based on live data analysis
        expected_categories = [
            "Groceries",
            "Eating out",
            "Coffee shop",
            "Transport",
        ]

        for expected_category in expected_categories:
            assert expected_category in category_names, (
                f"Expected category '{expected_category}' not found"
            )

    @pytest.mark.skipif(
        not os.getenv("ENABLE_LIVE_TESTS"),
        reason="Live tests disabled - set ENABLE_LIVE_TESTS=1 to enable",
    )
    def test_live_data_quality(self, live_db_conn):
        """Test data quality characteristics."""
        # Test for required fields
        total_count = live_db_conn.execute(
            "SELECT COUNT(*) FROM transactions"
        ).fetchone()[0]

        # Transaction ID should be present for all records
        null_tx_ids = live_db_conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE transaction_id IS NULL OR transaction_id = ''"
        ).fetchone()[0]
        assert null_tx_ids == 0, "All transactions should have transaction IDs"

        # Date should be present for all records
        null_dates = live_db_conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE date IS NULL"
        ).fetchone()[0]
        assert null_dates == 0, "All transactions should have dates"

        # Amount should be present for all records
        null_amounts = live_db_conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE amount IS NULL"
        ).fetchone()[0]
        assert null_amounts == 0, "All transactions should have amounts"

        # Currency should be mostly GBP
        gbp_count = live_db_conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE currency = 'GBP'"
        ).fetchone()[0]
        assert gbp_count > total_count * 0.95, "Most transactions should be in GBP"

    @pytest.mark.skipif(
        not os.getenv("ENABLE_LIVE_TESTS"),
        reason="Live tests disabled - set ENABLE_LIVE_TESTS=1 to enable",
    )
    def test_live_date_range(self, live_db_conn):
        """Test that date range is reasonable."""
        date_range = live_db_conn.execute("""
            SELECT MIN(date) as earliest, MAX(date) as latest
            FROM transactions
            WHERE date IS NOT NULL
        """).fetchone()

        earliest_date = date_range[0]
        latest_date = date_range[1]

        assert earliest_date is not None, "Should have earliest date"
        assert latest_date is not None, "Should have latest date"

        # Check that dates are reasonable (within last 10 years to today)
        today = date.today()
        ten_years_ago = date(today.year - 10, today.month, today.day)

        assert earliest_date >= ten_years_ago, (
            f"Earliest date {earliest_date} seems too old"
        )
        assert latest_date <= today, f"Latest date {latest_date} is in the future"
        assert latest_date > earliest_date, "Latest date should be after earliest date"

    @pytest.mark.skipif(
        not os.getenv("ENABLE_LIVE_TESTS"),
        reason="Live tests disabled - set ENABLE_LIVE_TESTS=1 to enable",
    )
    def test_live_amount_distribution(self, live_db_conn):
        """Test that amount distribution is reasonable."""
        amount_stats = live_db_conn.execute("""
            SELECT
                MIN(amount) as min_amount,
                MAX(amount) as max_amount,
                AVG(amount) as avg_amount,
                COUNT(CASE WHEN amount > 0 THEN 1 END) as positive_count,
                COUNT(CASE WHEN amount < 0 THEN 1 END) as negative_count,
                COUNT(CASE WHEN amount = 0 THEN 1 END) as zero_count,
                COUNT(*) as total_count
            FROM transactions
            WHERE amount IS NOT NULL
        """).fetchone()

        min_amount = amount_stats[0]
        max_amount = amount_stats[1]
        # avg_amount = amount_stats[2]  # Unused variable
        positive_count = amount_stats[3]
        negative_count = amount_stats[4]
        # zero_count = amount_stats[5]  # Unused variable
        total_count = amount_stats[6]

        # Basic sanity checks
        assert min_amount < 0, "Should have negative amounts (payments)"
        assert max_amount > 0, "Should have positive amounts (income)"
        assert negative_count > positive_count, "Should have more payments than income"

        # Reasonable ranges for personal finance data
        assert min_amount >= -100000, "Minimum amount seems unreasonably low"
        assert max_amount <= 100000, "Maximum amount seems unreasonably high"

        # Most transactions should be negative (spending)
        assert negative_count > total_count * 0.7, (
            "Most transactions should be spending (negative)"
        )

    @pytest.mark.skipif(
        not os.getenv("ENABLE_LIVE_TESTS"),
        reason="Live tests disabled - set ENABLE_LIVE_TESTS=1 to enable",
    )
    def test_live_merchant_data(self, live_db_conn):
        """Test merchant/name data quality."""
        # Test that we have merchant names for most card payments
        card_payments_with_names = live_db_conn.execute("""
            SELECT COUNT(*) FROM transactions
            WHERE type = 'Card payment' AND name IS NOT NULL AND name != ''
        """).fetchone()[0]

        total_card_payments = live_db_conn.execute("""
            SELECT COUNT(*) FROM transactions
            WHERE type = 'Card payment'
        """).fetchone()[0]

        if total_card_payments > 0:
            name_percentage = card_payments_with_names / total_card_payments
            assert name_percentage > 0.8, (
                "Most card payments should have merchant names"
            )

    @pytest.mark.skipif(
        not os.getenv("ENABLE_LIVE_TESTS"),
        reason="Live tests disabled - set ENABLE_LIVE_TESTS=1 to enable",
    )
    def test_live_data_consistency(self, live_db_conn):
        """Test data consistency across related fields."""
        # Test that amount and local_amount are consistent for GBP transactions
        inconsistent_amounts = live_db_conn.execute("""
            SELECT COUNT(*) FROM transactions
            WHERE currency = 'GBP'
            AND local_currency = 'GBP'
            AND amount != local_amount
        """).fetchone()[0]

        # Allow for small number of inconsistencies (e.g., rounding differences)
        total_gbp_transactions = live_db_conn.execute("""
            SELECT COUNT(*) FROM transactions
            WHERE currency = 'GBP' AND local_currency = 'GBP'
        """).fetchone()[0]

        if total_gbp_transactions > 0:
            inconsistency_rate = inconsistent_amounts / total_gbp_transactions
            assert inconsistency_rate < 0.01, (
                f"Too many inconsistencies: {inconsistent_amounts}/{total_gbp_transactions} "
                f"({inconsistency_rate:.2%}) - should be < 1%"
            )
        else:
            assert inconsistent_amounts == 0, (
                "Amount and local_amount should match for GBP transactions"
            )

        # Test that time format is consistent
        valid_times = live_db_conn.execute("""
            SELECT COUNT(*) FROM transactions
            WHERE time IS NOT NULL
        """).fetchone()[0]

        total_transactions = live_db_conn.execute(
            "SELECT COUNT(*) FROM transactions"
        ).fetchone()[0]

        # Most transactions should have valid time data
        if total_transactions > 0:
            time_percentage = valid_times / total_transactions
            assert time_percentage > 0.9, (
                "Most transactions should have valid time data"
            )

    @pytest.mark.skipif(
        not os.getenv("ENABLE_LIVE_TESTS"),
        reason="Live tests disabled - set ENABLE_LIVE_TESTS=1 to enable",
    )
    def test_analytical_queries_work(self, live_db_conn):
        """Test that common analytical queries work correctly."""
        # Monthly spending analysis
        monthly_spending = live_db_conn.execute("""
            SELECT
                strftime('%Y-%m', date) as month,
                SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END) as spending,
                COUNT(*) as transaction_count
            FROM transactions
            WHERE date >= current_date - INTERVAL '12 months'
            GROUP BY strftime('%Y-%m', date)
            ORDER BY month DESC
            LIMIT 12
        """).fetchall()

        assert len(monthly_spending) > 0, "Should have monthly spending data"

        # Category breakdown
        category_spending = live_db_conn.execute("""
            SELECT
                category,
                SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END) as total_spending,
                COUNT(*) as transaction_count
            FROM transactions
            WHERE amount < 0 AND category IS NOT NULL AND category != ''
            GROUP BY category
            ORDER BY total_spending ASC
            LIMIT 10
        """).fetchall()

        assert len(category_spending) > 0, "Should have category spending data"

        # Top merchants
        top_merchants = live_db_conn.execute("""
            SELECT
                name,
                COUNT(*) as visit_count,
                SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END) as total_spent
            FROM transactions
            WHERE amount < 0 AND name IS NOT NULL AND name != ''
            GROUP BY name
            ORDER BY visit_count DESC
            LIMIT 10
        """).fetchall()

        assert len(top_merchants) > 0, "Should have top merchants data"
