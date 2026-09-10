"""
ReconciliationAnalyzer - Analyze discrepancies between balance sheet and journal entries
"""
import logging
from typing import Dict, List, Any, Optional, Set

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReconciliationAnalyzer:
    """
    Analyzes discrepancies between balance sheet and journal entries.
    Detects mismatches and identifies potential root causes.
    """

    TOLERANCE = 0.01  # Rounding tolerance in JPY

    @staticmethod
    def analyze(
        balance_sheet: Dict[str, Any],
        journal_entries: List[Dict[str, Any]],
        cash_accounts: Optional[Set[str]] = None,
        bank_accounts: Optional[Set[str]] = None,
        personal_expense_keywords: Optional[Set[str]] = None,
        owner_draw_keywords: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze discrepancies between balance sheet and journal entries.

        Args:
            balance_sheet: Dict with structure {"assets": {...}, "liabilities": {...}, "equity": {...}}
            journal_entries: List of journal entry dicts with structure:
                [{"date": str, "debit_account": str, "credit_account": str, "amount": float}, ...]
            cash_accounts: Asset account names (case-insensitive) treated as cash.
                Defaults to {"cash"}. Real data uses account-specific names
                (e.g. "現金"), so callers should pass the actual name(s).
            bank_accounts: Asset account names (case-insensitive) treated as bank.
                Defaults to {"bank"}. Real data uses bank/branch-specific names
                (e.g. "楽天 228 マンボ支店 普通 ***6057"), so callers should pass
                the actual name(s).
            personal_expense_keywords: Substrings matched (case-insensitive)
                against debit/credit account names to flag personal expenses.
                Defaults to {"personal_expense"}.
            owner_draw_keywords: Substrings matched (case-insensitive) against
                debit/credit account names to flag owner withdrawals.
                Defaults to {"owner_draw"}. For real freee sole-proprietor
                data, the equivalent account is usually "事業主貸".

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

            result = {
                "has_discrepancy": False,
                "discrepancy_amount": 0.0,
                "cash_discrepancy": 0.0,
                "bank_discrepancy": 0.0,
                "potential_causes": [],
                "summary": ""
            }

            if not balance_sheet or not journal_entries:
                result["summary"] = "Insufficient data for analysis"
                logger.warning("Empty balance_sheet or journal_entries")
                return result

            cash_account_names = {a.lower() for a in (cash_accounts or {"cash"})}
            bank_account_names = {a.lower() for a in (bank_accounts or {"bank"})}

            # Calculate totals from journal entries (account names normalized to lowercase)
            debits_by_account: Dict[str, float] = {}
            credits_by_account: Dict[str, float] = {}
            total_debits = 0.0
            total_credits = 0.0

            for entry in journal_entries:
                amount = entry.get("amount", 0.0)
                debit_account = (entry.get("debit_account") or "").lower()
                credit_account = (entry.get("credit_account") or "").lower()

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

            # Balance sheet accounts normalized to lowercase for case-insensitive lookup
            assets = {k.lower(): v for k, v in balance_sheet.get("assets", {}).items()}
            liabilities = {k.lower(): v for k, v in balance_sheet.get("liabilities", {}).items()}
            equity = {k.lower(): v for k, v in balance_sheet.get("equity", {}).items()}

            # Check balance sheet equation: assets should equal liabilities + equity
            assets_total = sum(assets.values())
            liabilities_total = sum(liabilities.values())
            equity_total = sum(equity.values())

            bs_difference = abs(assets_total - (liabilities_total + equity_total))
            if bs_difference > ReconciliationAnalyzer.TOLERANCE and not result["has_discrepancy"]:
                result["has_discrepancy"] = True
                result["discrepancy_amount"] = bs_difference

            # Analyze cash and bank account discrepancies (summed across all
            # accounts named in cash_account_names / bank_account_names)
            cash_balance = sum(v for k, v in assets.items() if k in cash_account_names)
            bank_balance = sum(v for k, v in assets.items() if k in bank_account_names)

            cash_journal_total = sum(
                debits_by_account.get(a, 0.0) - credits_by_account.get(a, 0.0) for a in cash_account_names
            )
            bank_journal_total = sum(
                debits_by_account.get(a, 0.0) - credits_by_account.get(a, 0.0) for a in bank_account_names
            )

            result["cash_discrepancy"] = abs(cash_balance - cash_journal_total)
            result["bank_discrepancy"] = abs(bank_balance - bank_journal_total)

            # Identify potential causes
            result["potential_causes"] = ReconciliationAnalyzer._identify_potential_causes(
                journal_entries,
                {k.lower() for k in (personal_expense_keywords or {"personal_expense"})},
                {k.lower() for k in (owner_draw_keywords or {"owner_draw"})}
            )

            # Generate summary
            if result["has_discrepancy"]:
                result["summary"] = (
                    f"Discrepancy detected: {result['discrepancy_amount']:.2f} JPY. "
                    f"Cash diff: {result['cash_discrepancy']:.2f}, "
                    f"Bank diff: {result['bank_discrepancy']:.2f}. "
                    f"{len(result['potential_causes'])} potential cause(s) identified."
                )
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
        personal_expense_keywords: Set[str],
        owner_draw_keywords: Set[str]
    ) -> List[Dict[str, Any]]:
        """
        Identify potential causes of discrepancies.

        Checks for:
        - Unreconciled personal expenses
        - Owner withdrawals not in balance sheet
        """
        causes = []

        for entry in journal_entries:
            debit_account = (entry.get("debit_account") or "").lower()
            credit_account = (entry.get("credit_account") or "").lower()
            amount = entry.get("amount", 0.0)
            date = entry.get("date", "")

            if any(kw in debit_account or kw in credit_account for kw in personal_expense_keywords):
                account = debit_account if any(kw in debit_account for kw in personal_expense_keywords) else credit_account
                causes.append({
                    "account": account,
                    "amount": amount,
                    "transaction_date": date,
                    "reason": "個人的な支出の可能性があります。経費ではなく「事業主貸」で仕訳してください"
                              "（貸借対照表に未反映の場合、差異の原因になります）"
                })

            if any(kw in debit_account or kw in credit_account for kw in owner_draw_keywords):
                account = debit_account if any(kw in debit_account for kw in owner_draw_keywords) else credit_account
                causes.append({
                    "account": account,
                    "amount": amount,
                    "transaction_date": date,
                    "reason": "事業主による引き出しの可能性があります。資本の払戻しとして「事業主貸」で仕訳し、"
                              "損益に影響させないでください（貸借対照表の資本に未反映の場合、差異の原因になります）"
                })

        return causes
