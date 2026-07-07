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


def calculate_unrealized_inventory_profit(
    ending_internal_inventory_amount: Decimal,
    internal_gross_margin_rate: Decimal,
) -> Decimal:
    return (ending_internal_inventory_amount * internal_gross_margin_rate).quantize(Decimal("0.01"))


def build_intercompany_revenue_cost_elimination(
    group_id: str,
    period: str,
    revenue_amount: Decimal,
    cost_amount: Decimal,
) -> list[ConsolidationEliminationEntry]:
    elimination_amount = min(revenue_amount, cost_amount).quantize(Decimal("0.01"))
    return [
        ConsolidationEliminationEntry(
            elimination_id=f"elim-{group_id}-{period}-revenue-cost",
            group_id=group_id,
            period=period,
            elimination_type="intercompany_revenue_cost",
            debit_account_code="6001",
            credit_account_code="6401",
            amount=elimination_amount,
            explanation="抵销内部销售收入与成本",
        )
    ]


def calculate_minority_interest(
    subsidiary_net_assets: Decimal,
    ownership_percentage: Decimal,
) -> Decimal:
    minority_percentage = Decimal("1") - ownership_percentage
    return (subsidiary_net_assets * minority_percentage).quantize(Decimal("0.01"))


def build_investment_equity_elimination(
    group_id: str,
    period: str,
    investment_account_code: str,
    subsidiary_equity_account_code: str,
    investment_amount: Decimal,
    subsidiary_equity_amount: Decimal,
    ownership_percentage: Decimal,
) -> list[ConsolidationEliminationEntry]:
    attributable_equity = (subsidiary_equity_amount * ownership_percentage).quantize(Decimal("0.01"))
    elimination_amount = min(investment_amount, attributable_equity).quantize(Decimal("0.01"))
    return [
        ConsolidationEliminationEntry(
            elimination_id=f"elim-{group_id}-{period}-investment-equity",
            group_id=group_id,
            period=period,
            elimination_type="investment_equity",
            debit_account_code=subsidiary_equity_account_code,
            credit_account_code=investment_account_code,
            amount=elimination_amount,
            explanation="抵销母公司长期股权投资与子公司权益",
        )
    ]
