from fastapi.testclient import TestClient

from app.main import app
from app.services.system_admin_service import reset_system_admin_store
from app.services.voucher_center_service import reset_voucher_store


client = TestClient(app)


def _payload(summary: str = "过账API验证"):
    return {
        "voucher_date": "2026-06-30",
        "summary": summary,
        "counterparty": "上海云智科技有限公司",
        "invoice_number": "POST-API-001",
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


def test_voucher_post_and_unpost_endpoints_record_audit_logs():
    reset_voucher_store()
    reset_system_admin_store()
    headers = {"X-Actor-Id": "u-finance-manager"}

    create_response = client.post("/api/v1/vouchers/center", json=_payload(), headers=headers)
    assert create_response.status_code == 200
    voucher = create_response.json()

    review_response = client.post(
        f"/api/v1/vouchers/center/{voucher['id']}/review",
        json={"reviewer": "财务主管"},
        headers=headers,
    )
    assert review_response.status_code == 200

    post_response = client.post(
        f"/api/v1/vouchers/center/{voucher['id']}/post",
        json={"operator": "财务主管"},
        headers=headers,
    )
    assert post_response.status_code == 200
    posted = post_response.json()
    assert posted["posting_status"] == "posted"
    assert posted["posted_by"] == "财务主管"
    assert posted["posted_at"]

    unpost_response = client.post(
        f"/api/v1/vouchers/center/{voucher['id']}/unpost",
        json={"operator": "财务主管"},
        headers=headers,
    )
    assert unpost_response.status_code == 200
    unposted = unpost_response.json()
    assert unposted["posting_status"] == "unposted"
    assert unposted["posted_by"] is None
    assert unposted["posted_at"] is None

    logs_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=10")
    assert logs_response.status_code == 200
    logs = logs_response.json()["logs"]
    events = [log["event"] for log in logs]
    assert "voucher.post" in events
    assert "voucher.unpost" in events

    post_log = next(log for log in logs if log["event"] == "voucher.post")
    assert post_log["target_id"] == voucher["id"]
    assert post_log["metadata"]["voucher_number"] == voucher["voucher_number"]
    assert post_log["metadata"]["posted_by"] == "财务主管"


def test_voucher_posting_rejects_unauthorized_actor():
    reset_voucher_store()
    reset_system_admin_store()
    finance_headers = {"X-Actor-Id": "u-finance-manager"}
    integrator_headers = {"X-Actor-Id": "u-api-integrator"}

    create_response = client.post("/api/v1/vouchers/center", json=_payload(), headers=finance_headers)
    voucher = create_response.json()
    client.post(
        f"/api/v1/vouchers/center/{voucher['id']}/review",
        json={"reviewer": "财务主管"},
        headers=finance_headers,
    )

    response = client.post(
        f"/api/v1/vouchers/center/{voucher['id']}/post",
        json={"operator": "接口集成员"},
        headers=integrator_headers,
    )

    assert response.status_code == 403
    assert "权限不足" in response.json()["detail"]

    logs_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=5")
    logs = logs_response.json()["logs"]
    assert logs[0]["event"] == "voucher.post"
    assert logs[0]["result"] == "denied"
    assert logs[0]["metadata"]["permission_code"] == "voucher.post"


def test_finance_manager_has_voucher_posting_permissions():
    reset_system_admin_store()

    for permission_code in ["voucher.post", "voucher.unpost"]:
        response = client.post(
            "/api/v1/system/authorize",
            json={"user_id": "u-finance-manager", "permission_code": permission_code},
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is True
