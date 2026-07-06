from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.voucher_center import VoucherCenterCreateRequest, VoucherCenterLine
from app.services.accounting_period_service import (
    close_accounting_period,
    list_account_sets,
    list_accounting_periods,
    reopen_accounting_period,
    reset_accounting_period_store,
)
from app.services.voucher_center_service import create_voucher, post_voucher, reset_voucher_store, review_voucher


@pytest.fixture(autouse=True)
def isolated_stores(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_VOUCHER_DB_PATH", str(tmp_path / "voucher-center.sqlite3"))
    reset_voucher_store()
    reset_accounting_period_store()


def _request(voucher_date: str = "2026-06-30") -> VoucherCenterCreateRequest:
    return VoucherCenterCreateRequest(
        voucher_date=voucher_date,
        summary="期间管理验证",
        counterparty="上海云智科技有限公司",
        invoice_number="PERIOD-001",
        amount=Decimal("1000.00"),
        tax_amount=Decimal("60.00"),
        total_amount_with_tax=Decimal("1060.00"),
        lines=[
            VoucherCenterLine(account_code="6602", account_name="管理费用", direction="借", amount=Decimal("1000.00"), explanation="办公服务费"),
            VoucherCenterLine(account_code="22210101", account_name="应交税费-应交增值税（进项税额）", direction="借", amount=Decimal("60.00"), explanation="进项税额"),
            VoucherCenterLine(account_code="2202", account_name="应付账款", direction="贷", amount=Decimal("1060.00"), explanation="应付未付款"),
        ],
    )


def _period(periods, period: str):
    return next(item for item in periods.periods if item.period == period)


def test_default_account_set_and_open_periods_include_voucher_months():
    create_voucher(_request("2026-07-05"))

    account_sets = list_account_sets()
    periods = list_accounting_periods("default")

    assert account_sets.account_sets[0].id == "default"
    assert account_sets.account_sets[0].is_default is True
    assert _period(periods, "2026-06").status == "open"
    assert _period(periods, "2026-07").voucher_count == 1
    assert _period(periods, "2026-07").posted_voucher_count == 0


def test_accounting_period_can_be_closed_and_reopened():
    closed = close_accounting_period("2026-06", "财务主管")

    assert closed.period == "2026-06"
    assert closed.status == "closed"
    assert closed.closed_by == "财务主管"
    assert closed.closed_at is not None

    reopened = reopen_accounting_period("2026-06", "财务主管")
    assert reopened.status == "open"
    assert reopened.closed_by is None
    assert reopened.closed_at is None


def test_posting_rejects_closed_accounting_period():
    close_accounting_period("2026-06", "财务主管")
    voucher = create_voucher(_request("2026-06-30"))
    reviewed = review_voucher(voucher.id, "财务主管")

    with pytest.raises(HTTPException) as exc_info:
        post_voucher(reviewed.id, "财务主管")

    assert exc_info.value.status_code == 409
    assert "期间已关闭" in exc_info.value.detail


def test_period_counts_include_posted_vouchers():
    voucher = create_voucher(_request("2026-06-30"))
    reviewed = review_voucher(voucher.id, "财务主管")
    post_voucher(reviewed.id, "财务主管")

    periods = list_accounting_periods("default")
    period = _period(periods, "2026-06")

    assert period.voucher_count == 1
    assert period.posted_voucher_count == 1
