from app.models.finance import (
    ChartPoint,
    DashboardOverview,
    MetricCard,
    MonthlyFinanceRecord,
    TrendChartSeries,
)
from app.services.risk_service import detect_risks


COMPANY_NAME = "示例制造企业"


def _find_record(period: str, records: list[MonthlyFinanceRecord]) -> MonthlyFinanceRecord:
    for record in records:
        if record.period == period:
            return record
    available = ", ".join(record.period for record in records)
    raise ValueError(f"未找到期间 {period}，可用期间：{available}")


def _previous_record(
    period: str, records: list[MonthlyFinanceRecord]
) -> MonthlyFinanceRecord | None:
    for index, record in enumerate(records):
        if record.period == period and index > 0:
            return records[index - 1]
    return None


def _format_money(value: float) -> str:
    return f"¥{value:,.0f}万"


def _change_text(current: float, previous: float | None) -> str:
    if previous is None or previous == 0:
        return "无上期数据"
    change = current / previous - 1
    prefix = "+" if change >= 0 else ""
    return f"环比 {prefix}{change:.1%}"


def build_dashboard_overview(
    period: str, records: list[MonthlyFinanceRecord]
) -> DashboardOverview:
    current = _find_record(period, records)
    previous = _previous_record(period, records)
    risks = detect_risks(period, records)
    total_expense = (
        current.sales_expense
        + current.admin_expense
        + current.rd_expense
        + current.finance_expense
    )
    gross_profit = current.revenue - current.cost

    metrics = [
        MetricCard(
            key="revenue",
            title="营业收入",
            value=_format_money(current.revenue),
            change=_change_text(current.revenue, previous.revenue if previous else None),
        ),
        MetricCard(
            key="netProfit",
            title="净利润",
            value=_format_money(current.net_profit),
            change=_change_text(
                current.net_profit, previous.net_profit if previous else None
            ),
        ),
        MetricCard(
            key="operatingCashFlow",
            title="经营现金流",
            value=_format_money(current.operating_cash_flow_net),
            change=_change_text(
                current.operating_cash_flow_net,
                previous.operating_cash_flow_net if previous else None,
            ),
            status=(
                "warning"
                if current.operating_cash_flow_net < current.net_profit
                else "normal"
            ),
        ),
        MetricCard(
            key="risk",
            title="综合风险",
            value="★★★★☆" if any(risk.level >= 4 for risk in risks) else "★★★☆☆",
            change="需财务复核" if risks else "低风险",
            status="danger" if any(risk.level >= 4 for risk in risks) else "warning",
        ),
    ]

    trend_series = [
        TrendChartSeries(
            name="营业收入",
            data=[ChartPoint(period=item.period, value=item.revenue) for item in records],
        ),
        TrendChartSeries(
            name="营业成本",
            data=[ChartPoint(period=item.period, value=item.cost) for item in records],
        ),
        TrendChartSeries(
            name="净利润",
            data=[
                ChartPoint(period=item.period, value=item.net_profit) for item in records
            ],
        ),
    ]

    cash_flow_series = [
        TrendChartSeries(
            name="经营现金流",
            data=[
                ChartPoint(period=item.period, value=item.operating_cash_flow_net)
                for item in records
            ],
        ),
        TrendChartSeries(
            name="投资现金流",
            data=[
                ChartPoint(period=item.period, value=item.investing_cash_flow_net)
                for item in records
            ],
        ),
        TrendChartSeries(
            name="筹资现金流",
            data=[
                ChartPoint(period=item.period, value=item.financing_cash_flow_net)
                for item in records
            ],
        ),
    ]

    ai_summary = (
        f"{COMPANY_NAME}在{period}实现营业收入{_format_money(current.revenue)}，"
        f"净利润{_format_money(current.net_profit)}。经营现金流为"
        f"{_format_money(current.operating_cash_flow_net)}，低于净利润时应重点复核回款质量。"
        "系统识别出的风险仅作为经营与财税复核提示，不替代财务负责人判断。"
    )

    return DashboardOverview(
        period=period,
        company_name=COMPANY_NAME,
        metrics=metrics,
        trend_series=trend_series,
        expense_structure=[
            ChartPoint(period="销售费用", value=current.sales_expense),
            ChartPoint(period="管理费用", value=current.admin_expense),
            ChartPoint(period="研发费用", value=current.rd_expense),
            ChartPoint(period="财务费用", value=current.finance_expense),
        ],
        cash_flow_series=cash_flow_series,
        profit_waterfall=[
            ChartPoint(period="营业收入", value=current.revenue),
            ChartPoint(period="营业成本", value=-current.cost),
            ChartPoint(period="毛利", value=gross_profit),
            ChartPoint(period="期间费用", value=-total_expense),
            ChartPoint(period="净利润", value=current.net_profit),
        ],
        risk_heatmap=[
            [1, 2, 3, 4],
            [2, 3, 3, 4],
            [1, 2, 3, 3],
        ],
        risks=risks,
        ai_summary=ai_summary,
    )
