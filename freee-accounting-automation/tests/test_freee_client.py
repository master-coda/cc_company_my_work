"""
Tests for FreeeClient - mock all freee MCP calls
"""
import pytest
from unittest import mock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from freee_client import FreeeClient


class TestGetBalanceSheet:
    """Test get_balance_sheet method"""

    @mock.patch.dict(os.environ, {"FREEE_API_KEY": "test_key_123"})
    @mock.patch('freee_client.freee_api_get')
    def test_get_balance_sheet_success(self, mock_api_get):
        """Should return balance sheet dict on success"""
        # Mock freee API response
        mock_api_response = {
            "trial_balance": {
                "assets": {
                    "cash": 100000.0,
                    "bank": 500000.0,
                },
                "liabilities": {
                    "payables": 50000.0,
                },
                "equity": {
                    "capital": 550000.0,
                }
            }
        }
        mock_api_get.return_value = mock_api_response

        # Test
        client = FreeeClient()
        result = client.get_balance_sheet(2026, 9)

        # Assertions
        assert result is not None
        assert "assets" in result
        assert "liabilities" in result
        assert "equity" in result
        assert result["assets"]["cash"] == 100000.0
        assert result["liabilities"]["payables"] == 50000.0

        # Verify API was called with correct endpoint
        mock_api_get.assert_called_once()
        call_args = mock_api_get.call_args[0][0]
        assert "trial_balance" in call_args or "balance" in call_args.lower()

    @mock.patch.dict(os.environ, {"FREEE_API_KEY": "test_key_123"})
    @mock.patch('freee_client.freee_api_get')
    def test_get_balance_sheet_api_error(self, mock_api_get):
        """Should return empty dict on API error"""
        mock_api_get.side_effect = Exception("API Error")

        client = FreeeClient()
        result = client.get_balance_sheet(2026, 9)

        assert result == {}

    @mock.patch.dict(os.environ, {"FREEE_API_KEY": "test_key_123"})
    @mock.patch('freee_client.freee_api_get')
    def test_get_balance_sheet_invalid_year_month(self, mock_api_get):
        """Should handle invalid year/month"""
        mock_api_get.return_value = {"trial_balance": {}}

        client = FreeeClient()
        result = client.get_balance_sheet(0, 0)

        # Should still call API, but log might indicate issue
        mock_api_get.assert_called_once()


class TestGetJournalEntries:
    """Test get_journal_entries method"""

    @mock.patch.dict(os.environ, {"FREEE_API_KEY": "test_key_123"})
    @mock.patch('freee_client.freee_api_get')
    def test_get_journal_entries_success(self, mock_api_get):
        """Should return list of journal entries on success"""
        mock_api_response = {
            "journal_entries": [
                {
                    "date": "2026-09-01",
                    "debit_account": "110",
                    "credit_account": "300",
                    "amount": 100000.0
                },
                {
                    "date": "2026-09-02",
                    "debit_account": "200",
                    "credit_account": "110",
                    "amount": 50000.0
                }
            ]
        }
        mock_api_get.return_value = mock_api_response

        client = FreeeClient()
        result = client.get_journal_entries(2026, 9)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["date"] == "2026-09-01"
        assert result[0]["amount"] == 100000.0
        assert result[1]["debit_account"] == "200"

        # Verify API was called
        mock_api_get.assert_called_once()

    @mock.patch.dict(os.environ, {"FREEE_API_KEY": "test_key_123"})
    @mock.patch('freee_client.freee_api_get')
    def test_get_journal_entries_empty_period(self, mock_api_get):
        """Should return empty list if no entries in period"""
        mock_api_response = {"journal_entries": []}
        mock_api_get.return_value = mock_api_response

        client = FreeeClient()
        result = client.get_journal_entries(2026, 1)

        assert result == []

    @mock.patch.dict(os.environ, {"FREEE_API_KEY": "test_key_123"})
    @mock.patch('freee_client.freee_api_get')
    def test_get_journal_entries_api_error(self, mock_api_get):
        """Should return empty list on API error"""
        mock_api_get.side_effect = Exception("Connection Error")

        client = FreeeClient()
        result = client.get_journal_entries(2026, 9)

        assert result == []


class TestSyncBankData:
    """Test sync_bank_data method"""

    @mock.patch.dict(os.environ, {"FREEE_API_KEY": "test_key_123"})
    @mock.patch('freee_client.freee_api_post')
    def test_sync_bank_data_success(self, mock_api_post):
        """Should return True on successful sync"""
        mock_api_response = {
            "result": "success",
            "synced_accounts": [
                {"bank_name": "楽天銀行", "status": "synced"},
                {"bank_name": "もみじ銀行", "status": "synced"}
            ]
        }
        mock_api_post.return_value = mock_api_response

        client = FreeeClient()
        result = client.sync_bank_data()

        assert result is True
        mock_api_post.assert_called_once()

    @mock.patch.dict(os.environ, {"FREEE_API_KEY": "test_key_123"})
    @mock.patch('freee_client.freee_api_post')
    def test_sync_bank_data_failure(self, mock_api_post):
        """Should return False on sync failure"""
        mock_api_post.side_effect = Exception("Sync failed")

        client = FreeeClient()
        result = client.sync_bank_data()

        assert result is False

    @mock.patch.dict(os.environ, {"FREEE_API_KEY": "test_key_123"})
    @mock.patch('freee_client.freee_api_post')
    def test_sync_bank_data_partial_failure(self, mock_api_post):
        """Should handle partial sync failure"""
        mock_api_response = {
            "result": "partial",
            "synced_accounts": [
                {"bank_name": "楽天銀行", "status": "synced"},
                {"bank_name": "もみじ銀行", "status": "failed"}
            ]
        }
        mock_api_post.return_value = mock_api_response

        client = FreeeClient()
        result = client.sync_bank_data()

        # Partial success should still return True
        assert result is True


class TestFreeeClientInit:
    """Test FreeeClient initialization"""

    @mock.patch.dict(os.environ, {"FREEE_API_KEY": "test_key_123"})
    def test_init_with_api_key(self):
        """Should initialize with API key from environment"""
        client = FreeeClient()
        assert client is not None
        # API key should be stored
        assert hasattr(client, 'api_key')

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_init_without_api_key(self):
        """Should initialize even without API key (no validation)"""
        # Per requirements, no need to validate API key existence
        client = FreeeClient()
        assert client is not None
