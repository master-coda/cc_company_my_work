"""
ReconciliationAnalyzer - Analyze discrepancies between balance sheet and journal entries
"""
import logging
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Account classification constants
BUSINESS_ACCOUNTS = {"sales", "expenses", "cost_of_goods_sold"}
PERSONAL_ACCOUNTS = {"owner_draw", "owner_personal_expense"}
CASH_ACCOUNTS = {"cash", "bank"}


class ReconciliationAnalyzer:
    """
    Analyzes discrepancies between balance sheet and journal entries.
    Detects mismatches and identifies potential root causes.
    """

    TOLERANCE = 0.01  # Rounding tolerance in JPY

    def __init__(self):
        """Initialize ReconciliationAnalyzer"""
        logger.info("ReconciliationAnalyzer initialized")

    @staticmethod
    def analyze(balance_sheet: Dict[str, Any], journal_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze discrepancies between balance sheet and journal entries.

        Args:
            balance_sheet: Dict with structure {"assets": {...}, "liabilities": {...}, "equity": {...}}
            journal_entries: List of journal entry dicts with structure:
                [{"date": str, "debit_account": str, "credit_account": str, "amount": float}, ...]

        Returns:
            Dict with structure:
            {
                "has_discrepancy": bool,
                "discrepancy_amount": float,
                "cash_discrepancy": float,
                "bank_discrepancy": float,
                "potential_causes": [
                    {"account": str, "amount": float, "transaction_date": str, "reason": str},
                    ...
                ],
                "summary": str
            }
        """
        try:
            logger.info(f"Analyzing {len(journal_entries)} journal entries against balance sheet")

            # Initialize result dict
            result = {
                "has_discrepancy": False,
                "discrepancy_amount": 0.0,
                "cash_discrepancy": 0.0,
                "bank_discrepancy": 0.0,
                "potential_causes": [],
                "summary": ""
            }

            # Handle empty inputs
            if not balance_sheet or not journal_entries:
                result["summary"] = "Insufficient data for analysis"
                logger.warning("Empty balance_sheet or journal_entries")
                return result

            # Calculate totals from journal entries
            debits_by_account = {}
            credits_by_account = {}
            total_debits = 0.0
            total_credits = 0.0

            for entry in journal_entries:
                amount = entry.get("amount", 0.0)
                debit_account = entry.get("debit_account", "").lower()
                credit_account = entry.get("credit_account", "").lower()

                if debit_account:
                    debits_by_account[debit_account] = debits_by_account.get(debit_account, 0.0) + amount
                    total_debits += amount

                if credit_account:
                    credits_by_account[credit_account] = credits_by_account.get(credit_account, 0.0) + amount
                    total_credits += amount

            # Check journal equation: total debits should equal total credits
            journal_difference = abs(total_debits - total_credits)
            if journal_difference > ReconciliationAnalyzer.TOLERANCE:
                result["has_discrepancy"] = True
                result["discrepancy_amount"] = journal_difference

            # Calculate balance sheet totals
            assets_total = sum(balance_sheet.get("assets", {}).values())
            liabilities_total = sum(balance_sheet.get("liabilities", {}).values())
            equity_total = sum(balance_sheet.get("equity", {}).values())

            # Check balance sheet equation: assets should equal liabilities + equity
            bs_difference = abs(assets_total - (liabilities_total + equity_total))
            if bs_difference > ReconciliationAnalyzer.TOLERANCE and not result["has_discrepancy"]:
                result["has_discrepancy"] = True
                result["discrepancy_amount"] = bs_difference

            # Analyze cash and bank account discrepancies
            cash_balance = balance_sheet.get("assets", {}).get("cash", 0.0)
            bank_balance = balance_sheet.get("assets", {}).get("bank", 0.0)

            cash_journal_total = debits_by_account.get("cash", 0.0) - credits_by_account.get("cash", 0.0)
            bank_journal_total = debits_by_account.get("bank", 0.0) - credits_by_account.get("bank", 0.0)

            result["cash_discrepancy"] = abs(cash_balance - cash_journal_total)
            result["bank_discrepancy"] = abs(bank_balance - bank_journal_total)

            # Identify potential causes
            potential_causes = ReconciliationAnalyzer._identify_potential_causes(
                journal_entries,
                debits_by_account,
                credits_by_account,
                balance_sheet
            )
            result["potential_causes"] = potential_causes

            # Generate summary
            if result["has_discrepancy"]:
                result["summary"] = f"Discrepancy detected: {result['discrepancy_amount']:.2f} JPY. " \
                                   f"Cash diff: {result['cash_discrepancy']:.2f}, " \
                                   f"Bank diff: {result['bank_discrepancy']:.2f}. " \
                                   f"{len(potential_causes)} potential cause(s) identified."
            else:
                result["summary"] = "No discrepancies detected. Balance sheet and journal entries match."

            logger.info(result["summary"])
            return result

        except Exception as e:
            logger.error(f"Error analyzing reconciliation: {str(e)}")
            return {
                "has_discrepancy": False,
                "discrepancy_amount": 0.0,
                "cash_discrepancy": 0.0,
                "bank_discrepancy": 0.0,
                "potential_causes": [],
                "summary": f"Analysis error: {str(e)}"
            }

    @staticmethod
    def _identify_potential_causes(
        journal_entries: List[Dict[str, Any]],
        debits_by_account: Dict[str, float],
        credits_by_account: Dict[str, float],
        balance_sheet: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Identify potential causes of discrepancies.

        Checks for:
        - Unreconciled personal expenses
        - Owner withdrawals not in balance sheet
        - Suspicious account patterns
        """
        causes = []

        # Check for personal account transactions
        for entry in journal_entries:
            debit_account = entry.get("debit_account", "").lower()
            credit_account = entry.get("credit_account", "").lower()
            amount = entry.get("amount", 0.0)
            date = entry.get("date", "")

            # Flag personal account activity
            if "personal_expense" in debit_account or "personal_expense" in credit_account:
                causes.append({
                    "account": debit_account if "personal_expense" in debit_account else credit_account,
                    "amount": amount,
                    "transaction_date": date,
                    "reason": "Personal expense transaction detected - may not be reflected in balance sheet"
                })

            # Flag owner draw transactions
            if "owner_draw" in debit_account or "owner_draw" in credit_account:
                causes.append({
                    "account": debit_account if "owner_draw" in debit_account else credit_account,
                    "amount": amount,
                    "transaction_date": date,
                    "reason": "Owner withdrawal detected - verify against balance sheet equity"
                })

        # Check for unbalanced account pairs that might indicate errors
        for account in debits_by_account:
            if account in credits_by_account:
                difference = abs(debits_by_account[account] - credits_by_account[account])
                if difference > ReconciliationAnalyzer.TOLERANCE:
                    # This account has both debits and credits with a net difference
                    # This could indicate entry errors
                    causes.append({
                        "account": account,
                        "amount": difference,
                        "transaction_date": "multiple",
                        "reason": f"Account has both debits ({debits_by_account[account]:.2f}) "
                                 f"and credits ({credits_by_account[account]:.2f})"
                    })

        return causes
