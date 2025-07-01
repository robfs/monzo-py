#!/usr/bin/env python3
"""Integration tests for MonzoTransactions with live Google Sheets API.

These tests focus on integration aspects and API connectivity.
For comprehensive live data validation, see test_live_data_validation.py.

Run with: ENABLE_LIVE_TESTS=1 TEST_SPREADSHEET_ID=<spreadsheet_id> pytest integration/test_live_monzo.py -v
"""

import logging
import os

import pytest

from monzo_py import MonzoTransactions


@pytest.fixture(scope="module")
def live_spreadsheet_id():
    """Get the spreadsheet ID for live testing."""
    return os.getenv("TEST_SPREADSHEET_ID")


@pytest.fixture(scope="module")
def live_monzo_instance(live_spreadsheet_id):
    """Create a MonzoTransactions instance for live testing."""
    return MonzoTransactions(live_spreadsheet_id)


class TestLiveMonzoIntegration:
    """Integration tests for MonzoTransactions with live Google Sheets."""

    @pytest.mark.live
    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.getenv("ENABLE_LIVE_TESTS"),
        reason="Live tests disabled - set ENABLE_LIVE_TESTS=1 to enable",
    )
    def test_api_connectivity(self, live_monzo_instance):
        """Test basic API connectivity and data structure."""
        data = live_monzo_instance.data

        assert len(data) > 0, "Should fetch at least header row"
        assert isinstance(data, list), "Data should be a list"
        assert isinstance(data[0], list), "Each row should be a list"

        logging.info(f"API connectivity test: fetched {len(data)} rows")

    @pytest.mark.live
    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.getenv("ENABLE_LIVE_TESTS"),
        reason="Live tests disabled - set ENABLE_LIVE_TESTS=1 to enable",
    )
    def test_duckdb_integration(self, live_monzo_instance):
        """Test DuckDB integration with live data."""
        db_conn = live_monzo_instance.duck_db()

        try:
            count_result = db_conn.execute(
                "SELECT COUNT(*) FROM transactions"
            ).fetchone()
            assert count_result[0] >= 0, "Should return a valid count"

            schema_result = db_conn.execute("DESCRIBE transactions").fetchall()
            assert len(schema_result) > 0, "Table should have columns"

            db_conn.execute("SELECT * FROM transactions LIMIT 1").fetchall()
            logging.info(
                f"DuckDB integration test: {count_result[0]} transactions loaded"
            )

        finally:
            db_conn.close()

    @pytest.mark.live
    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.getenv("ENABLE_LIVE_TESTS"),
        reason="Live tests disabled - set ENABLE_LIVE_TESTS=1 to enable",
    )
    def test_connection_handling(self, live_spreadsheet_id):
        """Test connection handling and cleanup."""
        instance1 = MonzoTransactions(live_spreadsheet_id)
        data1 = instance1.data
        assert len(data1) > 0

        instance2 = MonzoTransactions(live_spreadsheet_id)
        data2 = instance2.data
        assert len(data2) > 0

        assert len(data1) == len(data2), "Should get same data from multiple instances"


def main():
    """Run integration tests directly for development/debugging."""
    if not os.getenv("ENABLE_LIVE_TESTS"):
        print("Set ENABLE_LIVE_TESTS=1 to run live integration tests")
        return 1

    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    print("Running Live MonzoTransactions Integration Tests")
    pytest.main([__file__, "-v", "-s", "-m", "live"])


if __name__ == "__main__":
    exit(main())
