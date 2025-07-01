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

### Transaction Analysis with DuckDB

The library automatically converts your spreadsheet data into a structured DuckDB database for powerful SQL analysis:

```python
# Create an in-memory DuckDB database
db_conn = monzo.duck_db()

# Basic transaction overview
total_transactions = db_conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
print(f"Total transactions: {total_transactions}")

# Spending by category
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

# Monthly spending trends
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

# Large transactions analysis
large_transactions = db_conn.execute("""
    SELECT date, name, description, amount
    FROM transactions 
    WHERE amount IS NOT NULL
        AND (amount > 100 OR amount < -100)
    ORDER BY ABS(amount) DESC
    LIMIT 10
""").fetchall()

# Don't forget to close the connection
db_conn.close()
```

### Data Visualization with Plotly

Create interactive charts to visualize your spending patterns:

```python
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# Get data for visualization
db_conn = monzo.duck_db()

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
        strftime('%H', time) as hour_of_day,
        COUNT(*) as transaction_count,
        ROUND(ABS(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END)), 2) as spending
    FROM transactions 
    WHERE amount IS NOT NULL 
        AND time IS NOT NULL
        AND amount < 0
    GROUP BY strftime('%w', date), strftime('%H', time)
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

fig_heatmap = px.imshow(
    heatmap_data,
    labels=dict(x="Hour of Day", y="Day of Week", color="Spending (£)"),
    title="Spending Patterns by Day and Hour"
)
fig_heatmap.show()

# Close database connection
db_conn.close()
```

### Advanced Analysis Examples

```python
# Merchant analysis - find your most frequented places
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