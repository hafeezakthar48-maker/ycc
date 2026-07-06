from fastapi.testclient import TestClient

from app.main import app
from app.services.accounting_archive_service import reset_accounting_archive_store
from app.services.system_admin_service import reset_system_admin_store
from app.services.voucher_center_service import reset_voucher_store


client = TestClient(app)


def _voucher_payload():
    return {
        "account_set_id": "default",
        "voucher_date": "2026-06-30",
        "summary": "Office service fee",
        "counterparty": "Shanghai Cloud Wisdom Ltd.",
        "invoice_number": "INV-20260630",
        "amount": "1000.00",
        "tax_amount": "60.00",
        "total_amount_with_tax": "1060.00",
        "lines": [
            {
                "account_code": "6602",
                "account_name": "Management Expense",
                "direction": "\u501f",
                "amount": "1000.00",
                "explanation": "Office service fee",
            },
            {
                "account_code": "22210101",
                "account_name": "Input VAT",
                "direction": "\u501f",
                "amount": "60.00",
                "explanation": "Input VAT",
            },
            {
                "account_code": "2202",
                "account_name": "Accounts Payable",
                "direction": "\u8d37",
                "amount": "1060.00",
                "explanation": "Payable",
            },
        ],
    }


def test_accounting_archive_lists_documents_creates_case_and_downloads_package():
    reset_voucher_store()
    reset_accounting_archive_store()
    reset_system_admin_store()
    headers = {"x-actor-id": "u-finance-manager"}

    create_response = client.post("/api/v1/vouchers/center", json=_voucher_payload(), headers=headers)
    assert create_response.status_code == 200
    voucher = create_response.json()

    upload_response = client.post(
        f"/api/v1/vouchers/center/{voucher['id']}/attachments",
        files={"file": ("invoice.txt", b"invoice text", "text/plain")},
        headers=headers,
    )
    assert upload_response.status_code == 200
    archive_document_id = upload_response.json()["attachments"][0]["archive_document_id"]

    list_response = client.get(
        "/api/v1/accounting-archive/documents?account_set_id=default&period=2026-06",
        headers=headers,
    )
    assert list_response.status_code == 200
    documents_payload = list_response.json()
    assert documents_payload["total"] == 1
    assert documents_payload["documents"][0]["archive_document_id"] == archive_document_id
    assert documents_payload["documents"][0]["filename"] == "invoice.txt"

    case_response = client.post(
        "/api/v1/accounting-archive/cases",
        json={
            "account_set_id": "default",
            "period": "2026-06",
            "case_type": "voucher",
            "title": "June voucher archive",
            "document_ids": [archive_document_id],
            "created_by": "u-finance-manager",
        },
        headers=headers,
    )
    assert case_response.status_code == 200
    archive_case = case_response.json()
    assert archive_case["document_count"] == 1
    assert archive_case["archive_status"] == "archived"

    download_response = client.get(
        f"/api/v1/accounting-archive/cases/{archive_case['archive_case_id']}/download",
        headers=headers,
    )
    assert download_response.status_code == 200
    assert download_response.headers["content-type"].startswith("application/zip")
    assert download_response.content.startswith(b"PK")
    assert "accounting-archive-default-2026-06-voucher.zip" in download_response.headers["content-disposition"]

    audit_response = client.get("/api/v1/system/audit-logs?event=archive.package.download")
    assert audit_response.status_code == 200
    assert audit_response.json()["logs"][0]["metadata"]["document_count"] == 1


def test_accounting_archive_rejects_user_without_archive_permission_and_records_denied_audit():
    reset_accounting_archive_store()
    reset_system_admin_store()

    response = client.get(
        "/api/v1/accounting-archive/documents?account_set_id=default",
        headers={"x-actor-id": "u-api-integrator"},
    )

    assert response.status_code == 403
    audit_response = client.get("/api/v1/system/audit-logs?event=archive.document.list&actor_id=u-api-integrator")
    assert audit_response.status_code == 200
    logs = audit_response.json()["logs"]
    assert logs[0]["result"] == "denied"
    assert logs[0]["metadata"]["permission_code"] == "archive.read"
