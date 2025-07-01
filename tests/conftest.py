"""Shared pytest fixtures for the test suite."""

import os
import tempfile
from unittest.mock import Mock

import pytest
from google.oauth2.credentials import Credentials

from monzo_py import MonzoTransactions


def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "live: mark test as requiring live external services"
    )
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


@pytest.fixture
def temp_credentials_file():
    """Create a temporary credentials file for testing."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as temp_creds:
        temp_creds.write('{"test": "credentials"}')
        temp_creds.flush()
        temp_creds_path = temp_creds.name

    yield temp_creds_path

    # Cleanup
    if os.path.exists(temp_creds_path):
        os.unlink(temp_creds_path)


@pytest.fixture
def mock_credentials():
    """Create a mock Credentials object."""
    credentials = Mock(spec=Credentials)
    credentials.to_json.return_value = '{"token": "test_token"}'
    return credentials


@pytest.fixture
def sample_transaction_data():
    """Provide sample transaction data for testing that matches live data structure."""
    return [
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
            "Category split",
        ],
        [
            "tx_00009R5jgIR0O6ricjZJwn",
            "15/06/2025",
            "09:30:15",
            "Card payment",
            "Costa Coffee",
            "☕",
            "Coffee shop",
            "-4.50",
            "GBP",
            "-4.50",
            "GBP",
            "#coffee #morning",
            "123 High Street, London",
            "",
            "COSTA COFFEE         LONDON   GBR",
            "",
        ],
        [
            "tx_00009R5tJnb9M6SSasNGu9",
            "16/06/2025",
            "09:00:00",
            "Faster payment",
            "ACME Corp Ltd",
            "💰",
            "Income",
            "2500.00",
            "GBP",
            "2500.00",
            "GBP",
            "Monthly salary payment",
            "",
            "",
            "SALARY PAYMENT - JUNE 2025",
            "",
        ],
        [
            "tx_00009R61meoPtrMZNLqquH",
            "17/06/2025",
            "14:22:10",
            "Card payment",
            "Tesco Express",
            "🛒",
            "Groceries",
            "-25.67",
            "GBP",
            "-25.67",
            "GBP",
            "",
            "456 Main Road, London",
            "",
            "TESCO EXPRESS        LONDON   GBR",
            "",
        ],
    ]


@pytest.fixture
def monzo_instance(temp_credentials_file):
    """Create a standard MonzoTransactions instance for testing."""
    return MonzoTransactions(
        spreadsheet_id="test_spreadsheet_id",
        sheet="test_sheet",
        range_start="A1",
        range_end="Z100",
        credentials_path=temp_credentials_file,
    )
