from fastapi.testclient import TestClient

from app.main import app
from app.services.system_admin_service import reset_system_admin_store
from app.services.voucher_center_service import reset_voucher_store


client = TestClient(app)


def _payload(summary: str = "办公服务费"):
    return {
        "voucher_date": "2026-06-30",
        "summary": summary,
        "counterparty": "上海云智科技有限公司",
        "invoice_number": "12345678",
        "amount": "1000.00",
        "tax_amount": "60.00",
        "total_amount_with_tax": "1060.00",
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
                "amount": "1060.00",
                "explanation": "应付未付款",
            },
        ],
    }


def test_voucher_center_rejects_unauthorized_review_export_and_attachment():
    reset_voucher_store()
    reset_system_admin_store()
    finance_headers = {"X-Actor-Id": "u-finance-manager"}
    integrator_headers = {"X-Actor-Id": "u-api-integrator"}

    create_response = client.post("/api/v1/vouchers/center", json=_payload(), headers=finance_headers)
    assert create_response.status_code == 200
    voucher = create_response.json()

    review_response = client.post(
        f"/api/v1/vouchers/center/{voucher['id']}/review",
        json={"reviewer": "接口集成员"},
        headers=integrator_headers,
    )
    export_response = client.get("/api/v1/vouchers/center/export/csv", headers=integrator_headers)
    attachment_response = client.post(
        f"/api/v1/vouchers/center/{voucher['id']}/attachments",
        files={"file": ("invoice.txt", b"invoice text", "text/plain")},
        headers=integrator_headers,
    )

    assert review_response.status_code == 403
    assert export_response.status_code == 403
    assert attachment_response.status_code == 403
    assert "权限不足" in review_response.json()["detail"]

    voucher_response = client.get("/api/v1/vouchers/center")
    assert voucher_response.status_code == 200
    stored = voucher_response.json()["vouchers"][0]
    assert stored["status"] == "draft"
    assert stored["attachments"] == []

    logs_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=10")
    assert logs_response.status_code == 200
    logs = logs_response.json()["logs"]
    denied_logs = [log for log in logs if log["result"] == "denied"]
    assert [log["event"] for log in denied_logs] == [
        "voucher.attachment.upload",
        "voucher.export",
        "voucher.review",
    ]
    assert all(log["actor_id"] == "u-api-integrator" for log in denied_logs)
    assert all(log["metadata"]["permission_code"].startswith("voucher.") for log in denied_logs)


def test_finance_manager_has_voucher_operation_permissions():
    reset_system_admin_store()

    for permission_code in [
        "voucher.create",
        "voucher.update",
        "voucher.review",
        "voucher.unreview",
        "voucher.import",
        "voucher.export",
        "voucher.attachment.upload",
    ]:
        response = client.post(
            "/api/v1/system/authorize",
            json={"user_id": "u-finance-manager", "permission_code": permission_code},
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is True
