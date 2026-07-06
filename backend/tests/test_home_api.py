from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_home_dashboard_endpoint_returns_frd_dashboard_payload():
    response = client.get("/api/v1/home/dashboard?period=2026-06")

    assert response.status_code == 200
    payload = response.json()
    assert payload["period"] == "2026-06"
    assert [section["title"] for section in payload["sections"]] == ["经营概况", "利润", "现金流", "库存", "税务"]
    assert len(payload["ai_tips"]) == 3
    tax_section = next(section for section in payload["sections"] if section["key"] == "tax")
    assert {metric["key"] for metric in tax_section["metrics"]} == {"monthly_tax_payable", "tax_burden_rate", "risk_count"}


def test_home_dashboard_endpoint_validates_period_format():
    response = client.get("/api/v1/home/dashboard?period=202606")

    assert response.status_code == 422
    assert "YYYY-MM" in response.json()["detail"]


def test_home_analyze_endpoint_uses_submitted_records():
    response = client.post(
        "/api/v1/home/analyze",
        json={
            "period": "2026-06",
            "records": [
                {
                    "period": "2026-06",
                    "revenue": 3000,
                    "cost": 1800,
                    "sales_expense": 120,
                    "admin_expense": 90,
                    "rd_expense": 40,
                    "finance_expense": 20,
                    "total_profit": 950,
                    "net_profit": 720,
                    "cash": 880,
                    "accounts_receivable": 500,
                    "inventory": 620,
                    "fixed_assets": 1000,
                    "total_assets": 3600,
                    "short_term_loans": 260,
                    "accounts_payable": 380,
                    "total_liabilities": 1200,
                    "owner_equity": 2400,
                    "operating_cash_inflow": 2500,
                    "operating_cash_outflow": 1900,
                    "operating_cash_flow_net": 600,
                    "investing_cash_flow_net": -100,
                    "financing_cash_flow_net": 80,
                    "customer_collection": 2400,
                    "sales_orders": 3000,
                    "purchase_amount": 1500,
                    "inventory_turnover_days": 60,
                    "tax_burden_rate": 0.05,
                }
            ],
        },
    )

    assert response.status_code == 200
    metrics = {
        metric["key"]: metric["value"]
        for section in response.json()["sections"]
        for metric in section["metrics"]
    }
    assert metrics["month_sales"] == "¥3,000万"
    assert metrics["today_sales"] == "¥100万"
    assert metrics["risk_count"] == "0项"
