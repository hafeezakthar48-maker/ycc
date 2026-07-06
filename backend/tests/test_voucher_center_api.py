from fastapi.testclient import TestClient

from app.main import app
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


def test_voucher_center_crud_review_attachment_and_export():
    reset_voucher_store()

    create_response = client.post("/api/v1/vouchers/center", json=_payload())
    assert create_response.status_code == 200
    voucher = create_response.json()
    assert voucher["voucher_number"] == "记-202606-0001"
    assert voucher["status"] == "draft"
    assert voucher["audit_result"]["rating"] == "通过"

    update_response = client.put(
        f"/api/v1/vouchers/center/{voucher['id']}",
        json=_payload("办公服务费-修改后"),
    )
    assert update_response.status_code == 200
    assert update_response.json()["summary"] == "办公服务费-修改后"

    review_response = client.post(
        f"/api/v1/vouchers/center/{voucher['id']}/review",
        json={"reviewer": "财务主管"},
    )
    assert review_response.status_code == 200
    assert review_response.json()["status"] == "reviewed"

    unreview_response = client.post(f"/api/v1/vouchers/center/{voucher['id']}/unreview")
    assert unreview_response.status_code == 200
    assert unreview_response.json()["status"] == "draft"

    attachment_response = client.post(
        f"/api/v1/vouchers/center/{voucher['id']}/attachments",
        files={"file": ("invoice.txt", b"invoice text", "text/plain")},
    )
    assert attachment_response.status_code == 200
    assert attachment_response.json()["attachments"][0]["ocr_status"] == "text_supported"

    list_response = client.get("/api/v1/vouchers/center")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    export_response = client.get("/api/v1/vouchers/center/export/csv")
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/csv")
    assert "记-202606-0001" in export_response.text


def test_voucher_center_import_endpoint_creates_multiple_vouchers():
    reset_voucher_store()

    response = client.post(
        "/api/v1/vouchers/center/import",
        json={"vouchers": [_payload("导入凭证一"), _payload("导入凭证二")]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["imported_count"] == 2
    assert payload["vouchers"][1]["voucher_number"] == "记-202606-0002"


def test_voucher_center_rejects_bad_date_and_direction():
    payload = _payload()
    payload["voucher_date"] = "20260630"
    payload["lines"][0]["direction"] = "sideways"

    response = client.post("/api/v1/vouchers/center", json=payload)

    assert response.status_code == 422


def test_voucher_center_rejects_extra_write_fields():
    payload = _payload()
    payload["reviewed_by"] = "forged reviewer"

    response = client.post("/api/v1/vouchers/center", json=payload)

    assert response.status_code == 422


def test_voucher_center_attachment_rejects_oversized_upload():
    reset_voucher_store()
    create_response = client.post("/api/v1/vouchers/center", json=_payload())
    voucher = create_response.json()

    response = client.post(
        f"/api/v1/vouchers/center/{voucher['id']}/attachments",
        files={"file": ("large.pdf", b"%PDF-" + (b"0" * (10 * 1024 * 1024 + 1)), "application/pdf")},
    )

    assert response.status_code == 413
