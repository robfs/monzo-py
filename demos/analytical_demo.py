#!/usr/bin/env python3
"""Comprehensive analytical demo showcasing the power of properly typed columns in DuckDB."""

import logging

from monzo_py import MonzoTransactions


def run_comprehensive_analysis(spreadsheet_id):
    """Run a comprehensive financial analysis using the properly typed DuckDB implementation."""
    # Set up logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise

    print("🔍 COMPREHENSIVE MONZO TRANSACTION ANALYSIS")
    print("=" * 80)

    # Create instance and DuckDB connection
    print("📊 Setting up data connection...")
    monzo = MonzoTransactions(spreadsheet_id)
    db_conn = monzo.duck_db()

    # Basic statistics
    print("\n📈 BASIC STATISTICS")
    print("-" * 40)

    basic_stats = db_conn.execute("""
        SELECT
            COUNT(*) as total_transactions,
            MIN(date) as earliest_transaction,
            MAX(date) as latest_transaction,
            COUNT(DISTINCT date) as unique_days,
            SUM(CASE WHEN amount > 0 THEN 1 ELSE 0 END) as income_transactions,
            SUM(CASE WHEN amount < 0 THEN 1 ELSE 0 END) as expense_transactions,
            ROUND(SUM(amount), 2) as net_total,
            ROUND(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 2) as total_income,
            ROUND(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END), 2) as total_expenses
        FROM transactions
    """).fetchone()

    print(f"📊 Total Transactions: {basic_stats[0]:,}")
    print(f"📅 Period: {basic_stats[1]} to {basic_stats[2]} ({basic_stats[3]:,} days)")
    print(f"💰 Net Balance: £{basic_stats[6]:,}")
    print(f"💵 Total Income: £{basic_stats[7]:,} ({basic_stats[4]} transactions)")
    print(f"💸 Total Expenses: £{basic_stats[8]:,} ({basic_stats[5]} transactions)")

    # Time-based analysis
    print("\n🕒 TIME-BASED ANALYSIS")
    print("-" * 40)

    # Monthly spending
    monthly_spending = db_conn.execute("""
        SELECT
            strftime('%Y-%m', date) as month,
            COUNT(*) as transactions,
            ROUND(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 2) as expenses,
            ROUND(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 2) as income
        FROM transactions
        WHERE date >= '2024-01-01'  -- Focus on recent data
        GROUP BY strftime('%Y-%m', date)
        ORDER BY month DESC
        LIMIT 6
    """).fetchall()

    print("📅 Recent Monthly Summary:")
    for month_data in monthly_spending:
        print(
            f"   {month_data[0]}: {month_data[1]} txns, £{month_data[2]:,} expenses, £{month_data[3]:,} income"
        )

    # Day of week analysis
    dow_analysis = db_conn.execute("""
        SELECT
            strftime('%w', date) as dow_num,
            CASE strftime('%w', date)
                WHEN '0' THEN 'Sunday'
                WHEN '1' THEN 'Monday'
                WHEN '2' THEN 'Tuesday'
                WHEN '3' THEN 'Wednesday'
                WHEN '4' THEN 'Thursday'
                WHEN '5' THEN 'Friday'
                WHEN '6' THEN 'Saturday'
            END as day_of_week,
            COUNT(*) as transactions,
            ROUND(AVG(CASE WHEN amount < 0 THEN ABS(amount) ELSE NULL END), 2) as avg_expense
        FROM transactions
        WHERE amount < 0
        GROUP BY strftime('%w', date)
        ORDER BY CAST(strftime('%w', date) AS INTEGER)
    """).fetchall()

    print("\n📅 Spending by Day of Week:")
    for dow in dow_analysis:
        print(f"   {dow[1]}: {dow[2]} transactions, avg £{dow[3]} per expense")

    # Hour analysis
    hourly_spending = db_conn.execute("""
        SELECT
            EXTRACT(HOUR FROM time) as hour,
            COUNT(*) as transactions,
            ROUND(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 2) as total_spent
        FROM transactions
        WHERE amount < 0 AND time IS NOT NULL
        GROUP BY EXTRACT(HOUR FROM time)
        ORDER BY total_spent DESC
        LIMIT 5
    """).fetchall()

    print("\n🕐 Top 5 Spending Hours:")
    for hour_data in hourly_spending:
        print(f"   {hour_data[0]}:00 - £{hour_data[2]:,} ({hour_data[1]} transactions)")

    # Category analysis
    print("\n🏷️ CATEGORY ANALYSIS")
    print("-" * 40)

    category_analysis = db_conn.execute("""
        SELECT
            category,
            COUNT(*) as transactions,
            ROUND(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 2) as total_spent,
            ROUND(AVG(CASE WHEN amount < 0 THEN ABS(amount) ELSE NULL END), 2) as avg_transaction,
            ROUND(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) * 100.0 /
                  (SELECT SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) FROM transactions), 2) as percentage
        FROM transactions
        WHERE amount < 0 AND category IS NOT NULL AND category != ''
        GROUP BY category
        ORDER BY total_spent DESC
        LIMIT 10
    """).fetchall()

    print("💰 Top 10 Spending Categories:")
    for cat in category_analysis:
        print(
            f"   {cat[0]:<20} £{cat[2]:>8,} ({cat[4]:>5}%) - {cat[1]:>4} txns, avg £{cat[3]}"
        )

    # Merchant analysis
    print("\n🏪 MERCHANT ANALYSIS")
    print("-" * 40)

    top_merchants = db_conn.execute("""
        SELECT
            name,
            COUNT(*) as visits,
            ROUND(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 2) as total_spent,
            ROUND(AVG(CASE WHEN amount < 0 THEN ABS(amount) ELSE NULL END), 2) as avg_spend
        FROM transactions
        WHERE amount < 0 AND name IS NOT NULL AND name != ''
        GROUP BY name
        ORDER BY total_spent DESC
        LIMIT 10
    """).fetchall()

    print("🛒 Top 10 Merchants by Total Spending:")
    for merchant in top_merchants:
        print(
            f"   {merchant[0]:<30} £{merchant[2]:>8,} - {merchant[1]:>3} visits, avg £{merchant[3]}"
        )

    # Largest transactions
    print("\n💎 NOTABLE TRANSACTIONS")
    print("-" * 40)

    largest_expenses = db_conn.execute("""
        SELECT date, name, category, ABS(amount) as amount, description
        FROM transactions
        WHERE amount < 0
        ORDER BY ABS(amount) DESC
        LIMIT 5
    """).fetchall()

    print("💸 Top 5 Largest Expenses:")
    for i, exp in enumerate(largest_expenses, 1):
        desc = exp[4][:40] + "..." if exp[4] and len(exp[4]) > 40 else exp[4] or ""
        print(f"   {i}. £{exp[3]:,} - {exp[1]} ({exp[2]}) on {exp[0]}")
        if desc:
            print(f"      {desc}")

    largest_income = db_conn.execute("""
        SELECT date, name, category, amount, description
        FROM transactions
        WHERE amount > 0
        ORDER BY amount DESC
        LIMIT 5
    """).fetchall()

    print("\n💰 Top 5 Largest Income:")
    for i, inc in enumerate(largest_income, 1):
        desc = inc[4][:40] + "..." if inc[4] and len(inc[4]) > 40 else inc[4] or ""
        print(f"   {i}. £{inc[3]:,} - {inc[1]} ({inc[2]}) on {inc[0]}")
        if desc:
            print(f"      {desc}")

    # Advanced time analysis
    print("\n📊 ADVANCED ANALYSIS")
    print("-" * 40)

    # Weekend vs weekday spending
    weekend_analysis = db_conn.execute("""
        SELECT
            CASE
                WHEN strftime('%w', date) IN ('0', '6') THEN 'Weekend'
                ELSE 'Weekday'
            END as period_type,
            COUNT(*) as transactions,
            ROUND(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 2) as total_spent,
            ROUND(AVG(CASE WHEN amount < 0 THEN ABS(amount) ELSE NULL END), 2) as avg_spend
        FROM transactions
        WHERE amount < 0
        GROUP BY CASE WHEN strftime('%w', date) IN ('0', '6') THEN 'Weekend' ELSE 'Weekday' END
    """).fetchall()

    print("📅 Weekend vs Weekday Spending:")
    for period in weekend_analysis:
        print(
            f"   {period[0]}: £{period[2]:,} total, £{period[3]} avg ({period[1]} transactions)"
        )

    # Seasonal analysis (by quarter)
    seasonal_analysis = db_conn.execute("""
        SELECT
            CASE
                WHEN strftime('%m', date) IN ('01', '02', '03') THEN 'Q1 (Jan-Mar)'
                WHEN strftime('%m', date) IN ('04', '05', '06') THEN 'Q2 (Apr-Jun)'
                WHEN strftime('%m', date) IN ('07', '08', '09') THEN 'Q3 (Jul-Sep)'
                ELSE 'Q4 (Oct-Dec)'
            END as quarter,
            ROUND(AVG(CASE WHEN amount < 0 THEN ABS(amount) ELSE NULL END), 2) as avg_expense
        FROM transactions
        WHERE amount < 0 AND date >= '2023-01-01'
        GROUP BY CASE
            WHEN strftime('%m', date) IN ('01', '02', '03') THEN 'Q1 (Jan-Mar)'
            WHEN strftime('%m', date) IN ('04', '05', '06') THEN 'Q2 (Apr-Jun)'
            WHEN strftime('%m', date) IN ('07', '08', '09') THEN 'Q3 (Jul-Sep)'
            ELSE 'Q4 (Oct-Dec)'
        END
        ORDER BY avg_expense DESC
    """).fetchall()

    print("\n🌍 Seasonal Spending Patterns (2023+):")
    for season in seasonal_analysis:
        print(f"   {season[0]}: £{season[1]} average expense")

    # Transaction frequency analysis
    frequency_analysis = db_conn.execute("""
        WITH daily_transactions AS (
            SELECT
                date,
                COUNT(*) as daily_count,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as daily_spending
            FROM transactions
            WHERE date >= '2024-01-01'
            GROUP BY date
        )
        SELECT
            ROUND(AVG(daily_count), 1) as avg_transactions_per_day,
            ROUND(AVG(daily_spending), 2) as avg_spending_per_day,
            MAX(daily_count) as max_transactions_day,
            MAX(daily_spending) as max_spending_day
        FROM daily_transactions
    """).fetchone()

    print("\n📊 Daily Activity (2024):")
    print(
        f"   Average: {frequency_analysis[0]} transactions, £{frequency_analysis[1]} spending per day"
    )
    print(
        f"   Maximum: {frequency_analysis[2]} transactions, £{frequency_analysis[3]} spending in a single day"
    )

    # Close connection
    db_conn.close()

    print("\n" + "=" * 80)
    print("✅ ANALYSIS COMPLETE - All data types working perfectly!")
    print("   📅 Dates: Proper DATE type enabling time-based analysis")
    print("   🕐 Times: Proper TIME type for hourly patterns")
    print("   💰 Amounts: Proper DECIMAL type for accurate financial calculations")
    print("=" * 80)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python analytical_demo.py <spreadsheet_id>")
        sys.exit(1)

    spreadsheet_id = sys.argv[1]
    try:
        run_comprehensive_analysis(spreadsheet_id)
    except KeyboardInterrupt:
        print("\n\n⏹️  Analysis interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback

        traceback.print_exc()
