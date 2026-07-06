from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.voucher_center import VoucherCenterCreateRequest, VoucherCenterLine
from app.services.system_admin_service import reset_system_admin_store
from app.services.voucher_center_service import create_voucher, reset_voucher_store, review_voucher


client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_voucher_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_VOUCHER_DB_PATH", str(tmp_path / "voucher-center.sqlite3"))
    reset_voucher_store()
    reset_system_admin_store()


def _request() -> VoucherCenterCreateRequest:
    return VoucherCenterCreateRequest(
        voucher_date="2026-06-30",
        summary="账簿权限审计验证",
        counterparty="上海云智科技有限公司",
        invoice_number="LEDGER-AUDIT-001",
        amount=Decimal("1000.00"),
        tax_amount=Decimal("60.00"),
        total_amount_with_tax=Decimal("1060.00"),
        lines=[
            VoucherCenterLine(account_code="6602", account_name="管理费用", direction="借", amount=Decimal("1000.00"), explanation="办公服务费"),
            VoucherCenterLine(account_code="22210101", account_name="应交税费-应交增值税（进项税额）", direction="借", amount=Decimal("60.00"), explanation="进项税额"),
            VoucherCenterLine(account_code="2202", account_name="应付账款", direction="贷", amount=Decimal("1060.00"), explanation="应付未付款"),
        ],
    )


def _seed_reviewed_voucher():
    voucher = create_voucher(_request())
    return review_voucher(voucher.id, "财务主管")


def test_ledger_read_records_success_audit_logs_for_authorized_actor():
    _seed_reviewed_voucher()
    headers = {"X-Actor-Id": "u-finance-manager"}

    general_response = client.get("/api/v1/ledger/general?period=2026-06", headers=headers)
    detail_response = client.get("/api/v1/ledger/detail?period=2026-06&account_code=6602", headers=headers)
    balance_response = client.get("/api/v1/ledger/account-balances?period=2026-06", headers=headers)

    assert general_response.status_code == 200
    assert detail_response.status_code == 200
    assert balance_response.status_code == 200

    logs_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=10")
    assert logs_response.status_code == 200
    logs = logs_response.json()["logs"]
    ledger_logs = [log for log in logs if log["event"].startswith("ledger.")]
    assert [log["event"] for log in ledger_logs] == [
        "ledger.account_balances.read",
        "ledger.detail.read",
        "ledger.general.read",
    ]
    assert all(log["actor_id"] == "u-finance-manager" for log in ledger_logs)
    assert all(log["result"] == "success" for log in ledger_logs)

    general_log = next(log for log in ledger_logs if log["event"] == "ledger.general.read")
    assert general_log["target_id"] == "ledger-general:2026-06"
    assert general_log["metadata"]["period"] == "2026-06"
    assert general_log["metadata"]["voucher_count"] == 1
    assert general_log["metadata"]["balanced"] is True

    detail_log = next(log for log in ledger_logs if log["event"] == "ledger.detail.read")
    assert detail_log["target_id"] == "ledger-detail:2026-06:6602"
    assert detail_log["metadata"]["account_code"] == "6602"
    assert detail_log["metadata"]["line_count"] == 1


def test_ledger_read_rejects_unauthorized_actor_and_records_denied_audit():
    _seed_reviewed_voucher()

    response = client.get(
        "/api/v1/ledger/general?period=2026-06",
        headers={"X-Actor-Id": "u-api-integrator"},
    )

    assert response.status_code == 403
    assert "权限不足" in response.json()["detail"]

    logs_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=5")
    assert logs_response.status_code == 200
    logs = logs_response.json()["logs"]
    assert logs[0]["actor_id"] == "u-api-integrator"
    assert logs[0]["event"] == "ledger.general.read"
    assert logs[0]["target_id"] == "ledger-general:2026-06"
    assert logs[0]["result"] == "denied"
    assert logs[0]["metadata"]["permission_code"] == "ledger.read"
