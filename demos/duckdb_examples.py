#!/usr/bin/env python3
"""Practical examples of using DuckDB with Monzo transaction data.

This script demonstrates common financial analysis queries using the duck_db() method
of the MonzoTransactions class.
"""

import logging
import sys

from monzo_py import MonzoTransactions

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def analyze_spending_patterns(db_conn):
    """Analyze spending patterns from transaction data."""
    print("\n" + "=" * 60)
    print("📊 SPENDING PATTERN ANALYSIS")
    print("=" * 60)

    # Monthly spending summary
    print("\n1. Monthly Spending Summary:")
    try:
        monthly_query = """
        SELECT
            STRFTIME('%Y-%m', date) as month,
            COUNT(*) as transaction_count,
            ROUND(SUM(CASE WHEN TRY_CAST(amount AS DOUBLE) < 0
                          THEN ABS(TRY_CAST(amount AS DOUBLE))
                          ELSE 0 END), 2) as total_spent,
            ROUND(AVG(CASE WHEN TRY_CAST(amount AS DOUBLE) < 0
                          THEN ABS(TRY_CAST(amount AS DOUBLE))
                          ELSE NULL END), 2) as avg_transaction
        FROM transactions
        WHERE date IS NOT NULL AND amount IS NOT NULL
        GROUP BY STRFTIME('%Y-%m', date)
        ORDER BY month DESC
        LIMIT 6
        """
        results = db_conn.execute(monthly_query).fetchall()

        if results:
            print("   Month    | Transactions | Total Spent | Avg per Transaction")
            print("   ---------|--------------|-------------|-------------------")
            for row in results:
                print(
                    f"   {row[0]:<8} | {row[1]:<12} | £{row[2]:<10} | £{row[3] or 0:<10}"
                )
        else:
            print("   No monthly data found")
    except Exception as e:
        print(f"   Error analyzing monthly data: {e}")

    # Category breakdown
    print("\n2. Spending by Category (Top 10):")
    try:
        category_query = """
        SELECT
            COALESCE(category, 'Unknown') as category,
            COUNT(*) as transaction_count,
            ROUND(SUM(CASE WHEN TRY_CAST(amount AS DOUBLE) < 0
                          THEN ABS(TRY_CAST(amount AS DOUBLE))
                          ELSE 0 END), 2) as total_spent
        FROM transactions
        WHERE amount IS NOT NULL
        GROUP BY category
        HAVING total_spent > 0
        ORDER BY total_spent DESC
        LIMIT 10
        """
        results = db_conn.execute(category_query).fetchall()

        if results:
            print("   Category          | Transactions | Total Spent")
            print("   ------------------|--------------|------------")
            for row in results:
                category = row[0][:17]  # Truncate long category names
                print(f"   {category:<17} | {row[1]:<12} | £{row[2]}")
        else:
            print("   No category data found")
    except Exception as e:
        print(f"   Error analyzing category data: {e}")


def find_unusual_transactions(db_conn):
    """Find unusual or noteworthy transactions."""
    print("\n" + "=" * 60)
    print("🔍 UNUSUAL TRANSACTION ANALYSIS")
    print("=" * 60)

    # Largest expenses
    print("\n1. Largest Expenses (Top 10):")
    try:
        large_expenses_query = """
        SELECT
            date,
            COALESCE(description, 'No description') as description,
            amount,
            COALESCE(category, 'Unknown') as category
        FROM transactions
        WHERE TRY_CAST(amount AS DOUBLE) < 0
        ORDER BY TRY_CAST(amount AS DOUBLE) ASC
        LIMIT 10
        """
        results = db_conn.execute(large_expenses_query).fetchall()

        if results:
            print(
                "   Date       | Description                    | Amount    | Category"
            )
            print(
                "   -----------|---------------------------------|-----------|----------"
            )
            for row in results:
                desc = (row[1][:30] + "...") if len(str(row[1])) > 30 else str(row[1])
                print(f"   {row[0]:<10} | {desc:<31} | £{row[2]:<8} | {row[3]}")
        else:
            print("   No large expenses found")
    except Exception as e:
        print(f"   Error finding large expenses: {e}")

    # Income transactions
    print("\n2. Income Transactions:")
    try:
        income_query = """
        SELECT
            date,
            COALESCE(description, 'No description') as description,
            amount,
            COALESCE(category, 'Unknown') as category
        FROM transactions
        WHERE TRY_CAST(amount AS DOUBLE) > 0
        ORDER BY TRY_CAST(amount AS DOUBLE) DESC
        LIMIT 10
        """
        results = db_conn.execute(income_query).fetchall()

        if results:
            print(
                "   Date       | Description                    | Amount     | Category"
            )
            print(
                "   -----------|---------------------------------|------------|----------"
            )
            for row in results:
                desc = (row[1][:30] + "...") if len(str(row[1])) > 30 else str(row[1])
                print(f"   {row[0]:<10} | {desc:<31} | £{row[2]:<9} | {row[3]}")
        else:
            print("   No income transactions found")
    except Exception as e:
        print(f"   Error finding income transactions: {e}")


def analyze_merchant_patterns(db_conn):
    """Analyze spending patterns by merchant."""
    print("\n" + "=" * 60)
    print("🏪 MERCHANT ANALYSIS")
    print("=" * 60)

    # Most frequent merchants
    print("\n1. Most Frequent Merchants:")
    try:
        merchant_frequency_query = """
        SELECT
            COALESCE(description, 'Unknown') as merchant,
            COUNT(*) as visit_count,
            ROUND(SUM(CASE WHEN TRY_CAST(amount AS DOUBLE) < 0
                          THEN ABS(TRY_CAST(amount AS DOUBLE))
                          ELSE 0 END), 2) as total_spent,
            ROUND(AVG(CASE WHEN TRY_CAST(amount AS DOUBLE) < 0
                          THEN ABS(TRY_CAST(amount AS DOUBLE))
                          ELSE NULL END), 2) as avg_transaction
        FROM transactions
        WHERE description IS NOT NULL AND amount IS NOT NULL
        GROUP BY description
        HAVING visit_count > 1 AND total_spent > 0
        ORDER BY visit_count DESC, total_spent DESC
        LIMIT 10
        """
        results = db_conn.execute(merchant_frequency_query).fetchall()

        if results:
            print("   Merchant                      | Visits | Total Spent | Avg/Visit")
            print(
                "   -------------------------------|--------|-------------|----------"
            )
            for row in results:
                merchant = (
                    (row[0][:30] + "...") if len(str(row[0])) > 30 else str(row[0])
                )
                print(
                    f"   {merchant:<30} | {row[1]:<6} | £{row[2]:<10} | £{row[3] or 0}"
                )
        else:
            print("   No merchant data found")
    except Exception as e:
        print(f"   Error analyzing merchant data: {e}")

    # Highest spending merchants
    print("\n2. Highest Spending Merchants:")
    try:
        merchant_spending_query = """
        SELECT
            COALESCE(description, 'Unknown') as merchant,
            COUNT(*) as visit_count,
            ROUND(SUM(CASE WHEN TRY_CAST(amount AS DOUBLE) < 0
                          THEN ABS(TRY_CAST(amount AS DOUBLE))
                          ELSE 0 END), 2) as total_spent
        FROM transactions
        WHERE description IS NOT NULL AND amount IS NOT NULL
        GROUP BY description
        HAVING total_spent > 0
        ORDER BY total_spent DESC
        LIMIT 10
        """
        results = db_conn.execute(merchant_spending_query).fetchall()

        if results:
            print("   Merchant                      | Visits | Total Spent")
            print("   -------------------------------|--------|------------")
            for row in results:
                merchant = (
                    (row[0][:30] + "...") if len(str(row[0])) > 30 else str(row[0])
                )
                print(f"   {merchant:<30} | {row[1]:<6} | £{row[2]}")
        else:
            print("   No merchant spending data found")
    except Exception as e:
        print(f"   Error analyzing merchant spending: {e}")


def weekly_spending_trends(db_conn):
    """Analyze spending trends by day of week."""
    print("\n" + "=" * 60)
    print("📅 WEEKLY SPENDING TRENDS")
    print("=" * 60)

    try:
        weekly_query = """
        SELECT
            CASE CAST(STRFTIME('%w', date) AS INTEGER)
                WHEN 0 THEN 'Sunday'
                WHEN 1 THEN 'Monday'
                WHEN 2 THEN 'Tuesday'
                WHEN 3 THEN 'Wednesday'
                WHEN 4 THEN 'Thursday'
                WHEN 5 THEN 'Friday'
                WHEN 6 THEN 'Saturday'
                ELSE 'Unknown'
            END as day_of_week,
            COUNT(*) as transaction_count,
            ROUND(SUM(CASE WHEN TRY_CAST(amount AS DOUBLE) < 0
                          THEN ABS(TRY_CAST(amount AS DOUBLE))
                          ELSE 0 END), 2) as total_spent,
            ROUND(AVG(CASE WHEN TRY_CAST(amount AS DOUBLE) < 0
                          THEN ABS(TRY_CAST(amount AS DOUBLE))
                          ELSE NULL END), 2) as avg_transaction
        FROM transactions
        WHERE date IS NOT NULL AND amount IS NOT NULL
        GROUP BY STRFTIME('%w', date)
        ORDER BY CAST(STRFTIME('%w', date) AS INTEGER)
        """
        results = db_conn.execute(weekly_query).fetchall()

        if results:
            print("   Day        | Transactions | Total Spent | Avg Transaction")
            print("   -----------|--------------|-------------|----------------")
            for row in results:
                print(
                    f"   {row[0]:<10} | {row[1]:<12} | £{row[2]:<10} | £{row[3] or 0}"
                )
        else:
            print("   No weekly data found")
    except Exception as e:
        print(f"   Error analyzing weekly trends: {e}")


def search_transactions(db_conn, search_term):
    """Search for transactions containing a specific term."""
    print(f"\n🔎 SEARCHING FOR: '{search_term}'")
    print("-" * 50)

    try:
        search_query = """
        SELECT
            date,
            COALESCE(description, 'No description') as description,
            amount,
            COALESCE(category, 'Unknown') as category
        FROM transactions
        WHERE LOWER(description) LIKE LOWER(?)
           OR LOWER(category) LIKE LOWER(?)
        ORDER BY date DESC
        LIMIT 20
        """
        search_pattern = f"%{search_term}%"
        results = db_conn.execute(
            search_query, [search_pattern, search_pattern]
        ).fetchall()

        if results:
            print(
                "   Date       | Description                    | Amount    | Category"
            )
            print(
                "   -----------|---------------------------------|-----------|----------"
            )
            for row in results:
                desc = (row[1][:30] + "...") if len(str(row[1])) > 30 else str(row[1])
                print(f"   {row[0]:<10} | {desc:<31} | £{row[2]:<8} | {row[3]}")
        else:
            print(f"   No transactions found containing '{search_term}'")
    except Exception as e:
        print(f"   Error searching transactions: {e}")


def main():
    """Main function to demonstrate DuckDB financial analysis."""
    if len(sys.argv) < 5:
        print(
            "Usage: python duckdb_examples.py <spreadsheet_id> <sheet> <start_range> <end_range> [search_term]"
        )
        print("Example: python duckdb_examples.py 1ABC123XYZ Sheet1 A1 Z1000")
        print("Example: python duckdb_examples.py 1ABC123XYZ Sheet1 A1 Z1000 'coffee'")
        sys.exit(1)

    spreadsheet_id = sys.argv[1]
    sheet = sys.argv[2]
    start_range = sys.argv[3]
    end_range = sys.argv[4]
    search_term = sys.argv[5] if len(sys.argv) > 5 else None

    print("🏦 MONZO TRANSACTION ANALYSIS WITH DUCKDB")
    print("=" * 60)
    print(f"Spreadsheet: {spreadsheet_id}")
    print(f"Range: {sheet}!{start_range}:{end_range}")

    try:
        # Create MonzoTransactions instance
        monzo = MonzoTransactions(
            spreadsheet_id=spreadsheet_id,
            sheet=sheet,
            range=(start_range, end_range),
            credentials_path="credentials.json",
        )

        print("\n📥 Fetching data from Google Sheets...")
        data = monzo.data
        print(f"✓ Retrieved {len(data)} rows from spreadsheet")

        print("\n🗄️  Creating DuckDB database...")
        db_conn = monzo.duck_db()

        # Get basic table info
        count_result = db_conn.execute("SELECT COUNT(*) FROM transactions").fetchone()
        schema_result = db_conn.execute("DESCRIBE transactions").fetchall()

        print(f"✓ Created database with {count_result[0]} transactions")
        print(f"✓ Available columns: {[row[0] for row in schema_result]}")

        # Run analysis functions
        analyze_spending_patterns(db_conn)
        find_unusual_transactions(db_conn)
        analyze_merchant_patterns(db_conn)
        weekly_spending_trends(db_conn)

        # Optional search functionality
        if search_term:
            search_transactions(db_conn, search_term)

        # Custom query example
        print("\n" + "=" * 60)
        print("💡 CUSTOM QUERY EXAMPLE")
        print("=" * 60)
        print("You can run any SQL query against your data:")
        print("""
# Example custom queries:
# Recent transactions
db_conn.execute("SELECT * FROM transactions ORDER BY date DESC LIMIT 10")

# Transactions above £50
db_conn.execute("SELECT * FROM transactions WHERE ABS(CAST(amount AS DOUBLE)) > 50")

# Monthly totals
db_conn.execute(\"\"\"
    SELECT STRFTIME('%Y-%m', date) as month,
           SUM(ABS(CAST(amount AS DOUBLE))) as total
    FROM transactions
    GROUP BY month ORDER BY month
\"\"\")
        """)

        # Close database connection
        db_conn.close()
        print("\n✓ Database connection closed")
        print("\n🎉 Analysis complete!")

    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        print(f"\n❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
