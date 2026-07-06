from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.voucher_center import VoucherCenterCreateRequest, VoucherCenterLine
from app.services.voucher_center_service import (
    create_voucher,
    post_voucher,
    reset_voucher_store,
    review_voucher,
    unpost_voucher,
    unreview_voucher,
)


@pytest.fixture(autouse=True)
def isolated_voucher_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_VOUCHER_DB_PATH", str(tmp_path / "voucher-center.sqlite3"))
    reset_voucher_store()


def _request() -> VoucherCenterCreateRequest:
    return VoucherCenterCreateRequest(
        voucher_date="2026-06-30",
        summary="过账状态验证",
        counterparty="上海云智科技有限公司",
        invoice_number="POST-202606",
        amount=Decimal("1000.00"),
        tax_amount=Decimal("60.00"),
        total_amount_with_tax=Decimal("1060.00"),
        lines=[
            VoucherCenterLine(account_code="6602", account_name="管理费用", direction="借", amount=Decimal("1000.00"), explanation="办公服务费"),
            VoucherCenterLine(account_code="22210101", account_name="应交税费-应交增值税（进项税额）", direction="借", amount=Decimal("60.00"), explanation="进项税额"),
            VoucherCenterLine(account_code="2202", account_name="应付账款", direction="贷", amount=Decimal("1060.00"), explanation="应付未付款"),
        ],
    )


def test_reviewed_voucher_can_be_posted_and_unposted():
    voucher = create_voucher(_request())
    assert voucher.posting_status == "unposted"

    reviewed = review_voucher(voucher.id, "财务主管")
    posted = post_voucher(reviewed.id, "财务主管")

    assert posted.status == "reviewed"
    assert posted.posting_status == "posted"
    assert posted.posted_by == "财务主管"
    assert posted.posted_at is not None

    unposted = unpost_voucher(posted.id)
    assert unposted.status == "reviewed"
    assert unposted.posting_status == "unposted"
    assert unposted.posted_by is None
    assert unposted.posted_at is None


def test_draft_voucher_cannot_be_posted():
    voucher = create_voucher(_request())

    with pytest.raises(HTTPException) as exc_info:
        post_voucher(voucher.id, "财务主管")

    assert exc_info.value.status_code == 409
    assert "先审核" in exc_info.value.detail


def test_posted_voucher_cannot_be_unreviewed_until_unposted():
    voucher = create_voucher(_request())
    reviewed = review_voucher(voucher.id, "财务主管")
    posted = post_voucher(reviewed.id, "财务主管")

    with pytest.raises(HTTPException) as exc_info:
        unreview_voucher(posted.id)

    assert exc_info.value.status_code == 409
    assert "先反过账" in exc_info.value.detail

    unposted = unpost_voucher(posted.id)
    draft = unreview_voucher(unposted.id)
    assert draft.status == "draft"
    assert draft.posting_status == "unposted"
