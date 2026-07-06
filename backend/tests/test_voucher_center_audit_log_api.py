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


def test_voucher_center_records_audit_logs_for_key_operations():
    reset_voucher_store()
    reset_system_admin_store()
    headers = {"X-Actor-Id": "u-finance-manager"}

    create_response = client.post("/api/v1/vouchers/center", json=_payload(), headers=headers)
    assert create_response.status_code == 200
    voucher = create_response.json()

    update_response = client.put(
        f"/api/v1/vouchers/center/{voucher['id']}",
        json=_payload("办公服务费-已修改"),
        headers=headers,
    )
    assert update_response.status_code == 200

    review_response = client.post(
        f"/api/v1/vouchers/center/{voucher['id']}/review",
        json={"reviewer": "财务主管"},
        headers=headers,
    )
    assert review_response.status_code == 200

    unreview_response = client.post(
        f"/api/v1/vouchers/center/{voucher['id']}/unreview",
        headers=headers,
    )
    assert unreview_response.status_code == 200

    attachment_response = client.post(
        f"/api/v1/vouchers/center/{voucher['id']}/attachments",
        files={"file": ("invoice.txt", b"invoice text", "text/plain")},
        headers=headers,
    )
    assert attachment_response.status_code == 200

    export_response = client.get("/api/v1/vouchers/center/export/csv", headers=headers)
    assert export_response.status_code == 200

    import_response = client.post(
        "/api/v1/vouchers/center/import",
        json={"vouchers": [_payload("导入凭证")]},
        headers=headers,
    )
    assert import_response.status_code == 200

    logs_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=20")
    assert logs_response.status_code == 200
    logs = logs_response.json()["logs"]
    events = [log["event"] for log in logs]

    for event in [
        "voucher.create",
        "voucher.update",
        "voucher.review",
        "voucher.unreview",
        "voucher.attachment.upload",
        "voucher.export",
        "voucher.import",
    ]:
        assert event in events

    for log in logs:
        assert log["actor_id"] == "u-finance-manager"
        assert log["module_id"] == "finance-center"
        assert log["result"] == "success"

    create_log = next(log for log in logs if log["event"] == "voucher.create")
    assert create_log["target_id"] == voucher["id"]
    assert create_log["metadata"]["voucher_number"] == voucher["voucher_number"]

    import_log = next(log for log in logs if log["event"] == "voucher.import")
    assert import_log["metadata"]["imported_count"] == 1

    export_log = next(log for log in logs if log["event"] == "voucher.export")
    assert export_log["target_id"] == "voucher-center"


def test_voucher_center_audit_uses_system_actor_when_header_is_missing():
    reset_voucher_store()
    reset_system_admin_store()

    response = client.post("/api/v1/vouchers/center", json=_payload())
    assert response.status_code == 200

    logs_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=5")
    assert logs_response.status_code == 200
    logs = logs_response.json()["logs"]
    assert logs[0]["actor_id"] == "system"
    assert logs[0]["event"] == "voucher.create"
