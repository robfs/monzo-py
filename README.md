# monzo-py

A Python library for interacting with and analyzing your Monzo bank transactions using Google Sheets and DuckDB.

Transform your exported Monzo transaction data into a powerful analytical database with SQL querying capabilities and rich visualizations. Perfect for personal finance analysis, budgeting insights, and spending pattern discovery.

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

Create a file called `basic_setup.py`:

```python
from monzo_py import MonzoTransactions

# Initialize with your Google Sheets spreadsheet ID
monzo = MonzoTransactions(spreadsheet_id="your_spreadsheet_id_here")

# Fetch transaction data from Google Sheets
data = monzo.data
print(f"Successfully loaded {len(data)} transactions")

# Preview your data structure
for i, row in enumerate(data[:3]):  # First 3 rows
    print(f"Row {i}: {row}")
```

Run with:
```bash
$ python basic_setup.py
Successfully loaded 1234 transactions
Row 0: ['Transaction ID', 'Date', 'Time', 'Type', 'Name', 'Emoji', 'Category', 'Amount', 'Currency', 'Local amount', 'Local currency', 'Notes and #tags', 'Address', 'Receipt', 'Description', 'Category split']
Row 1: ['tx_0000ABC123XYZ456789012', '15/06/2023', '14:35:22', 'prepaid-bridge', '', '', 'General', '25.50', 'GBP', '25.50', 'GBP', 'Prepaid to current transfer', '', '', 'Prepaid to current transfer', '']
Row 2: ['tx_0000DEF456ABC789012345', '15/06/2023', '18:45:15', 'Card payment', 'Coffee Corner', '☕', 'Entertainment', '-4.50', 'GBP', '-4.50', 'GBP', '', '123 High Street, London', '', 'COFFEE CORNER          LONDON  SW1   GBR', '']
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
    line=dict(color='green')
))
fig_monthly.update_layout(
    title='Monthly Income vs Spending',
    xaxis_title='Month',
    yaxis_title='Amount (£)',
    hovermode='x unified'
)
fig_monthly.show()

# Category spending pie chart
category_data = db_conn.execute("""
    SELECT
        category,
        ROUND(ABS(SUM(amount)), 2) as total_spent
    FROM transactions
    WHERE amount IS NOT NULL
        AND amount < 0  -- Only spending
        AND category IS NOT NULL
        AND category != ''
    GROUP BY category
    ORDER BY total_spent DESC
    LIMIT 10
""").fetchall()

df_categories = pd.DataFrame(category_data, columns=['category', 'total_spent'])

print("Category spending data:")
print(df_categories)
print()

fig_pie = px.pie(
    df_categories,
    values='total_spent',
    names='category',
    title='Spending by Category (Top 10)'
)
fig_pie.show()

# Weekly spending heatmap
weekly_data = db_conn.execute("""
    SELECT
        strftime('%w', date) as day_of_week,  -- 0=Sunday, 6=Saturday
        EXTRACT(HOUR FROM time) as hour_of_day,
        COUNT(*) as transaction_count,
        ROUND(ABS(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END)), 2) as spending
    FROM transactions
    WHERE amount IS NOT NULL
        AND time IS NOT NULL
        AND amount < 0
    GROUP BY strftime('%w', date), EXTRACT(HOUR FROM time)
""").fetchall()

df_heatmap = pd.DataFrame(weekly_data, columns=['day_of_week', 'hour_of_day', 'transaction_count', 'spending'])

# Convert day numbers to names
day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
df_heatmap['day_name'] = df_heatmap['day_of_week'].apply(lambda x: day_names[int(x)])

# Create pivot table for heatmap
heatmap_data = df_heatmap.pivot_table(
    values='spending',
    index='day_name',
    columns='hour_of_day',
    fill_value=0
)

print("Spending heatmap data shape:", heatmap_data.shape)
print("Peak spending hours identified")
print()

fig_heatmap = px.imshow(
    heatmap_data,
    labels=dict(x="Hour of Day", y="Day of Week", color="Spending (£)"),
    title="Spending Patterns by Day and Hour"
)
fig_heatmap.show()

print("All visualizations generated successfully!")
print("Charts will open in your default web browser.")

# Close database connection
db_conn.close()
```

Run with:
```bash
$ python visualizations.py
Creating visualizations...

Monthly Income vs Spending data:
     month  spending   income
0  2023-08    285.50   2500.00
1  2023-09    315.75   2500.00
2  2023-10    342.25   2650.00
3  2023-11    298.90   2500.00
4  2023-12    325.40   2500.00

Category spending data:
        category  total_spent
0      Groceries      3250.75
1     Eating out      2845.50
2          Bills      2250.00
3       Shopping      1950.25
4       Takeaway      1470.00
5        General      1340.00
6           Savings      1200.00
7  Entertainment      1170.00
8      Transport       890.00
9      Transfers       575.50

Spending heatmap data shape: (7, 24)
Peak spending hours identified

All visualizations generated successfully!
Charts will open in your default web browser.
```

The script will generate three interactive visualizations:
- **Monthly trends**: Line chart comparing income vs spending over time
- **Category breakdown**: Pie chart showing spending distribution across categories
- **Spending heatmap**: Visual representation of when you spend money throughout the week

### Advanced Analysis Examples

Create a file called `advanced_analysis.py`:

```python
from monzo_py import MonzoTransactions

# Initialize MonzoTransactions
monzo = MonzoTransactions(spreadsheet_id="your_spreadsheet_id_here")
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
            WHEN CAST(strftime('%m', date) AS INTEGER) IN (12, 1, 2) THEN 'Winter'
            WHEN CAST(strftime('%m', date) AS INTEGER) IN (3, 4, 5) THEN 'Spring'
            WHEN CAST(strftime('%m', date) AS INTEGER) IN (6, 7, 8) THEN 'Summer'
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
for season, category, avg_spending in seasonal_spending[:20]:  # Show top 20
    if season != current_season:
        print(f"\n{season}:")
        current_season = season
    print(f"  {category}: £{avg_spending} average")

print("\n=== SPENDING INSIGHTS ===")
# Additional insights
weekend_vs_weekday = db_conn.execute("""
    SELECT
        CASE
            WHEN strftime('%w', date) IN ('0', '6') THEN 'Weekend'
            ELSE 'Weekday'
        END as day_type,
        COUNT(*) as transaction_count,
        ROUND(ABS(SUM(amount)), 2) as total_spending,
        ROUND(ABS(AVG(amount)), 2) as avg_transaction
    FROM transactions
    WHERE amount IS NOT NULL AND amount < 0
    GROUP BY day_type
""").fetchall()

print("Weekend vs Weekday spending:")
for day_type, count, total, avg in weekend_vs_weekday:
    print(f"{day_type}: {count} transactions, £{total} total, £{avg} avg per transaction")

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

=== SPENDING INSIGHTS ===
Weekend vs Weekday spending:
Weekday: 856 transactions, £8,950.75 total, £10.45 avg per transaction
Weekend: 378 transactions, £5,715.50 total, £15.12 avg per transaction
```

## Data Structure

The library maps your Google Sheets columns to a structured database with the following schema:

| Column | Field Name | Description |
|--------|------------|-------------|
| A | `transaction_id` | Unique transaction identifier |
| B | `date` | Transaction date |
| C | `time` | Transaction time |
| D | `type` | Transaction type (Payment/Transfer) |
| E | `name` | Merchant or payee name |
| F | `emoji` | Transaction emoji |
| G | `category` | Spending category |
| H | `amount` | Transaction amount |
| I | `currency` | Transaction currency |
| J | `local_amount` | Local amount (if different currency) |
| K | `local_currency` | Local currency |
| L | `notes_and_tags` | Notes and hashtags |
| M | `address` | Merchant address |
| N | `receipt` | Receipt information |
| O | `description` | Transaction description |
| P | `category_split` | Category split identifier |

> [!TIP]
> Headers in your spreadsheet are automatically ignored - data is mapped by column position (A through P).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
