from app.models.finance import MonthlyFinanceRecord
from app.models.home_dashboard import HomeAiTip, HomeDashboardResponse, HomeMetric, HomeMetricSection
from app.services.risk_service import detect_risks


COMPANY_NAME = "示例制造企业"


def build_home_dashboard(period: str, records: list[MonthlyFinanceRecord]) -> HomeDashboardResponse:
    current = _find_record(period, records)
    current_year_records = [record for record in records if record.period.startswith(period[:4])]
    risks = detect_risks(period, records)
    gross_profit = current.revenue - current.cost
    profit_margin = current.net_profit / current.revenue if current.revenue else 0
    inventory_turnover_rate = 365 / current.inventory_turnover_days if current.inventory_turnover_days else 0
    slow_moving_inventory = current.inventory * 0.18 if current.inventory_turnover_days >= 70 else current.inventory * 0.08
    monthly_tax_payable = current.revenue * current.tax_burden_rate

    return HomeDashboardResponse(
        period=period,
        company_name=COMPANY_NAME,
        sections=[
            HomeMetricSection(
                key="business",
                title="经营概况",
                metrics=[
                    HomeMetric(key="today_sales", title="今日销售额", value=_format_money(current.revenue / 30), note="按本月收入日均折算"),
                    HomeMetric(key="month_sales", title="本月销售额", value=_format_money(current.revenue), note="当前期间营业收入"),
                    HomeMetric(key="year_sales", title="本年销售额", value=_format_money(sum(record.revenue for record in current_year_records)), note="当前年度累计收入"),
                ],
            ),
            HomeMetricSection(
                key="profit",
                title="利润",
                metrics=[
                    HomeMetric(key="gross_profit", title="毛利润", value=_format_money(gross_profit), note="营业收入 - 营业成本"),
                    HomeMetric(key="net_profit", title="净利润", value=_format_money(current.net_profit), note="当前期间净利润", status="warning" if current.net_profit < gross_profit * 0.4 else "normal"),
                    HomeMetric(key="profit_margin", title="利润率", value=_format_percent(profit_margin), note="净利润 / 营业收入"),
                ],
            ),
            HomeMetricSection(
                key="cash_flow",
                title="现金流",
                metrics=[
                    HomeMetric(key="cash_inflow", title="流入", value=_format_money(current.operating_cash_inflow), note="经营现金流入"),
                    HomeMetric(key="cash_outflow", title="流出", value=_format_money(current.operating_cash_outflow), note="经营现金流出"),
                    HomeMetric(key="cash_balance", title="余额", value=_format_money(current.cash), note="期末货币资金"),
                ],
            ),
            HomeMetricSection(
                key="inventory",
                title="库存",
                metrics=[
                    HomeMetric(key="inventory_amount", title="库存金额", value=_format_money(current.inventory), note="期末存货余额"),
                    HomeMetric(key="inventory_turnover_rate", title="库存周转率", value=f"{inventory_turnover_rate:.1f}次/年", note="365 / 周转天数", status="warning" if current.inventory_turnover_days >= 70 else "normal"),
                    HomeMetric(key="slow_moving_inventory", title="滞销库存", value=_format_money(slow_moving_inventory), note="基于周转天数的估算值", status="warning"),
                ],
            ),
            HomeMetricSection(
                key="tax",
                title="税务",
                metrics=[
                    HomeMetric(key="monthly_tax_payable", title="本月应纳税额", value=_format_money(monthly_tax_payable), note="收入 × 税负率估算"),
                    HomeMetric(key="tax_burden_rate", title="税负率", value=_format_percent(current.tax_burden_rate), note="当前期间税负率", status="warning" if current.tax_burden_rate < 0.04 else "normal"),
                    HomeMetric(key="risk_count", title="风险数量", value=f"{len(risks)}项", note="系统识别的经营与财税风险", status="danger" if any(risk.level >= 4 for risk in risks) else "warning"),
                ],
            ),
        ],
        ai_tips=_build_ai_tips(current, risks),
    )


def _find_record(period: str, records: list[MonthlyFinanceRecord]) -> MonthlyFinanceRecord:
    for record in records:
        if record.period == period:
            return record
    available = ", ".join(record.period for record in records)
    raise ValueError(f"未找到期间 {period}，可用期间：{available}")


def _format_money(value: float) -> str:
    return f"¥{value:,.0f}万"


def _format_percent(value: float) -> str:
    return f"{value:.1%}"


def _build_ai_tips(current: MonthlyFinanceRecord, risks) -> list[HomeAiTip]:
    risk_title = "当前存在高优先级风险" if any(risk.level >= 4 for risk in risks) else "当前风险以复核项为主"
    return [
        HomeAiTip(
            category="风险提示",
            title=risk_title,
            content=f"系统识别 {len(risks)} 项风险，请优先复核现金流、库存周转和税负率。",
            level="high" if any(risk.level >= 4 for risk in risks) else "medium",
        ),
        HomeAiTip(
            category="异常分析",
            title="现金流与利润需要联动复核",
            content=f"本期经营现金流净额为{_format_money(current.operating_cash_flow_net)}，净利润为{_format_money(current.net_profit)}。",
            level="medium",
        ),
        HomeAiTip(
            category="今日经营建议",
            title="优先处理回款、库存和税务证据链",
            content="建议查看应收账款账龄、滞销库存清单、发票与申报表匹配情况。",
            level="normal",
        ),
    ]
