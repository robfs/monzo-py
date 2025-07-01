"""Module defining the class to interact with Monzo transactions."""

import datetime
import json
import logging
import os
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path

import duckdb
import keyring
import pyarrow as pa
from google.auth.credentials import TokenState
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


class MonzoTransactions:
    """Class to interact with Monzo transactions via Google Sheets API.

    This class handles OAuth2 authentication with Google Sheets API and manages
    persistent token storage for seamless reuse across sessions. Tokens are stored
    in ~/.monzo-py/ directory for cross-session persistence.
    """

    def __init__(
        self,
        spreadsheet_id: str | None = None,
        *,
        sheet: str = "Personal Account Transactions",
        range_start: str = "A",
        range_end: str = "P",
        credentials_path: str | Path = "credentials.json",
        scopes: Sequence[str] = (
            "https://www.googleapis.com/auth/spreadsheets.readonly",
        ),
    ):
        self._spreadsheet_scopes: Sequence[str] = scopes
        self._spreadsheet_id: str | None = spreadsheet_id
        self._env_spreadsheet_id = os.environ.get("MONZO_SPREADSHEET_ID")
        if not (self._spreadsheet_id or self._env_spreadsheet_id):
            raise ValueError(
                "Spreadsheet ID is required as either parameter or MONZO_SPREADSHEET_ID environment variable."
            )
        self.sheet: str = sheet
        self.range: tuple[str, str] = range_start, range_end
        self._credentials_path: str | Path = credentials_path
        self._credentials = None
        self._keyring_service = "monzo-py"
        self._keyring_username = "google-oauth-token"
        logger.info("Creating Google Sheets service")
        self._data: list = []

    @property
    def spreadsheet_id(self) -> str | None:
        """Get the spreadsheet ID.

        Returns:
            str | None: The spreadsheet ID if set, None otherwise.
        """
        return self._spreadsheet_id or self._env_spreadsheet_id

    @property
    def range_name(self) -> str:
        """Get the formatted range name for Google Sheets API.

        Returns:
            str: Formatted range string in the format 'Sheet!A1:Z100'.
        """
        return f"{self.sheet}!{self.range[0]}:{self.range[1]}"

    def _token_exists(self) -> bool:
        """Check if a saved token exists in the system keyring.

        Returns:
            bool: True if the token exists in keyring, False otherwise.
        """
        try:
            token_json = keyring.get_password(
                self._keyring_service, self._keyring_username
            )
            exists = token_json is not None
            logger.debug(f"Checking token existence in keyring: {exists}")
            return exists
        except Exception as e:
            logger.warning(f"Error checking keyring for token: {e}")
            return False

    def _add_credentials_from_token(self) -> None:
        """Load credentials from an existing token stored in system keyring.

        Attempts to load previously saved OAuth2 credentials from the system keyring.

        Raises:
            ValueError: If no token exists in keyring or token is invalid.
        """
        logger.info("Attempting to load credentials from keyring")
        if not self._token_exists():
            logger.error("No token found in system keyring")
            raise ValueError("No token found in system keyring")

        try:
            token_json = keyring.get_password(
                self._keyring_service, self._keyring_username
            )
            if not token_json:
                raise ValueError("Token retrieved from keyring is empty")

            token_data = json.loads(token_json)
            self._credentials = Credentials.from_authorized_user_info(token_data)
            logger.info("Successfully loaded credentials from keyring")
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to load credentials from keyring: {e}")
            raise ValueError(f"Invalid token data in keyring: {e}") from e

    def _refresh_token(self) -> None:
        """Refresh the existing credentials token using Google's refresh mechanism.

        Uses the stored refresh token to obtain a new access token without
        requiring user interaction.

        Raises:
            ValueError: If credentials are not set.
        """
        logger.info("Attempting to refresh token")
        if self._credentials:
            logger.info("Refreshing existing credentials")
            self._credentials.refresh(Request())
            logger.info("Token refresh successful")
        else:
            logger.error("Cannot refresh token: credentials not set")
            raise ValueError("Credentials not set")

    def _add_credentials_from_secret(self) -> None:
        """Create credentials from the client secrets file using OAuth flow.

        This method will open a browser window for user authentication.
        """
        logger.info("Starting OAuth flow with client secrets file")
        logger.info(f"Using credentials file: {self._credentials_path}")
        flow = InstalledAppFlow.from_client_secrets_file(
            self._credentials_path, self._spreadsheet_scopes
        )
        logger.info("Opening browser for user authentication...")
        self._credentials = flow.run_local_server(port=0)
        logger.info("OAuth flow completed successfully")

    def _save_credentials(self) -> None:
        """Save the current credentials to system keyring.

        Saves OAuth2 credentials securely using the system keyring for reuse
        across sessions, eliminating the need for repeated authentication.

        Raises:
            ValueError: If credentials are not set.
        """
        logger.info("Saving credentials to system keyring")
        if not self._credentials:
            logger.error("Cannot save credentials: credentials not set")
            raise ValueError("Credentials not set")

        try:
            token_json = self._credentials.to_json()
            keyring.set_password(
                self._keyring_service, self._keyring_username, token_json
            )
            logger.info("Credentials saved successfully to keyring")
        except Exception as e:
            logger.error(f"Failed to save credentials to keyring: {e}")
            raise ValueError(f"Failed to save credentials: {e}") from e

    def credentials(self):
        """Get valid credentials for Google Sheets API access.

        This method handles the complete credential flow:
        - Loads existing token from keyring if available
        - Refreshes stale tokens
        - Initiates OAuth flow if no valid token exists
        - Saves credentials securely to keyring for future use

        Returns:
            Credentials: Valid Google API credentials.

        Raises:
            ValueError: If credentials cannot be obtained.
        """

        if not self._credentials and self._token_exists():
            try:
                self._add_credentials_from_token()
                token_state = (
                    self._credentials.token_state if self._credentials else None
                )
                if (
                    self._credentials
                    and token_state
                    and token_state == TokenState.STALE
                ):
                    logger.info("Refreshing stale token")
                    self._refresh_token()
                    self._save_credentials()
                if (
                    self._credentials
                    and token_state
                    and token_state == TokenState.INVALID
                ):
                    logger.info("Invalid token, initiating new OAuth flow")
                    self._add_credentials_from_secret()
                    self._save_credentials()
            except ValueError:
                logger.warning(
                    "Failed to load token from keyring, initiating new OAuth flow"
                )
                self._add_credentials_from_secret()
                self._save_credentials()
        elif not self._credentials:
            self._add_credentials_from_secret()
            self._save_credentials()

        if self._credentials is None:
            raise ValueError("Credentials not set")

        return self._credentials

    def clear_credentials(self) -> None:
        """Clear stored credentials from the system keyring.

        This method removes the OAuth2 token from the keyring and resets
        the internal credentials object. Useful for forcing re-authentication
        or when switching accounts.
        """
        logger.info("Clearing stored credentials from keyring")
        try:
            keyring.delete_password(self._keyring_service, self._keyring_username)
            logger.info("Successfully cleared credentials from keyring")
        except Exception as e:
            logger.warning(f"Could not clear credentials from keyring: {e}")

        # Reset internal credentials object
        self._credentials = None
        logger.info("Internal credentials object reset")

    def fetch_data(self):
        """Fetch data from the Google Sheets spreadsheet.

        Retrieves data from the specified spreadsheet, sheet, and range using
        the Google Sheets API. The fetched data is stored in the internal
        _data attribute for later access.

        The data is returned as a list of lists, where each inner list represents
        a row from the spreadsheet.

        Raises:
            Exception: If the API call fails or the spreadsheet/range is invalid.
        """
        logger.info("Fetching data from Google Sheets")
        logger.debug(f"Spreadsheet ID: {self.spreadsheet_id}")
        logger.debug(f"Range: {self.range_name}")

        sheet = self.service().spreadsheets()
        result = (
            sheet.values()
            .get(spreadsheetId=self.spreadsheet_id, range=self.range_name)
            .execute()
        )
        self._data = result.get("values", [])
        logger.info(f"Successfully fetched {len(self._data)} rows from spreadsheet")

    @property
    def data(self):
        """Get the spreadsheet data, fetching it if not already loaded.

        This property provides lazy loading of spreadsheet data. If the data
        hasn't been fetched yet, it will automatically call fetch_data() to
        retrieve it from the Google Sheets API.

        Returns:
            list: A list of lists representing the spreadsheet data, where each
                  inner list is a row from the specified range.
        """
        logger.debug("Accessing data property")
        if not self._data:
            logger.debug("Data not cached, fetching from spreadsheet")
            self.fetch_data()
        else:
            logger.debug(f"Returning cached data with {len(self._data)} rows")
        return self._data

    def service(self):
        """Build and return a Google Sheets API service object.

        Creates a Google Sheets API service instance using the authenticated
        credentials. This service object is used to make API calls to Google Sheets.

        Returns:
            googleapiclient.discovery.Resource: A Google Sheets API service object
                                               configured with valid credentials.

        Raises:
            Exception: If the service cannot be built due to authentication or
                      connection issues.
        """
        logger.debug("Building Google Sheets API service")
        service = build(
            "sheets",
            "v4",
            credentials=self.credentials(),
            cache_discovery=False,  # cache_discovery=False due to version
        )
        logger.debug("Google Sheets API service built successfully")
        return service

    def _get_column_definitions(self):
        """Get the standard Monzo transaction column definitions.

        Returns:
            list: List of tuples containing (column_name, duckdb_type, pyarrow_type)
        """
        return [
            ("transaction_id", "VARCHAR", pa.string()),
            ("date", "DATE", pa.date32()),
            ("time", "TIME", pa.time64("us")),
            ("type", "VARCHAR", pa.string()),
            ("name", "VARCHAR", pa.string()),
            ("emoji", "VARCHAR", pa.string()),
            ("category", "VARCHAR", pa.string()),
            ("amount", "DECIMAL(10,2)", pa.decimal128(10, 2)),
            ("currency", "VARCHAR", pa.string()),
            ("local_amount", "DECIMAL(10,2)", pa.decimal128(10, 2)),
            ("local_currency", "VARCHAR", pa.string()),
            ("notes_and_tags", "VARCHAR", pa.string()),
            ("address", "VARCHAR", pa.string()),
            ("receipt", "VARCHAR", pa.string()),
            ("description", "VARCHAR", pa.string()),
            ("category_split", "VARCHAR", pa.string()),
        ]

    def _create_empty_table(self, conn, column_definitions):
        """Create an empty DuckDB table with Monzo structure.

        Args:
            conn: DuckDB connection
            column_definitions: List of column definition tuples
        """
        columns_def = [
            f"{name} {duck_type}" for name, duck_type, _ in column_definitions
        ]
        conn.execute(f"CREATE TABLE transactions ({', '.join(columns_def)})")
        logger.info("Created empty DuckDB table with Monzo structure")

    def _get_type_converters(self):
        """Get data type conversion functions.

        Returns:
            dict: Mapping of PyArrow types to conversion functions
        """

        def convert_decimal(value):
            if value is None or value == "":
                return None
            try:
                return Decimal(str(value))
            except (ValueError, TypeError):
                return None

        def convert_date(value):
            if value is None or value == "":
                return None
            try:
                return datetime.datetime.strptime(value, "%d/%m/%Y").date()
            except (ValueError, TypeError):
                return None

        def convert_time(value):
            if value is None or value == "":
                return None
            try:
                return datetime.datetime.strptime(value, "%H:%M:%S").time()
            except (ValueError, TypeError):
                return None

        return {
            pa.decimal128(10, 2): convert_decimal,
            pa.date32(): convert_date,
            pa.time64("us"): convert_time,
        }

    def _convert_data_columns(self, table_data, column_definitions):
        """Convert raw data to appropriate types for PyArrow.

        Args:
            table_data: Raw spreadsheet data (excluding headers)
            column_definitions: List of column definition tuples

        Returns:
            dict: Dictionary of converted column data
        """
        converted_columns = {}
        type_converters = self._get_type_converters()

        for i, (column_name, _, pa_type) in enumerate(column_definitions):
            # Extract column data, padding with None if row is too short
            column_data = []
            for row in table_data:
                if i < len(row):
                    if pa_type in type_converters:
                        value = type_converters[pa_type](row[i])
                    else:
                        value = row[i]
                    # Convert empty strings to None for cleaner data
                    # value = value if value != "" else None
                    column_data.append(value)
                else:
                    column_data.append(None)

            # Apply type conversion if needed
            # if pa_type in type_converters:
            #     converted_columns[column_name] = [
            #         type_converters[pa_type](value) for value in column_data
            #     ]
            # else:
            converted_columns[column_name] = column_data

        return converted_columns

    def _validate_data_for_database(self) -> list:
        """Validate that data is available for database creation.

        Returns:
            list: The validated data

        Raises:
            ValueError: If no data is available
        """
        data = self.data
        if not data:
            logger.error("No data available to create DuckDB database")
            raise ValueError("No data available to create DuckDB database")
        return data

    def _create_duckdb_connection(self) -> duckdb.DuckDBPyConnection:
        """Create an in-memory DuckDB connection.

        Returns:
            duckdb.DuckDBPyConnection: A new DuckDB connection
        """
        conn = duckdb.connect(":memory:")
        logger.debug("DuckDB connection created")
        return conn

    def _handle_empty_data(self, conn: duckdb.DuckDBPyConnection, data: list) -> bool:
        """Handle the case where data has only headers or is empty.

        Args:
            conn: The DuckDB connection
            data: The data list

        Returns:
            bool: True if data was empty and handled, False if processing should continue
        """
        if len(data) <= 1:
            column_definitions = self._get_column_definitions()
            self._create_empty_table(conn, column_definitions)
            return True
        return False

    def _create_pyarrow_table(self, table_data: list) -> pa.Table:
        """Create a PyArrow table from the transaction data.

        Args:
            table_data: The data rows (excluding headers)

        Returns:
            pa.Table: A PyArrow table with converted data types
        """
        column_definitions = self._get_column_definitions()
        schema = pa.schema([(name, pa_type) for name, _, pa_type in column_definitions])
        converted_columns = self._convert_data_columns(table_data, column_definitions)
        return pa.table(converted_columns, schema=schema)

    def _register_table_with_duckdb(
        self, conn: duckdb.DuckDBPyConnection, arrow_table: pa.Table
    ) -> None:
        """Register the PyArrow table with DuckDB.

        Args:
            conn: The DuckDB connection
            arrow_table: The PyArrow table to register
        """
        conn.register("transactions", arrow_table)
        logger.info(
            f"Created DuckDB table using PyArrow with {len(arrow_table)} rows and 16 columns"
        )

    def _log_database_stats(self, conn: duckdb.DuckDBPyConnection) -> None:
        """Log statistics about the created database.

        Args:
            conn: The DuckDB connection
        """
        try:
            result = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()
            if result is not None:
                logger.info(
                    f"Successfully created DuckDB database with {result[0]} data rows"
                )
            else:
                logger.warning("Could not retrieve row count from DuckDB database")
        except Exception as e:
            logger.warning(f"Could not retrieve row count from DuckDB database: {e}")

    def duck_db(self):
        """Create an in-memory DuckDB database with the spreadsheet data.

        Creates a new in-memory DuckDB database and populates it with the
        spreadsheet data using PyArrow for optimized performance. The data is
        stored in a table named 'transactions' with standard Monzo export column names.

        The first row of the spreadsheet is assumed to contain column headers
        and is skipped. Uses hardcoded column names matching Monzo's export format.

        PyArrow is used to create a columnar table structure that can be efficiently
        transferred to DuckDB, providing significant performance improvements over
        row-by-row insertion, especially for large datasets.

        Returns:
            duckdb.DuckDBPyConnection: A DuckDB connection object with the
                                      spreadsheet data loaded into a table.

        Raises:
            ValueError: If no data is available to load into the database.
        """
        logger.info("Creating in-memory DuckDB database")

        # Validate that we have data to work with
        data = self._validate_data_for_database()

        # Create the database connection
        conn = self._create_duckdb_connection()

        # Handle the case where we only have headers or no data
        if self._handle_empty_data(conn, data):
            return conn

        # Process the actual data (skip header row)
        table_data = data[1:]

        # Create PyArrow table with converted data types
        arrow_table = self._create_pyarrow_table(table_data)

        # Register the table with DuckDB
        self._register_table_with_duckdb(conn, arrow_table)

        # Log database statistics
        self._log_database_stats(conn)

        return conn


if __name__ == "__main__":
    import sys

    # Set logging level to DEBUG for command-line usage
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.setLevel(logging.DEBUG)

    if len(sys.argv) != 2:
        print("Usage: python monzo_transactions.py <spreadsheet_id>")
        sys.exit(1)

    spreadsheet_id = sys.argv[1]

    monzo_transactions = MonzoTransactions(spreadsheet_id)
    credentials = monzo_transactions.credentials()
    print("Fetching data...")
    data = monzo_transactions.data
    print(f"Data fetched:\n\n{data}")

    # Demonstrate DuckDB functionality
    print("\nCreating DuckDB in-memory database...")
    try:
        db_conn = monzo_transactions.duck_db()
        print("✓ DuckDB database created successfully")

        # Show basic table info
        count_result = db_conn.execute("SELECT COUNT(*) FROM transactions").fetchone()
        if count_result is not None:
            print(f"✓ Database contains {count_result[0]} rows")
        else:
            print("! Could not retrieve row count from database")

        # Show column info
        schema_result = db_conn.execute("DESCRIBE transactions").fetchall()
        print(f"✓ Table columns: {[row[0] for row in schema_result]}")

        db_conn.close()
        print("✓ Database connection closed")
    except Exception as e:
        print(f"❌ DuckDB error: {e}")
