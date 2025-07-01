# Testing Guide for monzo-py

This document explains the testing structure and best practices for the monzo-py project.

## Test Structure

The project follows testing best practices by separating different types of tests:

```
monzo-py/
├── tests/                  # Unit tests (fast, mocked)
│   ├── __init__.py
│   ├── conftest.py        # Shared test fixtures
│   ├── test_monzo_transactions.py
│   ├── test_duck_db.py
│   └── test_live_data.py  # Unit tests with mocks
├── integration/           # Integration tests (slow, live services)
│   ├── __init__.py
│   └── test_live_monzo.py # Live API tests
└── pytest.ini           # Test configuration
```

## Test Categories

### Unit Tests (`tests/`)
- **Fast execution** (< 1 second each)
- **No external dependencies** (use mocks/stubs)
- **Predictable results** (same input = same output)
- **Run on every commit/PR**

### Integration Tests (`integration/`)
- **Slow execution** (seconds to minutes)
- **Use live external services** (Google Sheets API)
- **Require credentials and network**
- **Run manually or in staging**

## Running Tests

### Quick Start - Unit Tests Only
```bash
# Run all unit tests (fast, no external services)
pytest

# Run with coverage
pytest --cov=monzo_transactions --cov-report=term-missing
```

### Unit Tests by Category
```bash
# Run only unit tests (excluding integration/live tests)
pytest -m "not live and not integration"

# Run only fast tests
pytest -m "not slow"

# Run specific test file
pytest tests/test_monzo_transactions.py
```

### Integration Tests (Live Services)
```bash
# Enable live tests and run integration suite
ENABLE_LIVE_TESTS=1 pytest integration/ -v

# Run specific integration test
ENABLE_LIVE_TESTS=1 pytest integration/test_live_monzo.py -v

# Run live tests with custom spreadsheet
MONZO_SPREADSHEET_ID="your_spreadsheet_id" ENABLE_LIVE_TESTS=1 pytest integration/
```

### All Tests
```bash
# Run everything (unit + integration)
ENABLE_LIVE_TESTS=1 pytest tests/ integration/ -v
```

## Test Markers

Tests are marked with pytest markers to enable flexible test selection:

- `@pytest.mark.unit` - Unit tests (fast, mocked)
- `@pytest.mark.integration` - Integration tests (live services)
- `@pytest.mark.live` - Tests requiring live external services
- `@pytest.mark.slow` - Slow-running tests

## Environment Variables

### Required for Integration Tests
- `ENABLE_LIVE_TESTS=1` - Must be set to run integration tests
- `MONZO_SPREADSHEET_ID` - (Optional) Custom spreadsheet ID for testing

### Example Integration Test Run
```bash
# Set environment and run
export ENABLE_LIVE_TESTS=1
export MONZO_SPREADSHEET_ID=<spreadsheet_id>
pytest integration/test_live_monzo.py -v -s
```

## Writing New Tests

### Unit Tests
When adding new functionality, write unit tests that:

```python
import pytest
from unittest.mock import Mock, patch

@patch('monzo_transactions.build')  # Mock external API
def test_your_feature(mock_build):
    # Setup mocks
    mock_service = Mock()
    mock_build.return_value = mock_service

    # Test your code
    result = your_function()

    # Assert results
    assert result == expected_value
```

### Integration Tests
For testing actual API integration:

```python
@pytest.mark.live
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skipif(
    not os.getenv("ENABLE_LIVE_TESTS"),
    reason="Live tests disabled - set ENABLE_LIVE_TESTS=1 to enable"
)
def test_live_feature(live_monzo_instance):
    # Test with real API
    result = live_monzo_instance.some_method()
    assert result is not None
```

## CI/CD Considerations

### Continuous Integration
```bash
# Fast feedback loop - unit tests only
pytest -m "not live and not integration" --maxfail=1
```

### Staging/Pre-production
```bash
# Full test suite including integration
ENABLE_LIVE_TESTS=1 pytest --maxfail=3
```

## Best Practices

### DO ✅
- Write unit tests for all new features
- Mock external services in unit tests
- Use descriptive test names
- Keep integration tests separate
- Make integration tests opt-in
- Test both success and failure cases

### DON'T ❌
- Hit live APIs in unit tests
- Hardcode credentials in tests
- Write tests that depend on external service state
- Leave test data in external services
- Run integration tests in CI without proper setup

## Troubleshooting

### Common Issues

**"Live tests are skipped"**
```bash
# Solution: Enable live tests
export ENABLE_LIVE_TESTS=1
pytest integration/
```

**"Google API authentication failed"**
- Ensure `credentials.json` exists and is valid
- Check Google Sheets API is enabled
- Verify spreadsheet permissions

**"Tests are slow"**
```bash
# Solution: Run only fast tests
pytest -m "not slow"
```

**"Integration tests fail randomly"**
- Check network connectivity
- Verify external service availability
- Consider rate limiting issues

## Test Data

### Unit Test Data
Unit tests use predictable mock data defined in `tests/conftest.py`:

```python
@pytest.fixture
def sample_transaction_data():
    return [
        ["Transaction ID", "Date", "Amount", ...],
        ["tx_123", "2024-01-01", "-4.50", ...],
        # More test data...
    ]
```

### Integration Test Data
Integration tests use real spreadsheet data but should:
- Not modify the data
- Handle varying data gracefully
- Not assert specific values (data changes over time)

## Performance

### Typical Test Execution Times
- Unit tests: < 5 seconds total
- Integration tests: 10-30 seconds total
- Full suite: < 60 seconds

### Optimization Tips
- Run unit tests first (fail fast)
- Use `-x` flag to stop on first failure
- Use `-v` for verbose output during development
- Use `--tb=short` for concise error messages

## Examples

### Development Workflow
```bash
# 1. Write feature code
# 2. Write unit tests
pytest tests/test_your_feature.py -v

# 3. Run all unit tests
pytest -m "not live"

# 4. Test integration manually
ENABLE_LIVE_TESTS=1 pytest integration/test_live_monzo.py::test_specific_feature -v -s

# 5. Run full suite before commit
pytest && ENABLE_LIVE_TESTS=1 pytest integration/
```

### Debugging Failed Tests
```bash
# Run with detailed output
pytest tests/test_failing.py -v -s --tb=long

# Run single test with pdb
pytest tests/test_failing.py::test_specific -v -s --pdb

# Show local variables on failure
pytest tests/test_failing.py -v --tb=long -l
```
