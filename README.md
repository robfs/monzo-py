# monzo-py

A Python library for interacting with your Monzo transactions.

> [!IMPORTANT]
> In order to use this library you must have a paid Monzo account with your transactions exported to a Google Sheet.

## Google Sheets Setup

1. Ensure your Monzo transactions are exported to a Google Sheet and check you can access it.
2. Follow the instructions to enable access to your [Google Sheets via Python](https://developers.google.com/workspace/sheets/api/quickstart/python).

> [!IMPORTANT]
> Make sure you keep a copy of your `credentials.json` file immediately but DO NOT commit or share it with your project.

3. Within [Data Access](https://console.cloud.google.com/auth/scopes) add the `/auth/spreadsheets.readonly` scope to your project.
4. Within [Audience](https://console.cloud.google.com/auth/audience) add yourself as a test user (this will enable you to access the API without publishing the app).

## Installation

Install the required dependencies:

```bash
uv sync
```

Or if using pip:

```bash
pip install duckdb pyarrow google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

## Usage

### Basic Usage

```python
from monzo_py import MonzoTransactions

# Create instance
monzo = MonzoTransactions(spreadsheet_id="your_spreadsheet_id")

# Fetch data from Google Sheets
data = monzo.data
print(f"Fetched {len(data)} rows")
```

### DuckDB Integration

The library includes a `duck_db()` method that creates an in-memory DuckDB database from your spreadsheet data:

```python
# Create DuckDB database from spreadsheet data
db_conn = monzo.duck_db()

# Run SQL queries on your data
result = db_conn.execute("SELECT COUNT(*) FROM transactions").fetchone()
print(f"Total transactions: {result[0]}")

# Query by category
categories = db_conn.execute("""
    SELECT category, COUNT(*) as count, SUM(CAST(amount AS DOUBLE)) as total
    FROM transactions
    WHERE amount IS NOT NULL
    GROUP BY category
    ORDER BY total DESC
""").fetchall()

# Find transactions above a certain amount
large_transactions = db_conn.execute("""
    SELECT date, description, amount
    FROM transactions
    WHERE CAST(amount AS DOUBLE) > 100
    ORDER BY CAST(amount AS DOUBLE) DESC
""").fetchall()

# Close connection when done
db_conn.close()
```

#### Column Structure

The `duck_db()` method uses a fixed 16-column structure matching Monzo's export format:

- Column 1 → `transaction_id` (unique transaction identifier)
- Column 2 → `date` (transaction date)
- Column 3 → `time` (transaction time)
- Column 4 → `type` (transaction type: Payment/Transfer)
- Column 5 → `name` (merchant/payee name)
- Column 6 → `emoji` (transaction emoji)
- Column 7 → `category` (spending category)
- Column 8 → `amount` (transaction amount)
- Column 9 → `currency` (transaction currency)
- Column 10 → `local_amount` (local amount if different currency)
- Column 11 → `local_currency` (local currency)
- Column 12 → `notes_and_tags` (notes and hashtags)
- Column 13 → `address` (merchant address)
- Column 14 → `receipt` (receipt information)
- Column 15 → `description` (transaction description)
- Column 16 → `category_split` (category identifier)

Headers in your spreadsheet are ignored - data is mapped by column position (A-P).
