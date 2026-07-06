from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_voucher_draft_endpoint_returns_balanced_lines():
    response = client.post(
        "/api/v1/vouchers/draft",
        json={
            "business_type": "expense_purchase",
            "voucher_date": "2026-06-30",
            "counterparty": "上海云智科技有限公司",
            "amount": "1000.00",
            "tax_amount": "60.00",
            "total_amount_with_tax": "1060.00",
            "payment_status": "unpaid",
            "memo": "办公服务费",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scenario_label"] == "费用采购"
    assert payload["balanced"] is True
    assert len(payload["lines"]) == 3
    assert payload["lines"][0]["account_name"] == "管理费用"
    assert payload["citations"]
    assert payload["requires_human_review"] is True
