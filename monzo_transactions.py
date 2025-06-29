"""Module defining the class to interact with Monzo transactions."""

import tempfile
from collections.abc import Sequence
from pathlib import Path

from google.auth.credentials import TokenState
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


class MonzoTransactions:
    """Class to interact with Monzo transactions."""

    def __init__(
        self,
        spreadsheet_id: str,
        sheet: str,
        range: tuple[str, str],
        *,
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
        self._token_path = Path(tempfile.gettempdir(), "monzo_token.json")

    @property
    def range_name(self) -> str:
        """Get the formatted range name for Google Sheets API.

        Returns:
            str: Formatted range string in the format 'Sheet!A1:Z100'.
        """
        return f"{self.sheet}!{self.range[0]}:{self.range[1]}"

    def _token_exists(self) -> bool:
        """Check if a saved token file exists.

        Returns:
            bool: True if the token file exists, False otherwise.
        """
        return self._token_path.exists()

    def _add_credentials_from_token(self) -> None:
        """Load credentials from an existing token file.

        Raises:
            ValueError: If the token file does not exist.
        """
        if not self._token_exists():
            token_path = self._token_path.absolute()
            raise ValueError(f"Token file does not exist at {token_path}")
        self._credentials = Credentials.from_authorized_user_file(self._token_path)

    def _refresh_token(self) -> None:
        """Refresh the existing credentials token.

        Raises:
            ValueError: If credentials are not set.
        """
        if self._credentials:
            self._credentials.refresh(Request())
        else:
            raise ValueError("Credentials not set")

    def _add_credentials_from_secret(self) -> None:
        """Create credentials from the client secrets file using OAuth flow.

        This method will open a browser window for user authentication.
        """
        flow = InstalledAppFlow.from_client_secrets_file(
            self._credentials_path, self._spreadsheet_scopes
        )
        self._credentials = flow.run_local_server(port=0)

    def _save_credentials(self) -> None:
        """Save the current credentials to a token file.

        Raises:
            ValueError: If credentials are not set.
        """
        if not self._credentials:
            raise ValueError("Credentials not set")
        with open(self._token_path, "w") as token_file:
            token_file.write(self._credentials.to_json())

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
            if self._credentials and self._credentials.token_state == TokenState.STALE:
                self._refresh_token()
            else:
                self._add_credentials_from_secret()
        else:
            self._add_credentials_from_secret()
        if self._credentials is None:
            raise ValueError("Credentials not set")
        self._save_credentials()
        return self._credentials
