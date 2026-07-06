from fastapi.testclient import TestClient

from app.main import app
from app.services.accounting_period_service import reset_accounting_period_store
from app.services.accounting_service import list_journal_entries, reset_accounting_store
from app.services.voucher_center_service import reset_voucher_store


client = TestClient(app)


def setup_function():
    reset_voucher_store()
    reset_accounting_period_store()
    reset_accounting_store()


def _create_reviewed_voucher():
    response = client.post(
        "/api/v1/vouchers/center",
        json={
            "account_set_id": "default",
            "voucher_date": "2026-06-18",
            "summary": "费用采购",
            "counterparty": "上海服务商",
            "invoice_number": "INV-001",
            "amount": "100.00",
            "tax_amount": "0.00",
            "total_amount_with_tax": "100.00",
            "lines": [
                {"account_code": "6602", "account_name": "管理费用", "direction": "借", "amount": "100.00", "explanation": "费用"},
                {"account_code": "2202", "account_name": "应付账款", "direction": "贷", "amount": "100.00", "explanation": "应付"},
            ],
        },
        headers={"X-Actor-Id": "u-finance-manager"},
    )
    voucher_id = response.json()["id"]
    client.post(
        f"/api/v1/vouchers/center/{voucher_id}/review",
        json={"reviewer": "财务主管"},
        headers={"X-Actor-Id": "u-finance-manager"},
    )
    return voucher_id


def test_post_voucher_creates_formal_journal_entry():
    voucher_id = _create_reviewed_voucher()

    response = client.post(
        f"/api/v1/vouchers/center/{voucher_id}/post",
        json={"operator": "财务主管"},
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["posting_status"] == "posted"
    assert payload["journal_entry_id"].startswith("je-")
    entries = list_journal_entries("default", "2026-06").entries
    assert entries[0].source_id == voucher_id
    assert entries[0].entry_number == "JE-202606-0001"


def test_unpost_voucher_creates_reversal_journal_entry():
    voucher_id = _create_reviewed_voucher()
    posted = client.post(
        f"/api/v1/vouchers/center/{voucher_id}/post",
        json={"operator": "财务主管"},
        headers={"X-Actor-Id": "u-finance-manager"},
    ).json()

    response = client.post(
        f"/api/v1/vouchers/center/{voucher_id}/unpost",
        json={"operator": "财务主管"},
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["posting_status"] == "unposted"
    assert payload["journal_reversal_entry_id"].startswith("je-")
    entries = list_journal_entries("default", "2026-06").entries
    assert len(entries) == 2
    assert entries[1].reversal_of_entry_id == posted["journal_entry_id"]
