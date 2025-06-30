"""Module defining the class to interact with Monzo transactions."""

import datetime
import logging
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path

import duckdb
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
        spreadsheet_id: str,
        *,
        sheet: str = "Personal Account Transactions",
        range: tuple[str, str] = ("A", "P"),
        credentials_path: str | Path = "credentials.json",
        scopes: Sequence[str] = (
            "https://www.googleapis.com/auth/spreadsheets.readonly",
        ),
    ):
        self._spreadsheet_scopes: Sequence[str] = scopes
        self.spreadsheet_id: str = spreadsheet_id
        self.sheet: str = sheet
        self.range: tuple[str, str] = range
        self._credentials_path: str | Path = credentials_path
        self._credentials = None
        self._token_dir = Path.home() / ".monzo-py"
        self._token_path = self._token_dir / "monzo_token.json"
        logger.info("Creating Google Sheets service")
        self._data: list = []

    @property
    def range_name(self) -> str:
        """Get the formatted range name for Google Sheets API.

        Returns:
            str: Formatted range string in the format 'Sheet!A1:Z100'.
        """
        return f"{self.sheet}!{self.range[0]}:{self.range[1]}"

    def _token_exists(self) -> bool:
        """Check if a saved token file exists in the persistent storage directory.

        Returns:
            bool: True if the token file exists in ~/.monzo-py/, False otherwise.
        """
        exists = self._token_path.exists()
        logger.debug(f"Checking token file existence: {exists} at {self._token_path}")
        return exists

    def _add_credentials_from_token(self) -> None:
        """Load credentials from an existing persistent token file.

        Attempts to load previously saved OAuth2 credentials from the token file
        stored in ~/.monzo-py/monzo_token.json.

        Raises:
            ValueError: If the token file does not exist.
        """
        logger.info("Attempting to load credentials from token file")
        if not self._token_exists():
            token_path = self._token_path.absolute()
            logger.error(f"Token file does not exist at {token_path}")
            raise ValueError(f"Token file does not exist at {token_path}")
        logger.info(f"Loading credentials from: {self._token_path}")
        self._credentials = Credentials.from_authorized_user_file(self._token_path)
        logger.info("Successfully loaded credentials from token file")

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
        """Save the current credentials to persistent token file.

        Saves OAuth2 credentials to ~/.monzo-py/monzo_token.json for reuse
        across sessions, eliminating the need for repeated authentication.

        Raises:
            ValueError: If credentials are not set.
        """
        logger.info("Saving credentials to token file")
        if not self._credentials:
            logger.error("Cannot save credentials: credentials not set")
            raise ValueError("Credentials not set")
        logger.info(f"Writing token to: {self._token_path}")
        self._token_dir.mkdir(parents=True, exist_ok=True)
        with open(self._token_path, "w") as token_file:
            token_file.write(self._credentials.to_json())
        logger.info("Credentials saved successfully")

    def credentials(self):
        """Get valid credentials for Google Sheets API access.

        This method handles the complete credential flow:
        - Loads existing token if available
        - Refreshes stale tokens
        - Initiates OAuth flow if no valid token exists
        - Saves credentials for future use

        Returns:
            Credentials: Valid Google API credentials.

        Raises:
            ValueError: If credentials cannot be obtained.
        """

        if not self._credentials and self._token_exists():
            self._add_credentials_from_token()
            token_state = self._credentials.token_state if self._credentials else None
            if self._credentials and token_state and token_state == TokenState.STALE:
                logger.info("Refreshing stale token")
                self._refresh_token()
                self._save_credentials()
            if self._credentials and token_state and token_state == TokenState.INVALID:
                logger.info("Invalid token")
                self._add_credentials_from_secret()
                self._save_credentials()
        elif not self._credentials:
            self._add_credentials_from_secret()
            self._save_credentials()

        if self._credentials is None:
            raise ValueError("Credentials not set")

        return self._credentials

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
            "sheets", "v4", credentials=self.credentials(), cache_discovery=False
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

        # Get the data (this will fetch it if not already cached)
        data = self.data

        if not data:
            logger.error("No data available to create DuckDB database")
            raise ValueError("No data available to create DuckDB database")

        # Create in-memory DuckDB connection
        conn = duckdb.connect(":memory:")
        logger.debug("DuckDB connection created")

        # Get column definitions
        column_definitions = self._get_column_definitions()

        if len(data) <= 1:
            self._create_empty_table(conn, column_definitions)
            return conn

        # Skip header row, use remaining data
        table_data = data[1:]

        # Create PyArrow table with appropriate data types
        schema = pa.schema([(name, pa_type) for name, _, pa_type in column_definitions])

        # Convert data to appropriate types
        converted_columns = self._convert_data_columns(table_data, column_definitions)

        arrow_table = pa.table(converted_columns, schema=schema)

        # Register the PyArrow table directly with DuckDB
        # This is much more efficient than row-by-row insertion
        conn.register("transactions", arrow_table)

        logger.info(
            f"Created DuckDB table using PyArrow with {len(table_data)} rows and 16 columns"
        )

        # Log table info for debugging
        result = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()
        if result is not None:
            logger.info(
                f"Successfully created DuckDB database with {result[0]} data rows"
            )
        else:
            logger.warning("Could not retrieve row count from DuckDB database")

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
