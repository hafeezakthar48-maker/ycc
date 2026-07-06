from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _payload() -> dict:
    return {
        "period": "2026-06",
        "platform": "抖音小店",
        "gmv": 100000,
        "refund_amount": 8000,
        "product_cost": 48000,
        "platform_commission": 5500,
        "payment_fee": 600,
        "advertising_spend": 18000,
        "logistics_cost": 5200,
        "packaging_cost": 1200,
        "labor_cost": 4000,
        "other_cost": 1800,
        "order_count": 2000,
        "visitor_count": 50000,
    }


def test_ecommerce_profit_endpoint_returns_profit_analysis_payload():
    response = client.post("/api/v1/ecommerce/profit/analyze", json=_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["period"] == "2026-06"
    assert payload["platform"] == "抖音小店"
    assert payload["net_sales"] == 92000
    assert payload["net_profit"] == 7700
    assert payload["metrics"]
    assert payload["cost_breakdown"]
    assert payload["profit_bridge"]
    assert payload["risks"]
    assert payload["suggestions"]
