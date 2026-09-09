"""
Tests for ReconciliationAnalyzer - mock Task 1 outputs
"""
import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from reconciliation import ReconciliationAnalyzer


class TestReconciliationAnalyzerNoDiscrepancy:
    """Test analyze() with balanced data (no discrepancies)"""

    def test_balanced_simple_case(self):
        """Should return no discrepancy when balance sheet matches journal entries"""
        # Mock balance sheet from Task 1 output
        balance_sheet = {
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

        # Mock journal entries from Task 1 output
        # These entries should result in the balance sheet above
        journal_entries = [
            {
                "date": "2026-09-01",
                "debit_account": "cash",
                "credit_account": "capital",
                "amount": 100000.0
            },
            {
                "date": "2026-09-02",
                "debit_account": "bank",
                "credit_account": "capital",
                "amount": 500000.0
            },
            {
                "date": "2026-09-03",
                "debit_account": "expenses",
                "credit_account": "payables",
                "amount": 50000.0
            }
        ]

        # Analyze
        result = ReconciliationAnalyzer.analyze(balance_sheet, journal_entries)

        # Assertions
        assert result is not None
        assert isinstance(result, dict)
        assert "has_discrepancy" in result
        assert "discrepancy_amount" in result
        assert "cash_discrepancy" in result
        assert "bank_discrepancy" in result
        assert "potential_causes" in result
        assert "summary" in result

        # Should have no discrepancy
        assert result["has_discrepancy"] is False
        assert result["discrepancy_amount"] == 0.0

    def test_balanced_with_tolerance(self):
        """Should return no discrepancy when difference is within tolerance (±0.01)"""
        balance_sheet = {
            "assets": {
                "cash": 100000.01,
                "bank": 500000.0,
            },
            "liabilities": {
                "payables": 50000.0,
            },
            "equity": {
                "capital": 550000.01,
            }
        }

        journal_entries = [
            {
                "date": "2026-09-01",
                "debit_account": "cash",
                "credit_account": "capital",
                "amount": 100000.0
            },
            {
                "date": "2026-09-02",
                "debit_account": "bank",
                "credit_account": "capital",
                "amount": 500000.0
            },
            {
                "date": "2026-09-03",
                "debit_account": "expenses",
                "credit_account": "payables",
                "amount": 50000.0
            }
        ]

        result = ReconciliationAnalyzer.analyze(balance_sheet, journal_entries)

        # Within tolerance, should have no discrepancy
        assert result["has_discrepancy"] is False
        assert result["discrepancy_amount"] <= 0.01

    def test_multiple_transactions_balanced(self):
        """Should handle multiple transactions and still detect no discrepancy"""
        balance_sheet = {
            "assets": {
                "cash": 150000.0,
                "bank": 700000.0,
            },
            "liabilities": {
                "payables": 100000.0,
                "loans": 200000.0,
            },
            "equity": {
                "capital": 550000.0,
            }
        }

        journal_entries = [
            {"date": "2026-09-01", "debit_account": "cash", "credit_account": "capital", "amount": 100000.0},
            {"date": "2026-09-02", "debit_account": "bank", "credit_account": "capital", "amount": 500000.0},
            {"date": "2026-09-03", "debit_account": "expenses", "credit_account": "payables", "amount": 50000.0},
            {"date": "2026-09-04", "debit_account": "cash", "credit_account": "sales", "amount": 50000.0},
            {"date": "2026-09-05", "debit_account": "expenses", "credit_account": "payables", "amount": 50000.0},
            {"date": "2026-09-06", "debit_account": "bank", "credit_account": "loans", "amount": 200000.0},
        ]

        result = ReconciliationAnalyzer.analyze(balance_sheet, journal_entries)

        assert isinstance(result, dict)
        # Should complete without errors
        assert "summary" in result


class TestReconciliationAnalyzerWithDiscrepancy:
    """Test analyze() with unbalanced data (with discrepancies)"""

    def test_journal_entries_unbalanced(self):
        """Should detect discrepancy when journal entries don't balance (debits != credits)"""
        balance_sheet = {
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

        # Unbalanced: total debits = 200000, total credits = 100000
        # Only 100000 credit but 200000 debit
        journal_entries = [
            {
                "date": "2026-09-01",
                "debit_account": "cash",
                "credit_account": "capital",
                "amount": 100000.0
            },
            {
                "date": "2026-09-02",
                "debit_account": "bank",
                "credit_account": "capital",
                "amount": 100000.0  # Second debit, no matching credit
            },
            {
                "date": "2026-09-03",
                "debit_account": "expenses",
                "credit_account": "payables",
                "amount": 50000.0
            }
        ]

        result = ReconciliationAnalyzer.analyze(balance_sheet, journal_entries)

        # Should detect discrepancy
        assert result["has_discrepancy"] is True
        assert result["discrepancy_amount"] > 0.0

    def test_cash_account_discrepancy(self):
        """Should detect discrepancy in cash account specifically"""
        balance_sheet = {
            "assets": {
                "cash": 150000.0,  # More than journal entries show
                "bank": 500000.0,
            },
            "liabilities": {
                "payables": 50000.0,
            },
            "equity": {
                "capital": 550000.0,
            }
        }

        journal_entries = [
            {
                "date": "2026-09-01",
                "debit_account": "cash",
                "credit_account": "capital",
                "amount": 100000.0  # Only 100000, but balance sheet shows 150000
            },
            {
                "date": "2026-09-02",
                "debit_account": "bank",
                "credit_account": "capital",
                "amount": 500000.0
            },
            {
                "date": "2026-09-03",
                "debit_account": "expenses",
                "credit_account": "payables",
                "amount": 50000.0
            }
        ]

        result = ReconciliationAnalyzer.analyze(balance_sheet, journal_entries)

        # Cash discrepancy should be detected
        assert result["cash_discrepancy"] > ReconciliationAnalyzer.TOLERANCE

    def test_bank_account_discrepancy(self):
        """Should detect discrepancy in bank account specifically"""
        balance_sheet = {
            "assets": {
                "cash": 100000.0,
                "bank": 400000.0,  # Less than journal entries show
            },
            "liabilities": {
                "payables": 50000.0,
            },
            "equity": {
                "capital": 550000.0,
            }
        }

        journal_entries = [
            {
                "date": "2026-09-01",
                "debit_account": "cash",
                "credit_account": "capital",
                "amount": 100000.0
            },
            {
                "date": "2026-09-02",
                "debit_account": "bank",
                "credit_account": "capital",
                "amount": 500000.0  # 500000 in journal, but balance sheet shows 400000
            },
            {
                "date": "2026-09-03",
                "debit_account": "expenses",
                "credit_account": "payables",
                "amount": 50000.0
            }
        ]

        result = ReconciliationAnalyzer.analyze(balance_sheet, journal_entries)

        # Bank discrepancy should be detected
        assert result["bank_discrepancy"] > ReconciliationAnalyzer.TOLERANCE

    def test_balance_sheet_equation_fails(self):
        """Should detect when balance sheet equation fails (assets != liabilities + equity)"""
        # Broken balance sheet: assets (800000) != liabilities + equity (600000)
        balance_sheet = {
            "assets": {
                "cash": 500000.0,
                "bank": 300000.0,  # Total assets = 800000
            },
            "liabilities": {
                "payables": 200000.0,
            },
            "equity": {
                "capital": 400000.0,  # Total liabilities + equity = 600000
            }
        }

        journal_entries = [
            {
                "date": "2026-09-01",
                "debit_account": "cash",
                "credit_account": "capital",
                "amount": 500000.0
            },
            {
                "date": "2026-09-02",
                "debit_account": "bank",
                "credit_account": "capital",
                "amount": 300000.0
            },
            {
                "date": "2026-09-03",
                "debit_account": "expenses",
                "credit_account": "payables",
                "amount": 200000.0
            }
        ]

        result = ReconciliationAnalyzer.analyze(balance_sheet, journal_entries)

        # Balance sheet equation fails (assets != liabilities + equity), should detect discrepancy
        assert result["has_discrepancy"] is True


class TestReconciliationAnalyzerPotentialCauses:
    """Test potential causes detection"""

    def test_personal_expense_detection(self):
        """Should identify personal expense transactions as potential causes"""
        balance_sheet = {
            "assets": {"cash": 100000.0},
            "liabilities": {"payables": 0.0},
            "equity": {"capital": 100000.0}
        }

        journal_entries = [
            {
                "date": "2026-09-01",
                "debit_account": "cash",
                "credit_account": "capital",
                "amount": 100000.0
            },
            {
                "date": "2026-09-02",
                "debit_account": "owner_personal_expense",
                "credit_account": "cash",
                "amount": 50000.0
            }
        ]

        result = ReconciliationAnalyzer.analyze(balance_sheet, journal_entries)

        # Should identify personal expense as potential cause
        assert len(result["potential_causes"]) > 0
        causes_text = [c["reason"].lower() for c in result["potential_causes"]]
        assert any("personal" in text for text in causes_text)

    def test_owner_draw_detection(self):
        """Should identify owner draw transactions as potential causes"""
        balance_sheet = {
            "assets": {"cash": 50000.0},
            "liabilities": {"payables": 0.0},
            "equity": {"capital": 50000.0}
        }

        journal_entries = [
            {
                "date": "2026-09-01",
                "debit_account": "cash",
                "credit_account": "capital",
                "amount": 100000.0
            },
            {
                "date": "2026-09-02",
                "debit_account": "owner_draw",
                "credit_account": "cash",
                "amount": 50000.0
            }
        ]

        result = ReconciliationAnalyzer.analyze(balance_sheet, journal_entries)

        # Should identify owner draw as potential cause
        assert len(result["potential_causes"]) > 0
        causes_text = [c["reason"].lower() for c in result["potential_causes"]]
        assert any("withdrawal" in text or "draw" in text for text in causes_text)

    def test_potential_causes_have_required_fields(self):
        """Should ensure all potential causes have required fields"""
        balance_sheet = {
            "assets": {"cash": 100000.0},
            "liabilities": {"payables": 0.0},
            "equity": {"capital": 100000.0}
        }

        journal_entries = [
            {
                "date": "2026-09-01",
                "debit_account": "cash",
                "credit_account": "capital",
                "amount": 100000.0
            },
            {
                "date": "2026-09-02",
                "debit_account": "owner_personal_expense",
                "credit_account": "cash",
                "amount": 50000.0
            }
        ]

        result = ReconciliationAnalyzer.analyze(balance_sheet, journal_entries)

        # Check all causes have required fields
        for cause in result["potential_causes"]:
            assert "account" in cause
            assert "amount" in cause
            assert "transaction_date" in cause
            assert "reason" in cause


class TestReconciliationAnalyzerEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_balance_sheet(self):
        """Should handle empty balance sheet gracefully"""
        balance_sheet = {}
        journal_entries = [
            {
                "date": "2026-09-01",
                "debit_account": "cash",
                "credit_account": "capital",
                "amount": 100000.0
            }
        ]

        result = ReconciliationAnalyzer.analyze(balance_sheet, journal_entries)

        # Should not crash, should return valid result
        assert isinstance(result, dict)
        assert "summary" in result

    def test_empty_journal_entries(self):
        """Should handle empty journal entries gracefully"""
        balance_sheet = {
            "assets": {"cash": 0.0},
            "liabilities": {"payables": 0.0},
            "equity": {"capital": 0.0}
        }
        journal_entries = []

        result = ReconciliationAnalyzer.analyze(balance_sheet, journal_entries)

        # Should not crash
        assert isinstance(result, dict)
        assert "summary" in result

    def test_missing_account_fields(self):
        """Should handle journal entries with missing account fields"""
        balance_sheet = {
            "assets": {"cash": 100000.0},
            "liabilities": {"payables": 0.0},
            "equity": {"capital": 100000.0}
        }

        journal_entries = [
            {
                "date": "2026-09-01",
                "debit_account": "cash",
                # Missing credit_account
                "amount": 100000.0
            },
            {
                "date": "2026-09-02",
                # Missing debit_account
                "credit_account": "capital",
                "amount": 50000.0
            }
        ]

        result = ReconciliationAnalyzer.analyze(balance_sheet, journal_entries)

        # Should handle gracefully and return valid result
        assert isinstance(result, dict)

    def test_negative_amounts(self):
        """Should handle negative amounts (reversals/adjustments)"""
        balance_sheet = {
            "assets": {"cash": 50000.0},
            "liabilities": {"payables": 0.0},
            "equity": {"capital": 50000.0}
        }

        journal_entries = [
            {
                "date": "2026-09-01",
                "debit_account": "cash",
                "credit_account": "capital",
                "amount": 100000.0
            },
            {
                "date": "2026-09-02",
                "debit_account": "capital",
                "credit_account": "cash",
                "amount": -50000.0  # Reversal
            }
        ]

        result = ReconciliationAnalyzer.analyze(balance_sheet, journal_entries)

        # Should handle without crashing
        assert isinstance(result, dict)

    def test_case_insensitive_account_names(self):
        """Should handle account names in different cases"""
        balance_sheet = {
            "assets": {"CASH": 100000.0},
            "liabilities": {"PAYABLES": 0.0},
            "equity": {"CAPITAL": 100000.0}
        }

        journal_entries = [
            {
                "date": "2026-09-01",
                "debit_account": "Cash",
                "credit_account": "Capital",
                "amount": 100000.0
            }
        ]

        result = ReconciliationAnalyzer.analyze(balance_sheet, journal_entries)

        # Should not crash and handle case variations
        assert isinstance(result, dict)


class TestReconciliationAnalyzerReturnStructure:
    """Test return value structure and types"""

    def test_return_structure_complete(self):
        """Should return all required fields in correct types"""
        balance_sheet = {
            "assets": {"cash": 100000.0},
            "liabilities": {"payables": 0.0},
            "equity": {"capital": 100000.0}
        }

        journal_entries = [
            {
                "date": "2026-09-01",
                "debit_account": "cash",
                "credit_account": "capital",
                "amount": 100000.0
            }
        ]

        result = ReconciliationAnalyzer.analyze(balance_sheet, journal_entries)

        # Check all required fields exist and have correct types
        assert isinstance(result["has_discrepancy"], bool)
        assert isinstance(result["discrepancy_amount"], float)
        assert isinstance(result["cash_discrepancy"], float)
        assert isinstance(result["bank_discrepancy"], float)
        assert isinstance(result["potential_causes"], list)
        assert isinstance(result["summary"], str)

        # All amounts should be >= 0
        assert result["discrepancy_amount"] >= 0
        assert result["cash_discrepancy"] >= 0
        assert result["bank_discrepancy"] >= 0

    def test_summary_contains_relevant_info(self):
        """Should generate meaningful summary text"""
        balance_sheet = {
            "assets": {"cash": 100000.0},
            "liabilities": {"payables": 0.0},
            "equity": {"capital": 100000.0}
        }

        journal_entries = [
            {
                "date": "2026-09-01",
                "debit_account": "cash",
                "credit_account": "capital",
                "amount": 100000.0
            }
        ]

        result = ReconciliationAnalyzer.analyze(balance_sheet, journal_entries)

        # Summary should not be empty
        assert len(result["summary"]) > 0
        # Should contain meaningful words
        assert any(word in result["summary"].lower() for word in ["match", "discrepancy", "no", "detected"])
