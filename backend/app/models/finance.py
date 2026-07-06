from pydantic import BaseModel, ConfigDict, Field


MONTH_PATTERN = r"^\d{4}-\d{2}$"


class MonthlyFinanceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: str = Field(pattern=MONTH_PATTERN)
    revenue: float
    cost: float
    sales_expense: float
    admin_expense: float
    rd_expense: float
    finance_expense: float
    total_profit: float
    net_profit: float
    cash: float
    accounts_receivable: float
    inventory: float
    fixed_assets: float
    total_assets: float
    short_term_loans: float
    accounts_payable: float
    total_liabilities: float
    owner_equity: float
    operating_cash_inflow: float
    operating_cash_outflow: float
    operating_cash_flow_net: float
    investing_cash_flow_net: float
    financing_cash_flow_net: float
    customer_collection: float
    sales_orders: float
    purchase_amount: float
    inventory_turnover_days: float
    tax_burden_rate: float


class MetricCard(BaseModel):
    key: str
    title: str
    value: str
    change: str
    status: str = "normal"


class ChartPoint(BaseModel):
    period: str
    value: float


class TrendChartSeries(BaseModel):
    name: str
    data: list[ChartPoint]


class RiskItem(BaseModel):
    id: str
    title: str
    level: int = Field(ge=1, le=5)
    level_label: str
    description: str
    trigger_reason: str
    suggested_checks: list[str]
    compliance_note: str


class DashboardOverview(BaseModel):
    period: str
    company_name: str
    metrics: list[MetricCard]
    trend_series: list[TrendChartSeries]
    expense_structure: list[ChartPoint]
    cash_flow_series: list[TrendChartSeries]
    profit_waterfall: list[ChartPoint]
    risk_heatmap: list[list[int]]
    risks: list[RiskItem]
    ai_summary: str


class ReportSection(BaseModel):
    title: str
    content: str


class ManagementReport(BaseModel):
    period: str = Field(pattern=MONTH_PATTERN)
    company_name: str
    title: str
    sections: list[ReportSection]


class DashboardAnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: str = Field(pattern=MONTH_PATTERN)
    records: list[MonthlyFinanceRecord] = Field(min_length=1, max_length=120)


class DashboardAnalyzeResponse(BaseModel):
    overview: DashboardOverview
    report: ManagementReport


class FieldMapping(BaseModel):
    field: str
    label: str
    source_header: str | None = None
    required: bool
    matched: bool
    status: str


class ImportPreview(BaseModel):
    sheet_name: str
    records: list[MonthlyFinanceRecord]
    matched_fields: list[str]
    field_mappings: list[FieldMapping] = []
    warnings: list[str] = []
