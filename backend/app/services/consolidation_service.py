from app.models.consolidation import ConsolidationReportingPackage
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
