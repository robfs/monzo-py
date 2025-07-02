# monzo-py

A Python library for interacting with and analyzing your Monzo bank transactions using Google Sheets and DuckDB.

> [!NOTE]
> In order to use this library you must have a **paid Monzo account** with your transactions exported to a Google Sheet. Free Monzo accounts do not have access to transaction exports.

## Setup

### Google Sheets Setup

1. **Export your Monzo transactions** to a Google Sheet through your Monzo app and verify you can access the spreadsheet.

2. **Enable Google Sheets API access** by following the [Google Sheets Python Quickstart guide](https://developers.google.com/workspace/sheets/api/quickstart/python).

> [!CAUTION]
> **Security Warning**: Never commit or share your `credentials.json` file with your project. Add it to your `.gitignore` file immediately.

3. **Configure API permissions**:
   - In [Google Cloud Console Data Access](https://console.cloud.google.com/auth/scopes), add the `/auth/spreadsheets.readonly` scope
   - In [Audience settings](https://console.cloud.google.com/auth/audience), add yourself as a test user to access the API without publishing

4. **Get your spreadsheet ID** from your Monzo Transactions Google Sheet URL:
   ```
   https://docs.google.com/spreadsheets/d/SPREADSHEET_ID_HERE/edit
   ```

### Installation

#### Setting up a new project

<!-- termynal -->

```
$ mkdir my-monzo-analysis
$ cd my-monzo-analysis
$ uv init
$ uv add git+https://github.com/robfs/monzo-py.git
```

#### Installing in an existing project

<!-- termynal -->

```
$ uv add git+https://github.com/robfs/monzo-py.git
```

#### Development installation

<!-- termynal -->

```
$ git clone https://github.com/robfs/monzo-py.git
$ cd monzo-py
$ uv sync
```

## Usage

### Basic Setup and Data Access

In order to access your Monzo transactions spreadsheet, you need to provide your Google Sheets spreadsheet ID. This can be cone in one of two ways:

1. Set the environment variable `MONZO_SPREADSHEET_ID` to your Google Sheets spreadsheet ID.
2. Pass the spreadsheet ID as the first argument to the `MonzoTransactions` constructor.

When you first run the code, it will prompt you to authorize the application to access your Google Sheets account. Follow the instructions to complete the authorization process.

Create a file called `basic_setup.py`:

```python
from monzo_py import MonzoTransactions

# Initialize with your Google Sheets spreadsheet ID
# monzo = MonzoTransactions("your_spreadsheet_id_here")  # use without environment variable
monzo = MonzoTransactions()                              # use with environment variable

# Create an in-memory DuckDB database
db_conn = monzo.duck_db()

# Show the contents of the transactions table
query = "SELECT date, time, name, amount FROM transactions ORDER BY date DESC"
db_conn.sql(query).show(max_rows=5)
```

Run with:
```bash
$ MONZO_SPREADSHEET_ID=your_spreadsheet_id_here uv run basic_setup.py
┌─────────────────────┬──────────┬─────────────────────┬───────────────┤
│        date         │   time   │        name         │    amount     │
│        date         │   time   │       varchar       │ decimal(10,2) │
├─────────────────────┼──────────┼─────────────────────┼───────────────┤
│ 2024-01-15          │ 14:32:00 │ Tesco Store         │        -23.45 │
│ 2024-01-14          │ 09:15:00 │ Costa Coffee        │         -4.50 │
│ 2024-01-13          │ 18:45:00 │ Salary Payment      │       2500.00 │
│ 2024-01-12          │ 12:30:00 │ Amazon Purchase     │        -45.99 │
│ 2024-01-11          │ 16:20:00 │ Local Restaurant    │        -18.75 │
└─────────────────────┴──────────┴─────────────────────┴───────────────┘
```

### Transaction Analysis with DuckDB

Create a file called `transaction_analysis.py`:

```python
from monzo_py import MonzoTransactions

# Assumes the MONZO_SPREADSHEET_ID environment variable is set
monzo = MonzoTransactions()

# Create an in-memory DuckDB database
db_conn = monzo.duck_db()

# Basic transaction overview
total_transactions = db_conn.sql("SELECT COUNT(*) FROM transactions").fetchone()[0]
print(f"Total transactions: {total_transactions}")

# Spending by category
print("\nSpending by category:")
spending_by_category = db_conn.sql("""
    SELECT
        category,
        COUNT(*) as transaction_count,
        ROUND(SUM(amount), 2) as total_spent,
        ROUND(AVG(amount), 2) as avg_amount
    FROM transactions
    WHERE amount IS NOT NULL
        AND amount < 0  -- Only spending (negative amounts)
    GROUP BY category
    ORDER BY total_spent ASC  -- Most spending first (most negative)
""").fetchall()

for category, count, total, avg in spending_by_category:
    print(
        f"{category}: {count} transactions, £{abs(total):.2f} total, £{abs(avg):.2f} avg"
    )

# Monthly spending trends
print("\nMonthly spending trends:")
monthly_spending = db_conn.sql("""
    SELECT
        strftime('%Y-%m', date) as month,
        ROUND(SUM(amount), 2) as net_spending
    FROM transactions
    WHERE amount IS NOT NULL
    GROUP BY strftime('%Y-%m', date)
    ORDER BY month DESC
    LIMIT 12
""").fetchall()

for month, net_spending in monthly_spending:
    print(f"{month}: £{abs(net_spending):.2f} net spending")

# Large transactions analysis
print("\nLargest transactions:")
large_transactions = db_conn.sql("""
    SELECT date, name, description, amount
    FROM transactions
    WHERE amount IS NOT NULL
        AND (amount > 100 OR amount < -100)
    ORDER BY ABS(amount) DESC
    LIMIT 10
""").fetchall()

for date, name, description, amount in large_transactions:
    print(f"{date} | {name} | {description} | £{amount:.2f}")

# Don't forget to close the connection
db_conn.close()

```

Run with:
```bash
$ MONZO_SPREADSHEET_ID=your_spreadsheet_id_here uv run transaction_analysis.py
Total transactions: 1234

Spending by category:
Groceries: 245 transactions, £3250.75 total, £13.27 avg
Eating out: 189 transactions, £2845.50 total, £15.05 avg
Bills: 45 transactions, £2250.00 total, £50.00 avg
Shopping: 156 transactions, £1950.25 total, £12.50 avg
Transport: 89 transactions, £890.00 total, £10.00 avg
Entertainment: 78 transactions, £1170.00 total, £15.00 avg
General: 67 transactions, £1340.00 total, £20.00 avg
Transfers: 23 transactions, £2300.00 total, £100.00 avg
Takeaway: 98 transactions, £1470.00 total, £15.00 avg
Savings: 12 transactions, £1200.00 total, £100.00 avg

Monthly spending trends:
2023-12: £450.25 net spending
2023-11: £385.75 net spending
2023-10: £420.50 net spending
2023-09: £395.80 net spending
2023-08: £465.20 net spending
2023-07: £410.95 net spending
2023-06: £378.45 net spending
2023-05: £425.60 net spending
2023-04: £390.30 net spending
2023-03: £445.75 net spending

Largest transactions:
2023-11-15 | Salary Payment | Monthly Salary | £2500.00
2023-11-01 | Rent Payment | Monthly Rent | £-1200.00
2023-10-25 | Savings Transfer | Emergency Fund | £-500.00
2023-10-20 | Grocery Shopping | Weekly Shop | £-125.50
2023-10-18 | Freelance Payment | Project Work | £800.00
```

### Data Visualization with Plotly

Create a file called `visualizations.py`:

```python
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from monzo_py import MonzoTransactions

# Initialize MonzoTransactions
monzo = MonzoTransactions(spreadsheet_id="your_spreadsheet_id_here")

# Get data for visualization
db_conn = monzo.duck_db()

print("Creating visualizations...")
print()

# Monthly spending trend
monthly_data = db_conn.execute("""
    SELECT
        strftime('%Y-%m', date) as month,
        ROUND(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END), 2) as spending,
        ROUND(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 2) as income
    FROM transactions
    WHERE amount IS NOT NULL
    GROUP BY strftime('%Y-%m', date)
    ORDER BY month
""").fetchall()

# Convert to DataFrame for easier plotting
df_monthly = pd.DataFrame(monthly_data, columns=['month', 'spending', 'income'])
df_monthly['spending'] = df_monthly['spending'].abs()  # Make spending positive for chart

print("Monthly Income vs Spending data:")
print(df_monthly.head())
print()

# Create monthly spending/income chart
fig_monthly = go.Figure()
fig_monthly.add_trace(go.Scatter(
    x=df_monthly['month'],
    y=df_monthly['spending'],
    mode='lines+markers',
    name='Spending',
    line=dict(color='red')
))
fig_monthly.add_trace(go.Scatter(
    x=df_monthly['month'],
    y=df_monthly['income'],
    mode='lines+markers',
    name='Income',
```

### Transaction Analysis with DuckDB

Create a file called `transaction_analysis.py`:

```python
from monzo_py import MonzoTransactions

# Initialize with your Google Sheets spreadsheet ID
monzo = MonzoTransactions(spreadsheet_id="your_spreadsheet_id_here")

# Create an in-memory DuckDB database
db_conn = monzo.duck_db()

# Basic transaction overview
total_transactions = db_conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
print(f"Total transactions: {total_transactions}")
print()

# Spending by category
print("Spending by category:")
spending_by_category = db_conn.execute("""
    SELECT
        category,
        COUNT(*) as transaction_count,
        ROUND(SUM(amount), 2) as total_spent,
        ROUND(AVG(amount), 2) as avg_amount
    FROM transactions
    WHERE amount IS NOT NULL
        AND amount < 0  -- Only spending (negative amounts)
    GROUP BY category
    ORDER BY total_spent ASC  -- Most spending first (most negative)
""").fetchall()

for category, count, total, avg in spending_by_category:
    print(f"{category}: {count} transactions, £{abs(total):.2f} total, £{abs(avg):.2f} avg")

print()

# Monthly spending trends
print("Monthly spending trends:")
monthly_spending = db_conn.execute("""
    SELECT
        strftime('%Y-%m', date) as month,
        ROUND(SUM(amount), 2) as net_spending
    FROM transactions
    WHERE amount IS NOT NULL
    GROUP BY strftime('%Y-%m', date)
    ORDER BY month DESC
    LIMIT 12
""").fetchall()

for month, net_spending in monthly_spending:
    print(f"{month}: £{abs(net_spending):.2f} net spending")

print()

# Large transactions analysis
print("Largest transactions:")
large_transactions = db_conn.execute("""
    SELECT date, name, description, amount
    FROM transactions
    WHERE amount IS NOT NULL
        AND (amount > 100 OR amount < -100)
    ORDER BY ABS(amount) DESC
    LIMIT 10
""").fetchall()

for date, name, description, amount in large_transactions:
    print(f"{date} | {name} | {description} | £{amount:.2f}")

# Don't forget to close the connection
db_conn.close()
```

Run with:
```bash
$ python transaction_analysis.py
Total transactions: 1234

Spending by category:
Groceries: 245 transactions, £3250.75 total, £13.27 avg
Eating out: 189 transactions, £2845.50 total, £15.05 avg
Bills: 45 transactions, £2250.00 total, £50.00 avg
Shopping: 156 transactions, £1950.25 total, £12.50 avg
Transport: 89 transactions, £890.00 total, £10.00 avg
Entertainment: 78 transactions, £1170.00 total, £15.00 avg
General: 67 transactions, £1340.00 total, £20.00 avg
Transfers: 23 transactions, £2300.00 total, £100.00 avg
Takeaway: 98 transactions, £1470.00 total, £15.00 avg
Savings: 12 transactions, £1200.00 total, £100.00 avg

Monthly spending trends:
2023-12: £450.25 net spending
2023-11: £385.75 net spending
2023-10: £420.50 net spending
2023-09: £395.80 net spending
2023-08: £465.20 net spending
2023-07: £410.95 net spending
2023-06: £378.45 net spending
2023-05: £425.60 net spending
2023-04: £390.30 net spending
2023-03: £445.75 net spending

Largest transactions:
2023-11-15 | Salary Payment | Monthly Salary | £2500.00
2023-11-01 | Rent Payment | Monthly Rent | £-1200.00
2023-10-25 | Savings Transfer | Emergency Fund | £-500.00
2023-10-20 | Grocery Shopping | Weekly Shop | £-125.50
2023-10-18 | Freelance Payment | Project Work | £800.00
```

### Advanced Analysis Examples

Create a file called `advanced_analysis.py`:

```python
from monzo_py import MonzoTransactions

# Initialize MonzoTransactions
monzo = MonzoTransactions()
db_conn = monzo.duck_db()

# Merchant analysis - find your most frequented places
print("=== MERCHANT ANALYSIS ===")
merchant_analysis = db_conn.execute("""
    SELECT
        name,
        COUNT(*) as visit_count,
        ROUND(ABS(SUM(amount)), 2) as total_spent,
        ROUND(ABS(AVG(amount)), 2) as avg_spent_per_visit
    FROM transactions
    WHERE amount IS NOT NULL
        AND amount < 0
        AND name IS NOT NULL
        AND name != ''
    GROUP BY name
    HAVING COUNT(*) >= 5  -- At least 5 visits
    ORDER BY total_spent DESC
    LIMIT 15
""").fetchall()

print("Top merchants by total spending:")
for name, visits, total, avg in merchant_analysis:
    print(f"{name}: {visits} visits, £{total} total, £{avg} avg per visit")

print("\n=== SEASONAL SPENDING PATTERNS ===")
# Seasonal spending patterns
seasonal_spending = db_conn.execute("""
    SELECT
        CASE
            WHEN EXTRACT(MONTH FROM date) IN (12, 1, 2) THEN 'Winter'
            WHEN EXTRACT(MONTH FROM date) IN (3, 4, 5) THEN 'Spring'
            WHEN EXTRACT(MONTH FROM date) IN (6, 7, 8) THEN 'Summer'
            ELSE 'Autumn'
        END as season,
        category,
        ROUND(ABS(AVG(amount)), 2) as avg_spending
    FROM transactions
    WHERE amount IS NOT NULL
        AND amount < 0
        AND category IS NOT NULL
    GROUP BY season, category
    ORDER BY season, avg_spending DESC
""").fetchall()

current_season = ""
for season, category, avg_spending in seasonal_spending:
    if season != current_season:
        print(f"\n{season}:")
        current_season = season
    print(f"  {category}: £{avg_spending} average")

print("\n=== SPENDING INSIGHTS ===")
# Additional insights
weekend_vs_weekday = db_conn.execute("""
    SELECT
        CASE
            WHEN EXTRACT(DOW FROM date) IN (0, 6) THEN 'Weekend'
            ELSE 'Weekday'
        END as day_type,
        COUNT(transaction_id) as transaction_count,
        ROUND(ABS(SUM(amount)), 2) as total_spending,
        ROUND(ABS(AVG(amount)), 2) as avg_transaction
    FROM transactions
    WHERE amount IS NOT NULL AND amount < 0
    GROUP BY day_type
""").fetchall()

print("Weekend vs Weekday spending:")
for day_type, count, total, avg in weekend_vs_weekday:
    print(
        f"{day_type}: {count} transactions, £{total} total, £{avg} avg per transaction"
    )

# Close database connection
db_conn.close()
```

Run with:
```bash
$ python advanced_analysis.py
=== MERCHANT ANALYSIS ===
Top merchants by total spending:
Tesco: 45 visits, £675.50 total, £15.01 avg per visit
Sainsbury's: 38 visits, £542.25 total, £14.27 avg per visit
Costa Coffee: 67 visits, £335.00 total, £5.00 avg per visit
Amazon: 23 visits, £458.75 total, £19.95 avg per visit
Deliveroo: 31 visits, £465.00 total, £15.00 avg per visit
McDonald's: 19 visits, £152.00 total, £8.00 avg per visit
Local Restaurant: 12 visits, £240.00 total, £20.00 avg per visit
Corner Shop: 28 visits, £168.00 total, £6.00 avg per visit

=== SEASONAL SPENDING PATTERNS ===

Autumn:
  Bills: £65.50 average
  Groceries: £18.75 average
  Eating out: £22.50 average
  Shopping: £28.90 average
  Transport: £12.40 average
  Entertainment: £16.25 average
  Takeaway: £14.80 average
  General: £25.00 average

Spring:
  Groceries: £16.25 average
  Bills: £58.75 average
  Shopping: £32.50 average
  Eating out: £19.90 average
  Transport: £11.80 average

Summer:
  Groceries: £17.50 average
  Bills: £60.00 average
  Shopping: £35.00 average
  Eating out: £20.00 average
  Transport: £12.00 average

Winter:
  Groceries: £15.00 average
  Bills: £55.00 average
  Shopping: £30.00 average
  Eating out: £18.00 average
  Transport: £10.00 average

=== SPENDING INSIGHTS ===
Weekend vs Weekday spending:
Weekday: 856 transactions, £8,950.75 total, £10.45 avg per transaction
Weekend: 378 transactions, £5,715.50 total, £15.12 avg per transaction
```

## Data Structure

The library maps your Google Sheets columns to a structured database with the following schema:

| Column | Field Name | Description |
|--------|------------|-------------|
| 1 | `transaction_id` | Unique transaction identifier |
| 2 | `date` | Transaction date |
| 3 | `time` | Transaction time |
| 4 | `type` | Transaction type (Payment/Transfer) |
| 5 | `name` | Merchant or payee name |
| 6 | `emoji` | Transaction emoji |
| 7 | `category` | Spending category |
| 8 | `amount` | Transaction amount |
| 9 | `currency` | Transaction currency |
| 10 | `local_amount` | Local amount (if different currency) |
| 11 | `local_currency` | Local currency |
| 12 | `notes_and_tags` | Notes and hashtags |
| 13 | `address` | Merchant address |
| 14 | `receipt` | Receipt information |
| 15 | `description` | Transaction description |
| 16 | `category_split` | Category split identifier |

> [!TIP]
> Headers in your spreadsheet are automatically ignored - data is mapped by column position (A through P).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
