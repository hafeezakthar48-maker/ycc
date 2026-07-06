from app.data.sample_finance_data import SAMPLE_FINANCE_DATA
from app.services.home_dashboard_service import build_home_dashboard


def test_build_home_dashboard_returns_frd_sections_for_current_period():
    response = build_home_dashboard("2026-06", SAMPLE_FINANCE_DATA)

    assert response.period == "2026-06"
    assert response.company_name == "示例制造企业"
    assert [section.title for section in response.sections] == ["经营概况", "利润", "现金流", "库存", "税务"]

    metrics = {
        metric.key: metric.value
        for section in response.sections
        for metric in section.metrics
    }
    assert metrics["today_sales"] == "¥43万"
    assert metrics["month_sales"] == "¥1,286万"
    assert metrics["year_sales"] == "¥6,964万"
    assert metrics["gross_profit"] == "¥406万"
    assert metrics["net_profit"] == "¥146万"
    assert metrics["profit_margin"] == "11.4%"
    assert metrics["cash_inflow"] == "¥1,088万"
    assert metrics["cash_outflow"] == "¥996万"
    assert metrics["cash_balance"] == "¥402万"
    assert metrics["inventory_amount"] == "¥482万"
    assert metrics["inventory_turnover_rate"] == "4.9次/年"
    assert metrics["monthly_tax_payable"] == "¥49万"
    assert metrics["tax_burden_rate"] == "3.8%"
    assert metrics["risk_count"] == "4项"
    assert response.ai_tips
    assert {tip.category for tip in response.ai_tips} == {"风险提示", "异常分析", "今日经营建议"}
