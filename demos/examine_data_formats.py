#!/usr/bin/env python3
"""Script to examine the actual data formats in the Monzo spreadsheet."""

import logging

from monzo_py import MonzoTransactions


def examine_data_formats(spreadsheet_id):
    """Examine the data formats in the live spreadsheet."""
    # Set up logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise

    print("Examining data formats in Monzo spreadsheet...")
    print("=" * 60)

    # Create instance and fetch data
    monzo = MonzoTransactions(spreadsheet_id)
    data = monzo.data

    print(f"Total rows: {len(data)}")
    print(f"Headers: {data[0]}")
    print()

    # Look at first few data rows to understand formats
    print("Sample data rows:")
    for i in range(1, min(6, len(data))):
        print(f"Row {i}: {data[i]}")
    print()

    # Examine specific column formats
    if len(data) > 1:
        sample_rows = data[1 : min(21, len(data))]  # First 20 data rows

        print("Column format analysis:")
        print("-" * 40)

        # Date column (index 1)
        dates = [row[1] if len(row) > 1 else None for row in sample_rows]
        print(f"Date samples: {dates[:5]}")

        # Time column (index 2)
        times = [row[2] if len(row) > 2 else None for row in sample_rows]
        print(f"Time samples: {times[:5]}")

        # Amount column (index 7)
        amounts = [row[7] if len(row) > 7 else None for row in sample_rows]
        print(f"Amount samples: {amounts[:5]}")

        # Local amount column (index 9)
        local_amounts = [row[9] if len(row) > 9 else None for row in sample_rows]
        print(f"Local amount samples: {local_amounts[:5]}")

        print()
        print("Detailed format analysis:")
        print("-" * 40)

        # Analyze date format
        unique_date_formats = set()
        for date_val in dates[:10]:
            if date_val:
                unique_date_formats.add(f"'{date_val}' (len={len(date_val)})")
        print(f"Date formats found: {list(unique_date_formats)}")

        # Analyze time format
        unique_time_formats = set()
        for time_val in times[:10]:
            if time_val:
                unique_time_formats.add(f"'{time_val}' (len={len(time_val)})")
        print(f"Time formats found: {list(unique_time_formats)}")

        # Analyze amount format
        unique_amount_formats = set()
        for amount_val in amounts[:10]:
            if amount_val:
                unique_amount_formats.add(
                    f"'{amount_val}' (type={type(amount_val).__name__})"
                )
        print(f"Amount formats found: {list(unique_amount_formats)}")

        print()
        print("Empty/None value analysis:")
        print("-" * 40)

        # Count empty values
        empty_dates = sum(1 for d in dates if not d or d == "")
        empty_times = sum(1 for t in times if not t or t == "")
        empty_amounts = sum(1 for a in amounts if not a or a == "")

        print(f"Empty dates: {empty_dates}/{len(dates)}")
        print(f"Empty times: {empty_times}/{len(times)}")
        print(f"Empty amounts: {empty_amounts}/{len(amounts)}")

        # Look for different date formats in larger sample
        print()
        print("Broader date format analysis (first 100 rows):")
        print("-" * 40)

        larger_sample = data[1 : min(101, len(data))]
        date_patterns = {}

        for row in larger_sample:
            if len(row) > 1 and row[1]:
                date_str = row[1]
                # Categorize by pattern
                if "/" in date_str:
                    parts = date_str.split("/")
                    pattern = f"{len(parts[0])}digit/{len(parts[1])}digit/{len(parts[2])}digit"
                    date_patterns[pattern] = date_patterns.get(pattern, 0) + 1
                elif "-" in date_str:
                    parts = date_str.split("-")
                    pattern = f"{len(parts[0])}digit-{len(parts[1])}digit-{len(parts[2])}digit"
                    date_patterns[pattern] = date_patterns.get(pattern, 0) + 1
                else:
                    date_patterns["other"] = date_patterns.get("other", 0) + 1

        print(f"Date patterns found: {date_patterns}")

        # Analyze amount values more deeply
        print()
        print("Amount value analysis:")
        print("-" * 40)

        amount_analysis = {
            "positive": 0,
            "negative": 0,
            "zero": 0,
            "non_numeric": 0,
            "empty": 0,
        }

        for row in larger_sample:
            if len(row) > 7:
                amount_str = row[7]
                if not amount_str or amount_str == "":
                    amount_analysis["empty"] += 1
                else:
                    try:
                        amount_val = float(amount_str)
                        if amount_val > 0:
                            amount_analysis["positive"] += 1
                        elif amount_val < 0:
                            amount_analysis["negative"] += 1
                        else:
                            amount_analysis["zero"] += 1
                    except (ValueError, TypeError):
                        amount_analysis["non_numeric"] += 1

        print(f"Amount analysis: {amount_analysis}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python examine_data_formats.py <spreadsheet_id>")
        sys.exit(1)

    spreadsheet_id = sys.argv[1]

    examine_data_formats(spreadsheet_id)
