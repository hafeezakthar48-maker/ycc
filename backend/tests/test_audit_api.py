from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_audit_review_endpoint_returns_findings():
    response = client.post(
        "/api/v1/audit/review",
        json={
            "audit_subject": "voucher",
            "voucher_date": "2026-06-30",
            "summary": "办公服务费",
            "counterparty": "上海云智科技有限公司",
            "invoice_number": "",
            "amount": "1000.00",
            "tax_amount": "60.00",
            "total_amount_with_tax": "1099.00",
            "lines": [
                {
                    "account_code": "6602",
                    "account_name": "管理费用",
                    "direction": "借",
                    "amount": "1000.00",
                    "explanation": "办公服务费",
                },
                {
                    "account_code": "22210101",
                    "account_name": "应交税费-应交增值税（进项税额）",
                    "direction": "借",
                    "amount": "60.00",
                    "explanation": "进项税额",
                },
                {
                    "account_code": "2202",
                    "account_name": "应付账款",
                    "direction": "贷",
                    "amount": "1099.00",
                    "explanation": "应付未付款",
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    finding_ids = {finding["id"] for finding in payload["findings"]}
    assert payload["rating"] == "高风险"
    assert "amount_mismatch" in finding_ids
    assert "voucher_not_balanced" in finding_ids
    assert "missing_invoice_number" in finding_ids
    assert payload["requires_human_review"] is True
