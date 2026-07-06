from app.data.sample_finance_data import SAMPLE_FINANCE_DATA
from app.services.risk_service import detect_risks


def test_detect_risks_returns_prudent_finance_risk_items():
    risks = detect_risks("2026-06", SAMPLE_FINANCE_DATA)

    titles = {risk.title for risk in risks}

    assert "现金流与利润背离" in titles
    assert "库存周转异常" in titles
    assert "税负率需复核" in titles
    assert all("建议财务人员结合企业实际业务" in risk.compliance_note for risk in risks)


def test_risk_levels_are_in_expected_range():
    risks = detect_risks("2026-06", SAMPLE_FINANCE_DATA)

    assert risks
    assert all(1 <= risk.level <= 5 for risk in risks)
