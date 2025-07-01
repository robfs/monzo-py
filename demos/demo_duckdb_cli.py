#!/usr/bin/env python3
"""Example script demonstrating the duck_db method of MonzoTransactions."""

import logging
import sys

from monzo_py import MonzoTransactions

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Demonstrate the duck_db functionality."""
    if len(sys.argv) != 5:
        print(
            "Usage: python test_duckdb.py <spreadsheet_id> <sheet> <start_range> <end_range>"
        )
        print("Example: python test_duckdb.py 1ABC123XYZ Sheet1 A1 Z100")
        sys.exit(1)

    spreadsheet_id = sys.argv[1]
    sheet = sys.argv[2]
    start_range = sys.argv[3]
    end_range = sys.argv[4]

    print(f"Creating MonzoTransactions instance for {sheet}!{start_range}:{end_range}")

    # Create MonzoTransactions instance
    monzo = MonzoTransactions(
        spreadsheet_id=spreadsheet_id,
        sheet=sheet,
        range=(start_range, end_range),
        credentials_path="credentials.json",
    )

    try:
        print("Fetching data from Google Sheets...")
        data = monzo.data
        print(f"✓ Fetched {len(data)} rows from spreadsheet")

        if data:
            print("✓ Sample data (first 2 rows):")
            for i, row in enumerate(data[:2]):
                print(f"  Row {i}: {row}")

        print("\nCreating DuckDB in-memory database...")
        db_conn = monzo.duck_db()
        print("✓ DuckDB database created successfully")

        # Demonstrate some basic queries
        print("\n" + "=" * 50)
        print("DEMONSTRATING DUCKDB QUERIES")
        print("=" * 50)

        # Show table structure
        print("\n1. Table schema:")
        schema_result = db_conn.execute("DESCRIBE transactions").fetchall()
        for row in schema_result:
            print(f"   {row[0]}: {row[1]}")

        # Count rows
        print("\n2. Total rows in table:")
        count_result = db_conn.execute("SELECT COUNT(*) FROM transactions").fetchone()
        print(f"   {count_result[0]} rows")

        # Show first few rows
        print("\n3. First 3 rows from database:")
        sample_result = db_conn.execute("SELECT * FROM transactions LIMIT 3").fetchall()
        for i, row in enumerate(sample_result):
            print(f"   Row {i + 1}: {row}")

        # Show column names
        print("\n4. Available columns:")
        columns_result = db_conn.execute("PRAGMA table_info(transactions)").fetchall()
        column_names = [col[1] for col in columns_result]
        print(f"   {column_names}")

        # Demonstrate a simple aggregation (if numeric columns exist)
        print("\n5. Attempting sample queries...")
        try:
            # Try to find numeric columns and do some basic stats
            numeric_cols = []
            for col_info in columns_result:
                col_name = col_info[1]
                try:
                    # Try to cast the column to numeric to see if it contains numbers
                    test_query = f"SELECT COUNT(*) FROM transactions WHERE TRY_CAST({col_name} AS DOUBLE) IS NOT NULL AND {col_name} IS NOT NULL"
                    result = db_conn.execute(test_query).fetchone()
                    if result[0] > 0:
                        numeric_cols.append(col_name)
                except Exception:
                    pass

            if numeric_cols:
                print(f"   Found numeric columns: {numeric_cols}")
                for col in numeric_cols[:2]:  # Just show first 2 numeric columns
                    try:
                        stats_query = f"""
                        SELECT
                            COUNT(*) as count,
                            MIN(TRY_CAST({col} AS DOUBLE)) as min_val,
                            MAX(TRY_CAST({col} AS DOUBLE)) as max_val,
                            AVG(TRY_CAST({col} AS DOUBLE)) as avg_val
                        FROM transactions
                        WHERE TRY_CAST({col} AS DOUBLE) IS NOT NULL
                        """
                        stats_result = db_conn.execute(stats_query).fetchone()
                        print(
                            f"   Stats for {col}: count={stats_result[0]}, min={stats_result[1]}, max={stats_result[2]}, avg={stats_result[3]:.2f}"
                        )
                    except Exception as e:
                        print(f"   Could not calculate stats for {col}: {e}")
            else:
                print("   No numeric columns detected for aggregation")

        except Exception as e:
            print(f"   Error running sample queries: {e}")

        print("\n6. Custom query example:")
        print("   You can now run any SQL query against the 'transactions' table!")
        print(
            "   Example: db_conn.execute('SELECT * FROM transactions WHERE column_name = ?', [value])"
        )

        # Close the database connection
        db_conn.close()
        print("\n✓ Database connection closed")

    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"❌ Error: {e}")
        return 1

    print("\n🎉 DuckDB demonstration completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
