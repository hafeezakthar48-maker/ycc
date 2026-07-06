from app.data.sample_finance_data import SAMPLE_FINANCE_DATA
from app.services.analysis_service import build_dashboard_overview


def test_dashboard_overview_contains_core_metrics():
    overview = build_dashboard_overview("2026-06", SAMPLE_FINANCE_DATA)

    titles = {metric.title for metric in overview.metrics}

    assert overview.period == "2026-06"
    assert "营业收入" in titles
    assert "净利润" in titles
    assert "经营现金流" in titles
    assert "综合风险" in titles


def test_dashboard_overview_contains_chart_data():
    overview = build_dashboard_overview("2026-06", SAMPLE_FINANCE_DATA)

    assert len(overview.trend_series) == 3
    assert len(overview.trend_series[0].data) == 12
    assert len(overview.expense_structure) == 4
    assert len(overview.cash_flow_series) == 3
    assert len(overview.profit_waterfall) == 5
