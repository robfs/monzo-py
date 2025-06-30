"""Integration tests for monzo-py.

This package contains integration tests that connect to live external services.
These tests are separate from unit tests and require:

- Valid credentials for external services
- Network connectivity
- Specific environment variables to be set
- Longer execution times

Run integration tests with:
    ENABLE_LIVE_TESTS=1 pytest integration/ -v

Or run specific integration test files:
    ENABLE_LIVE_TESTS=1 pytest integration/test_live_monzo.py -v
"""
