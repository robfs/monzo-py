#!/usr/bin/env python3
"""
Example script demonstrating secure usage of MonzoTransactions with keyring storage.

This example shows how to use the updated MonzoTransactions class that stores
OAuth2 credentials securely in the system keyring instead of plaintext files.
"""

import logging
import sys
from pathlib import Path

# Add the src directory to the path so we can import monzo_py
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from monzo_py.monzo_transactions import MonzoTransactions

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def main():
    """Example usage of MonzoTransactions with secure keyring storage."""

    # Your Google Sheets configuration
    SPREADSHEET_ID = (
        "your-spreadsheet-id-here"  # Replace with your actual spreadsheet ID
    )
    CREDENTIALS_FILE = "credentials.json"  # Path to your Google OAuth2 credentials file

    print("🔒 MonzoTransactions Secure Usage Example")
    print("=" * 50)

    try:
        # Initialize MonzoTransactions
        # Credentials will now be stored securely in system keyring
        print("Initializing MonzoTransactions with secure keyring storage...")
        monzo = MonzoTransactions(
            spreadsheet_id=SPREADSHEET_ID,
            credentials_path=CREDENTIALS_FILE,
            sheet="Personal Account Transactions",  # Adjust sheet name as needed
            range=("A", "P"),  # Adjust range as needed
        )

        print("✓ MonzoTransactions initialized")

        # The first time you run this, it will:
        # 1. Check if credentials exist in keyring
        # 2. If not, open browser for OAuth flow
        # 3. Store the credentials securely in keyring
        # 4. Subsequent runs will use stored credentials automatically

        print("\nFetching data from Google Sheets...")
        data = monzo.data  # This will trigger authentication if needed
        print(f"✓ Successfully fetched {len(data)} rows")

        # Display first few rows as example
        if data:
            print("\nFirst few rows:")
            for i, row in enumerate(data[:3]):
                print(f"Row {i + 1}: {row}")

        # Create DuckDB database for analysis
        print("\nCreating DuckDB database...")
        db = monzo.duck_db()
        print("✓ Database created successfully")

        # Example query
        result = db.execute(
            "SELECT COUNT(*) as total_transactions FROM transactions"
        ).fetchone()
        if result:
            print(f"✓ Total transactions in database: {result[0]}")

        print("\n🎉 Example completed successfully!")
        print(
            "\nYour OAuth2 credentials are now stored securely in your system keyring."
        )
        print("Future runs will automatically use the stored credentials.")

    except FileNotFoundError:
        print("❌ Error: credentials.json file not found!")
        print("\nTo fix this:")
        print("1. Go to Google Cloud Console")
        print("2. Create a new project or select existing one")
        print("3. Enable Google Sheets API")
        print("4. Create OAuth2 credentials (Desktop application)")
        print("5. Download the credentials file as 'credentials.json'")
        print("6. Update SPREADSHEET_ID in this script")

    except ValueError as e:
        if "spreadsheet-id-here" in str(e) or "SPREADSHEET_ID" in str(e):
            print(
                "❌ Error: Please update SPREADSHEET_ID with your actual spreadsheet ID"
            )
            print("\nTo get your spreadsheet ID:")
            print("1. Open your Google Sheet")
            print(
                "2. Look at the URL: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit"
            )
            print("3. Copy the SPREADSHEET_ID part")
        else:
            print(f"❌ Error: {e}")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("\nIf you're migrating from the old file-based storage,")
        print("run the migration script: python migrate_to_keyring.py")


def demonstrate_credential_management():
    """Demonstrate credential management features."""
    print("\n" + "=" * 50)
    print("🔧 Credential Management Examples")
    print("=" * 50)

    # Example configuration (you'd use your real values)
    SPREADSHEET_ID = "example-id"

    try:
        monzo = MonzoTransactions(spreadsheet_id=SPREADSHEET_ID)

        # Check if credentials exist
        if monzo._token_exists():
            print("✓ Credentials found in keyring")

            # Clear credentials if needed (e.g., to switch accounts)
            response = input("Clear stored credentials? (y/N): ").lower().strip()
            if response == "y":
                monzo.clear_credentials()
                print("✓ Credentials cleared from keyring")
                print("Next authentication will require browser login")
        else:
            print("No credentials found in keyring")
            print("First authentication will require browser login")

    except Exception as e:
        print(f"Error in credential management demo: {e}")


if __name__ == "__main__":
    main()

    # Uncomment the line below to see credential management examples
    # demonstrate_credential_management()

    print("\n" + "=" * 50)
    print("Security Benefits of Keyring Storage:")
    print("=" * 50)
    print("🔒 Credentials encrypted by your operating system")
    print("🔒 No plaintext files on disk")
    print("🔒 Access controlled by OS security policies")
    print("🔒 Automatic cleanup when user account is removed")
    print("🔒 Integration with system security features")
    print("=" * 50)
