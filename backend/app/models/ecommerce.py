from pydantic import BaseModel, Field


class ECommerceProfitRequest(BaseModel):
    period: str
    platform: str
    gmv: float = Field(ge=0)
    refund_amount: float = Field(ge=0)
    product_cost: float = Field(ge=0)
    platform_commission: float = Field(ge=0)
    payment_fee: float = Field(ge=0)
    advertising_spend: float = Field(ge=0)
    logistics_cost: float = Field(ge=0)
    packaging_cost: float = Field(ge=0)
    labor_cost: float = Field(ge=0)
    other_cost: float = Field(ge=0)
    order_count: int = Field(ge=0)
    visitor_count: int = Field(ge=0)


class ECommerceMetric(BaseModel):
    key: str
    title: str
    value: str
    status: str = "normal"


class ECommerceChartPoint(BaseModel):
    name: str
    value: float


class ECommerceRiskItem(BaseModel):
    id: str
    title: str
    level: int = Field(ge=1, le=5)
    description: str
    suggestion: str


class ECommerceProfitResult(BaseModel):
    period: str
    platform: str
    net_sales: float
    gross_profit: float
    contribution_profit: float
    net_profit: float
    gross_margin: float
    net_margin: float
    ad_spend_rate: float
    roi: float
    refund_rate: float
    average_order_value: float
    conversion_rate: float
    metrics: list[ECommerceMetric]
    cost_breakdown: list[ECommerceChartPoint]
    profit_bridge: list[ECommerceChartPoint]
    risks: list[ECommerceRiskItem]
    suggestions: list[str]
