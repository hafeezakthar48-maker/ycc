from decimal import Decimal

from app.models.consolidation import ConsolidationEliminationEntry, ConsolidationReportingPackage
from app.models.financial_statement import FinancialStatementGenerateRequest
from app.services.financial_statement_service import generate_financial_statements


def build_reporting_package(account_set_id: str, period: str) -> ConsolidationReportingPackage:
    bundle = generate_financial_statements(
        FinancialStatementGenerateRequest(account_set_id=account_set_id, period=period, include_trace=True)
    )
    return ConsolidationReportingPackage(
        account_set_id=account_set_id,
        period=period,
        balance_sheet=bundle.balance_sheet,
        income_statement=bundle.income_statement,
        cash_flow_statement=bundle.cash_flow_statement,
    )


def build_intercompany_balance_elimination(
    group_id: str,
    period: str,
    receivable_account_code: str,
    payable_account_code: str,
    amount: Decimal,
) -> ConsolidationEliminationEntry:
    return ConsolidationEliminationEntry(
        elimination_id=f"elim-{group_id}-{period}-balance",
        group_id=group_id,
        period=period,
        elimination_type="intercompany_balance",
        debit_account_code=payable_account_code,
        credit_account_code=receivable_account_code,
        amount=amount.quantize(Decimal("0.01")),
        explanation="抵销内部应收应付",
    )
