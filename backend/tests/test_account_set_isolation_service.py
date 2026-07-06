from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.voucher_center import VoucherCenterCreateRequest, VoucherCenterLine
from app.services.accounting_period_service import (
    close_accounting_period,
    list_accounting_periods,
    reset_accounting_period_store,
)
from app.services.accounting_service import reset_accounting_store
from app.services.ledger_service import build_general_ledger
from app.services.voucher_center_service import create_voucher, post_voucher, reset_voucher_store, review_voucher


@pytest.fixture(autouse=True)
def isolated_stores(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_VOUCHER_DB_PATH", str(tmp_path / "voucher-center.sqlite3"))
    monkeypatch.setenv("FINANCE_AI_ACCOUNTING_DB_PATH", str(tmp_path / "formal-accounting.sqlite3"))
    reset_voucher_store()
    reset_accounting_store()
    reset_accounting_period_store()


def _request(account_set_id: str, summary: str, amount: Decimal, tax_amount: Decimal) -> VoucherCenterCreateRequest:
    total = amount + tax_amount
    return VoucherCenterCreateRequest(
        account_set_id=account_set_id,
        voucher_date="2026-06-30",
        summary=summary,
        counterparty="上海云智科技有限公司",
        invoice_number=f"{account_set_id}-001",
        amount=amount,
        tax_amount=tax_amount,
        total_amount_with_tax=total,
        lines=[
            VoucherCenterLine(account_code="6602", account_name="管理费用", direction="借", amount=amount, explanation=summary),
            VoucherCenterLine(account_code="22210101", account_name="应交税费-应交增值税（进项税额）", direction="借", amount=tax_amount, explanation="进项税额"),
            VoucherCenterLine(account_code="2202", account_name="应付账款", direction="贷", amount=total, explanation="应付未付款"),
        ],
    )


def _seed_reviewed(account_set_id: str, amount: str, tax_amount: str):
    voucher = create_voucher(
        _request(
            account_set_id=account_set_id,
            summary=f"{account_set_id} 账套费用",
            amount=Decimal(amount),
            tax_amount=Decimal(tax_amount),
        )
    )
    return review_voucher(voucher.id, "财务主管")


def test_general_ledger_isolated_by_account_set():
    _seed_reviewed("default", "1000.00", "60.00")
    _seed_reviewed("cross_border", "2000.00", "120.00")

    default_ledger = build_general_ledger("2026-06", account_set_id="default")
    cross_border_ledger = build_general_ledger("2026-06", account_set_id="cross_border")

    assert default_ledger.voucher_count == 1
    assert default_ledger.total_debit == Decimal("1060.00")
    assert cross_border_ledger.voucher_count == 1
    assert cross_border_ledger.total_debit == Decimal("2120.00")


def test_close_period_rejects_unposted_vouchers():
    _seed_reviewed("default", "1000.00", "60.00")

    with pytest.raises(HTTPException) as exc_info:
        close_accounting_period("2026-06", "财务主管", account_set_id="default")

    assert exc_info.value.status_code == 409
    assert "未过账凭证" in exc_info.value.detail


def test_closed_period_only_blocks_same_account_set_posting():
    default_voucher = _seed_reviewed("default", "1000.00", "60.00")
    cross_border_voucher = _seed_reviewed("cross_border", "2000.00", "120.00")
    post_voucher(default_voucher.id, "财务主管")

    close_accounting_period("2026-06", "财务主管", account_set_id="default")
    posted = post_voucher(cross_border_voucher.id, "财务主管")

    assert posted.account_set_id == "cross_border"
    assert posted.posting_status == "posted"
    default_period = next(item for item in list_accounting_periods("default").periods if item.period == "2026-06")
    cross_border_period = next(item for item in list_accounting_periods("cross_border").periods if item.period == "2026-06")
    assert default_period.status == "closed"
    assert cross_border_period.status == "open"
