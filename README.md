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
Successfully loaded 5627 transactions
Row 0: ['Transaction ID', 'Date', 'Time', 'Type', 'Name', 'Emoji', 'Category', 'Amount', 'Currency', 'Local amount', 'Local currency', 'Notes and #tags', 'Address', 'Receipt', 'Description', 'Category split']
Row 1: ['tx_00009R5jgIR0O6ricjZJwn', '30/11/2017', '19:24:39', 'prepaid-bridge', '', '', 'General', '37.72', 'GBP', '37.72', 'GBP', 'Prepaid to current transfer', '', '', 'Prepaid to current transfer', '']
Row 2: ['tx_00009R5tJnb9M6SSasNGu9', '30/11/2017', '21:12:38', 'Card payment', 'The Three Crowns', '🍺', 'Entertainment', '-11.20', 'GBP', '-11.20', 'GBP', '', '175 Stoke Newington High Street', '', 'THE THREE CROWNS       LONDON  N16   GBR', '']
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
Total transactions: 5626

Spending by category:
Transfers: 107 transactions, £148584.03 total, £1388.64 avg
General: 257 transactions, £67144.45 total, £261.26 avg
Savings: 9 transactions, £54301.64 total, £6033.52 avg
Bills: 57 transactions, £37261.47 total, £653.71 avg
Extension: 4 transactions, £19295.00 total, £4823.75 avg
Eating out: 1039 transactions, £16405.00 total, £15.79 avg
Groceries: 1196 transactions, £14983.08 total, £12.53 avg
Shopping: 321 transactions, £13339.96 total, £41.56 avg
Takeaway: 181 transactions, £5322.20 total, £29.40 avg
Entertainment: 323 transactions, £5216.30 total, £16.15 avg

Monthly spending trends:
2025-07: £9.99 net spending
2025-06: £326.96 net spending
2025-05: £93.84 net spending
2025-04: £629.53 net spending
2025-03: £270.56 net spending
2025-02: £281.11 net spending
2025-01: £292.59 net spending
2024-12: £240.39 net spending
2024-11: £171.41 net spending
2024-10: £63.69 net spending

Largest transactions:
2024-03-22 | Robert Simms & Nicola Fox | None | £-50000.00
2024-03-22 | SIMMS R/STU2011 | MONZO | £50000.00
2023-03-30 | Savings Pot | None | £34000.00
2023-03-31 | Charles Stanley | CHARLES STANLEY        LONDON        GBR | £-34000.00
2023-10-05 | SIMMS R/STU2011 | MONZO | £20000.00
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
0  2017-11     33.60    37.72
1  2017-12      4.55    18.00
2  2018-01     73.00   100.00
3  2018-02    319.18   300.00
4  2018-03      2.40    54.50

Category spending data:
        category  total_spent
0      Transfers    148584.03
1        General     67144.45
2        Savings     54301.64
3          Bills     37261.47
4      Extension     19295.00
5     Eating out     16405.00
6      Groceries     14983.08
7       Shopping     13339.96
8       Takeaway      5322.20
9  Entertainment      5216.30

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
Robert Simms & Nicola Fox: 52 visits, £83944.64 total, £1614.32 avg per visit
Rob Fox & Nicola Fox: 11 visits, £55003.45 total, £5000.31 avg per visit
Savings Pot: 8 visits, £54300.00 total, £6787.5 avg per visit
Hanne & Co: 5 visits, £29560.25 total, £5912.05 avg per visit
AMERICAN EXP 3773: 30 visits, £21661.12 total, £722.04 avg per visit
Deliveroo: 168 visits, £5058.34 total, £30.11 avg per visit
M&S: 317 visits, £3921.86 total, £12.37 avg per visit
Sainsbury's: 294 visits, £3088.67 total, £10.51 avg per visit

=== SEASONAL SPENDING PATTERNS ===

Autumn:
  Family: £908.0 average
  General: £637.55 average
  Transfers: £601.73 average
  Renovations: £153.31 average
  Shopping: £38.36 average
  Holidays: £34.14 average
  Bills: £29.2 average
  Takeaway: £26.53 average
  Eating out: £14.44 average
  Entertainment: £12.55 average

Spring:
  Savings: £8300.0 average
  Extension: £8125.0 average
  General: £280.48 average
  Transfers: £2766.67 average
  Shopping: £45.21 average

=== SPENDING INSIGHTS ===
Weekend vs Weekday spending:
Weekday: 3558 transactions, £317755.67 total, £89.31 avg per transaction
Weekend: 1429 transactions, £89130.39 total, £62.37 avg per transaction
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
