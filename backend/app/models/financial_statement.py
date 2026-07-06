from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.finance import MONTH_PATTERN


class FinancialStatementGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: str = Field(pattern=MONTH_PATTERN)
    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    operator: str = Field(default="财务主管", min_length=1, max_length=32)


class StatementLineItem(BaseModel):
    code: str
    name: str
    amount: Decimal
    formula: str


class BalanceSheet(BaseModel):
    title: str
    period: str
    items: list[StatementLineItem]
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    total_liabilities_and_equity: Decimal
    balanced: bool


class IncomeStatement(BaseModel):
    title: str
    period: str
    items: list[StatementLineItem]
    total_revenue: Decimal
    total_cost: Decimal
    total_expense: Decimal
    total_profit: Decimal
    net_profit: Decimal


class CashFlowStatement(BaseModel):
    title: str
    period: str
    items: list[StatementLineItem]
    operating_cash_flow_net: Decimal
    investing_cash_flow_net: Decimal
    financing_cash_flow_net: Decimal
    net_cash_flow: Decimal


class EquityStatement(BaseModel):
    title: str
    period: str
    items: list[StatementLineItem]
    opening_equity: Decimal
    current_period_profit: Decimal
    closing_equity: Decimal


class ManagementStatementSummary(BaseModel):
    title: str
    key_metrics: dict[str, str]
    highlights: list[str]
    risks: list[str]


class FinancialStatementGenerationSummary(BaseModel):
    account_set_id: str
    period: str
    source: str
    reviewed_voucher_count: int
    asset_liability_balanced: bool
    generated_statement_count: int
    base_currency: str = "CNY"
    foreign_currency_line_count: int = 0


class FinancialStatementBundle(BaseModel):
    account_set_id: str
    period: str
    company_name: str
    source: str
    summary: FinancialStatementGenerationSummary
    balance_sheet: BalanceSheet
    income_statement: IncomeStatement
    cash_flow_statement: CashFlowStatement
    equity_statement: EquityStatement
    management_summary: ManagementStatementSummary
