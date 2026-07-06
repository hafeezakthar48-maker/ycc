from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.accounting_period_service import reset_accounting_period_store
from app.services.system_admin_service import reset_system_admin_store
from app.services.voucher_center_service import reset_voucher_store


client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_stores(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_VOUCHER_DB_PATH", str(tmp_path / "voucher-center.sqlite3"))
    reset_voucher_store()
    reset_system_admin_store()
    reset_accounting_period_store()


def _payload(account_set_id: str, amount: str, tax_amount: str):
    amount_value = Decimal(amount)
    tax_value = Decimal(tax_amount)
    total = amount_value + tax_value
    return {
        "account_set_id": account_set_id,
        "voucher_date": "2026-06-30",
        "summary": f"{account_set_id} 账套 API 验证",
        "counterparty": "上海云智科技有限公司",
        "invoice_number": f"{account_set_id}-API-001",
        "amount": str(amount_value),
        "tax_amount": str(tax_value),
        "total_amount_with_tax": str(total),
        "lines": [
            {
                "account_code": "6602",
                "account_name": "管理费用",
                "direction": "借",
                "amount": str(amount_value),
                "explanation": "办公服务费",
            },
            {
                "account_code": "22210101",
                "account_name": "应交税费-应交增值税（进项税额）",
                "direction": "借",
                "amount": str(tax_value),
                "explanation": "进项税额",
            },
            {
                "account_code": "2202",
                "account_name": "应付账款",
                "direction": "贷",
                "amount": str(total),
                "explanation": "应付未付款",
            },
        ],
    }


def _create_and_review(account_set_id: str, amount: str, tax_amount: str):
    headers = {"X-Actor-Id": "u-finance-manager"}
    create_response = client.post(
        "/api/v1/vouchers/center",
        json=_payload(account_set_id, amount, tax_amount),
        headers=headers,
    )
    assert create_response.status_code == 200
    voucher = create_response.json()
    review_response = client.post(
        f"/api/v1/vouchers/center/{voucher['id']}/review",
        json={"reviewer": "财务主管"},
        headers=headers,
    )
    assert review_response.status_code == 200
    return review_response.json()


def test_ledger_api_filters_by_account_set_and_records_metadata():
    headers = {"X-Actor-Id": "u-finance-manager"}
    _create_and_review("default", "1000.00", "60.00")
    _create_and_review("cross_border", "2000.00", "120.00")

    response = client.get(
        "/api/v1/ledger/general?period=2026-06&account_set_id=cross_border",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["voucher_count"] == 1
    assert Decimal(str(payload["total_debit"])) == Decimal("2120.00")

    logs_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&event=ledger.general.read")
    assert logs_response.status_code == 200
    log = logs_response.json()["logs"][0]
    assert log["metadata"]["account_set_id"] == "cross_border"


def test_voucher_center_list_can_filter_by_account_set():
    _create_and_review("default", "1000.00", "60.00")
    cross_border = _create_and_review("cross_border", "2000.00", "120.00")

    response = client.get("/api/v1/vouchers/center?account_set_id=cross_border")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["vouchers"][0]["id"] == cross_border["id"]
    assert payload["vouchers"][0]["account_set_id"] == "cross_border"


def test_close_period_rejects_unposted_vouchers_from_same_account_set():
    headers = {"X-Actor-Id": "u-finance-manager"}
    _create_and_review("default", "1000.00", "60.00")

    response = client.post(
        "/api/v1/ledger/periods/2026-06/close?account_set_id=default",
        json={"operator": "财务主管"},
        headers=headers,
    )

    assert response.status_code == 409
    assert "未过账凭证" in response.json()["detail"]


def test_account_sets_api_exposes_multiple_account_sets():
    response = client.get("/api/v1/ledger/account-sets", headers={"X-Actor-Id": "u-finance-manager"})

    assert response.status_code == 200
    account_set_ids = [item["id"] for item in response.json()["account_sets"]]
    assert "default" in account_set_ids
    assert "cross_border" in account_set_ids
