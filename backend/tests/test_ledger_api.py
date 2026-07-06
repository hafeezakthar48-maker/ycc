from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.voucher_center import VoucherCenterCreateRequest, VoucherCenterLine
from app.services.voucher_center_service import create_voucher, reset_voucher_store, review_voucher


client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_voucher_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_VOUCHER_DB_PATH", str(tmp_path / "voucher-center.sqlite3"))
    reset_voucher_store()


def _request() -> VoucherCenterCreateRequest:
    return VoucherCenterCreateRequest(
        voucher_date="2026-06-30",
        summary="办公服务费",
        counterparty="上海云智科技有限公司",
        invoice_number="12345678",
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


def _decimal(value) -> Decimal:
    return Decimal(str(value))


def test_ledger_api_returns_general_detail_and_balance_reports():
    reviewed = _seed_reviewed_voucher()

    general_response = client.get("/api/v1/ledger/general?period=2026-06")
    assert general_response.status_code == 200
    general = general_response.json()
    assert general["voucher_count"] == 1
    assert general["entry_count"] == 3
    assert _decimal(general["total_debit"]) == Decimal("1060.00")
    assert _decimal(general["total_credit"]) == Decimal("1060.00")
    assert general["balanced"] is True

    detail_response = client.get("/api/v1/ledger/detail?period=2026-06&account_code=6602")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["account_name"] == "管理费用"
    assert detail["line_count"] == 1
    assert detail["lines"][0]["voucher_id"] == reviewed.id
    assert _decimal(detail["lines"][0]["debit_amount"]) == Decimal("1000.00")

    balance_response = client.get("/api/v1/ledger/account-balances?period=2026-06")
    assert balance_response.status_code == 200
    balance_table = balance_response.json()
    assert balance_table["account_count"] == 3
    assert balance_table["accounts"][0]["account_code"] == "2202"
    assert balance_table["accounts"][0]["balance_direction"] == "贷"


def test_ledger_api_rejects_invalid_period():
    response = client.get("/api/v1/ledger/general?period=202606")

    assert response.status_code == 422
