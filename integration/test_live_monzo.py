#!/usr/bin/env python3
"""Integration tests for MonzoTransactions with live Google Sheets API.

These tests connect to real external services and should be run separately
from the main test suite. They require:
- Valid Google Sheets API credentials
- Network connectivity
- ENABLE_LIVE_TESTS environment variable

Run with: ENABLE_LIVE_TESTS=1 TEST_SPREADSHEET_ID=<spreadsheet_id> pytest integration/test_live_monzo.py -v
"""

import logging
import os

import pytest

from monzo_py import MonzoTransactions


@pytest.fixture(scope="module")
def live_spreadsheet_id():
    """Get the spreadsheet ID for live testing."""
    # Use environment variable if set, otherwise use the known test spreadsheet
    return os.getenv("TEST_SPREADSHEET_ID")


@pytest.fixture(scope="module")
def live_monzo_instance(live_spreadsheet_id):
    """Create a MonzoTransactions instance for live testing."""
    return MonzoTransactions(live_spreadsheet_id)


class TestLiveMonzoIntegration:
    """Integration tests for MonzoTransactions with live Google Sheets."""

    @pytest.mark.live
    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skipif(
        not os.getenv("ENABLE_LIVE_TESTS"),
        reason="Live tests disabled - set ENABLE_LIVE_TESTS=1 to enable",
    )
    def test_live_data_fetch(self, live_monzo_instance):
        """Test fetching data from live Google Sheets."""
        data = live_monzo_instance.data

        assert len(data) > 0, "Should fetch at least header row"
        assert isinstance(data, list), "Data should be a list"
        assert isinstance(data[0], list), "Each row should be a list"

        # Log some basic info (but don't assert specific values)
        logging.info(f"Fetched {len(data)} rows from live spreadsheet")
        if len(data) > 1:
            logging.info(f"First data row has {len(data[1])} columns")

    @pytest.mark.live
    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skipif(
        not os.getenv("ENABLE_LIVE_TESTS"),
        reason="Live tests disabled - set ENABLE_LIVE_TESTS=1 to enable",
    )
    def test_live_duckdb_integration(self, live_monzo_instance):
        """Test DuckDB integration with live data."""
        db_conn = live_monzo_instance.duck_db()

        try:
            # Test basic table exists and has data
            count_result = db_conn.execute(
                "SELECT COUNT(*) FROM transactions"
            ).fetchone()
            assert count_result[0] >= 0, "Should return a valid count"

            # Test table schema
            schema_result = db_conn.execute("DESCRIBE transactions").fetchall()
            assert len(schema_result) > 0, "Table should have columns"

            logging.info(f"Live database has {count_result[0]} transactions")
            logging.info(f"Table schema has {len(schema_result)} columns")

            # Test basic queries don't crash
            db_conn.execute("SELECT * FROM transactions LIMIT 1").fetchall()

        finally:
            db_conn.close()

    @pytest.mark.live
    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skipif(
        not os.getenv("ENABLE_LIVE_TESTS"),
        reason="Live tests disabled - set ENABLE_LIVE_TESTS=1 to enable",
    )
    def test_live_analytical_queries(self, live_monzo_instance):
        """Test analytical queries on live data."""
        db_conn = live_monzo_instance.duck_db()

        try:
            # Test date range query (should not crash)
            date_range = db_conn.execute("""
                SELECT MIN(date) as earliest, MAX(date) as latest
                FROM transactions
                WHERE date IS NOT NULL
            """).fetchone()

            # Don't assert specific dates, just that query works
            logging.info(f"Live data date range: {date_range}")

            # Test grouping queries
            types = db_conn.execute("""
                SELECT type, COUNT(*) as count
                FROM transactions
                WHERE type IS NOT NULL AND type != ''
                GROUP BY type
                ORDER BY count DESC
                LIMIT 5
            """).fetchall()

            assert isinstance(types, list), "Should return a list of results"
            logging.info(f"Found {len(types)} transaction types in live data")

            # Test amount analysis
            amount_stats = db_conn.execute("""
                SELECT
                    COUNT(*) as total_rows,
                    COUNT(amount) as non_null_amounts
                FROM transactions
            """).fetchone()

            assert amount_stats[0] >= 0, "Should have valid row count"
            assert amount_stats[1] >= 0, "Should have valid amount count"

            logging.info(
                f"Live data: {amount_stats[1]} non-null amounts out of {amount_stats[0]} total rows"
            )

        finally:
            db_conn.close()

    @pytest.mark.live
    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skipif(
        not os.getenv("ENABLE_LIVE_TESTS"),
        reason="Live tests disabled - set ENABLE_LIVE_TESTS=1 to enable",
    )
    def test_live_connection_handling(self, live_spreadsheet_id):
        """Test connection handling and cleanup."""
        # Create and destroy multiple instances to test cleanup
        instance1 = MonzoTransactions(live_spreadsheet_id)
        data1 = instance1.data
        assert len(data1) > 0

        instance2 = MonzoTransactions(live_spreadsheet_id)
        data2 = instance2.data
        assert len(data2) > 0

        # Both should work independently
        assert len(data1) == len(data2), "Should get same data from multiple instances"


# Standalone test runner for development
def main():
    """Run live tests directly for development/debugging."""
    if not os.getenv("ENABLE_LIVE_TESTS"):
        print("Set ENABLE_LIVE_TESTS=1 to run live integration tests")
        return 1

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("Running Live MonzoTransactions Integration Tests")
    print("=" * 60)

    # Run tests
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "live"])


if __name__ == "__main__":
    exit(main())
