"""Tests for MonzoTransactions class."""

from unittest.mock import patch

import pytest
from google.auth.credentials import TokenState

from monzo_py import MonzoTransactions


class TestMonzoTransactions:
    """Test suite for MonzoTransactions class."""

    def test_init(self):
        """Test MonzoTransactions initialization."""
        monzo = MonzoTransactions(
            spreadsheet_id="test_id",
            sheet="Sheet1",
            range=("A1", "Z100"),
            credentials_path="test_credentials.json",
        )
        assert monzo.spreadsheet_id == "test_id"
        assert monzo.sheet == "Sheet1"
        assert monzo.range == ("A1", "Z100")
        assert monzo._credentials_path == "test_credentials.json"
        assert monzo._credentials is None

    def test_range_name_property(self, monzo_instance):
        """Test the range_name property returns correct format."""
        expected = "test_sheet!A1:Z100"
        assert monzo_instance.range_name == expected

    def test_keyring_credentials_configured(self, monzo_instance):
        """Test that keyring service and username are correctly configured."""
        assert monzo_instance._keyring_service == "monzo-py"
        assert monzo_instance._keyring_username == "google-oauth-token"

    @patch("keyring.get_password")
    def test_token_exists_true(self, mock_get_password, monzo_instance):
        """Test _token_exists returns True when token exists in keyring."""
        mock_get_password.return_value = '{"test": "token"}'
        assert monzo_instance._token_exists() is True
        mock_get_password.assert_called_once_with("monzo-py", "google-oauth-token")

    @patch("keyring.get_password")
    def test_token_exists_false(self, mock_get_password, monzo_instance):
        """Test _token_exists returns False when no token in keyring."""
        mock_get_password.return_value = None
        assert monzo_instance._token_exists() is False
        mock_get_password.assert_called_once_with("monzo-py", "google-oauth-token")

    def test_save_credentials_no_credentials(self, monzo_instance):
        """Test ValueError raised when trying to save without credentials."""
        with pytest.raises(ValueError, match="Credentials not set"):
            monzo_instance._save_credentials()

    @patch("keyring.set_password")
    def test_save_credentials_success(
        self, mock_set_password, monzo_instance, mock_credentials
    ):
        """Test successful credential saving to keyring."""
        monzo_instance._credentials = mock_credentials

        monzo_instance._save_credentials()

        mock_set_password.assert_called_once_with(
            "monzo-py", "google-oauth-token", '{"token": "test_token"}'
        )

    def test_refresh_token_no_credentials(self, monzo_instance):
        """Test ValueError raised when trying to refresh without credentials."""
        with pytest.raises(ValueError, match="Credentials not set"):
            monzo_instance._refresh_token()

    @patch("monzo_py.monzo_transactions.Request")
    def test_refresh_token_success(
        self, mock_request_class, monzo_instance, mock_credentials
    ):
        """Test successful token refresh."""
        monzo_instance._credentials = mock_credentials
        mock_request = mock_request_class.return_value

        monzo_instance._refresh_token()
        mock_credentials.refresh.assert_called_once_with(mock_request)

    @patch("monzo_py.monzo_transactions.InstalledAppFlow")
    def test_add_credentials_from_secret(
        self, mock_flow_class, monzo_instance, mock_credentials
    ):
        """Test credential creation from client secrets file."""
        mock_flow = mock_flow_class.from_client_secrets_file.return_value
        mock_flow.run_local_server.return_value = mock_credentials

        monzo_instance._add_credentials_from_secret()

        mock_flow_class.from_client_secrets_file.assert_called_once_with(
            monzo_instance._credentials_path, monzo_instance._spreadsheet_scopes
        )
        mock_flow.run_local_server.assert_called_once_with(port=0)
        assert monzo_instance._credentials == mock_credentials

    @patch("keyring.get_password")
    @patch("monzo_py.monzo_transactions.Credentials.from_authorized_user_info")
    def test_add_credentials_from_token_success(
        self, mock_from_info, mock_get_password, monzo_instance, mock_credentials
    ):
        """Test successful credential loading from keyring."""
        mock_get_password.return_value = '{"test": "token_data"}'
        mock_from_info.return_value = mock_credentials

        with patch.object(monzo_instance, "_token_exists", return_value=True):
            monzo_instance._add_credentials_from_token()
            assert monzo_instance._credentials == mock_credentials
            mock_get_password.assert_called_once_with("monzo-py", "google-oauth-token")
            mock_from_info.assert_called_once_with({"test": "token_data"})

    def test_add_credentials_from_token_no_token(self, monzo_instance):
        """Test ValueError raised when no token in keyring."""
        with (
            patch.object(monzo_instance, "_token_exists", return_value=False),
            pytest.raises(ValueError, match="No token found in system keyring"),
        ):
            monzo_instance._add_credentials_from_token()

    @patch("keyring.get_password")
    def test_add_credentials_from_token_invalid_json(
        self, mock_get_password, monzo_instance
    ):
        """Test ValueError raised when token contains invalid JSON."""
        mock_get_password.return_value = "invalid json"

        with (
            patch.object(monzo_instance, "_token_exists", return_value=True),
            pytest.raises(ValueError, match="Invalid token data in keyring"),
        ):
            monzo_instance._add_credentials_from_token()

    @patch.object(MonzoTransactions, "_save_credentials")
    @patch.object(MonzoTransactions, "_add_credentials_from_secret")
    @patch.object(MonzoTransactions, "_token_exists")
    def test_credentials_workflow_no_token(
        self,
        mock_token_exists,
        mock_add_secret,
        mock_save,
        monzo_instance,
        mock_credentials,
    ):
        """Test credentials workflow when no token in keyring."""
        mock_token_exists.return_value = False

        def set_credentials():
            monzo_instance._credentials = mock_credentials

        mock_add_secret.side_effect = set_credentials

        result = monzo_instance.credentials()

        mock_token_exists.assert_called_once()
        mock_add_secret.assert_called_once()
        mock_save.assert_called_once()
        assert result == mock_credentials

    @patch.object(MonzoTransactions, "_save_credentials")
    @patch.object(MonzoTransactions, "_refresh_token")
    @patch.object(MonzoTransactions, "_add_credentials_from_token")
    @patch.object(MonzoTransactions, "_token_exists")
    def test_credentials_workflow_stale_token(
        self,
        mock_token_exists,
        mock_add_token,
        mock_refresh,
        mock_save,
        monzo_instance,
        mock_credentials,
    ):
        """Test credentials workflow with stale token that needs refresh."""
        mock_token_exists.return_value = True
        mock_credentials.token_state = TokenState.STALE

        def set_credentials():
            monzo_instance._credentials = mock_credentials

        mock_add_token.side_effect = set_credentials

        result = monzo_instance.credentials()

        mock_token_exists.assert_called_once()
        mock_add_token.assert_called_once()
        mock_refresh.assert_called_once()
        mock_save.assert_called_once()
        assert result == mock_credentials

    @patch.object(MonzoTransactions, "_save_credentials")
    @patch.object(MonzoTransactions, "_add_credentials_from_secret")
    @patch.object(MonzoTransactions, "_token_exists")
    def test_credentials_workflow_invalid_token_fallback(
        self,
        mock_token_exists,
        mock_add_secret,
        mock_save,
        monzo_instance,
        mock_credentials,
    ):
        """Test credentials workflow falls back to OAuth when keyring token is invalid."""
        mock_token_exists.return_value = True

        def set_credentials():
            monzo_instance._credentials = mock_credentials

        # Mock _add_credentials_from_token to raise ValueError (invalid token)
        with patch.object(
            monzo_instance,
            "_add_credentials_from_token",
            side_effect=ValueError("Invalid token"),
        ):
            mock_add_secret.side_effect = set_credentials

            result = monzo_instance.credentials()

            mock_token_exists.assert_called_once()
            mock_add_secret.assert_called_once()
            mock_save.assert_called_once()
            assert result == mock_credentials

    def test_credentials_workflow_failure(self, monzo_instance):
        """Test credentials workflow raises ValueError when credentials can't be obtained."""
        with (
            patch.object(monzo_instance, "_token_exists", return_value=False),
            patch.object(monzo_instance, "_add_credentials_from_secret"),
            patch.object(monzo_instance, "_save_credentials"),
            pytest.raises(ValueError, match="Credentials not set"),
        ):
            # _credentials remains None since we don't set it in the mock
            monzo_instance.credentials()

    @patch("keyring.delete_password")
    def test_clear_credentials_success(
        self, mock_delete_password, monzo_instance, mock_credentials
    ):
        """Test successful credential clearing from keyring."""
        monzo_instance._credentials = mock_credentials

        monzo_instance.clear_credentials()

        mock_delete_password.assert_called_once_with("monzo-py", "google-oauth-token")
        assert monzo_instance._credentials is None

    @patch("keyring.delete_password")
    def test_clear_credentials_keyring_error(
        self, mock_delete_password, monzo_instance
    ):
        """Test credential clearing handles keyring errors gracefully."""
        mock_delete_password.side_effect = Exception("Keyring error")

        # Should not raise exception
        monzo_instance.clear_credentials()

        mock_delete_password.assert_called_once_with("monzo-py", "google-oauth-token")
        assert monzo_instance._credentials is None
