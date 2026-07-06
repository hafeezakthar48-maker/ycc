from decimal import Decimal
from importlib import reload

import app.services.voucher_center_service as voucher_service
from app.models.voucher_center import VoucherCenterCreateRequest, VoucherCenterLine


def _lines() -> list[VoucherCenterLine]:
    return [
        VoucherCenterLine(account_code="6602", account_name="管理费用", direction="借", amount=Decimal("1000.00"), explanation="办公服务费"),
        VoucherCenterLine(account_code="22210101", account_name="应交税费-应交增值税（进项税额）", direction="借", amount=Decimal("60.00"), explanation="进项税额"),
        VoucherCenterLine(account_code="2202", account_name="应付账款", direction="贷", amount=Decimal("1060.00"), explanation="应付未付款"),
    ]


def _request(summary: str = "持久化凭证") -> VoucherCenterCreateRequest:
    return VoucherCenterCreateRequest(
        voucher_date="2026-06-30",
        summary=summary,
        counterparty="上海云智科技有限公司",
        invoice_number="12345678",
        amount=Decimal("1000.00"),
        tax_amount=Decimal("60.00"),
        total_amount_with_tax=Decimal("1060.00"),
        lines=_lines(),
    )


def test_voucher_center_persists_records_after_service_reload(tmp_path, monkeypatch):
    db_path = tmp_path / "voucher-center.sqlite"
    monkeypatch.setenv("FINANCE_AI_VOUCHER_DB_PATH", str(db_path))

    service = reload(voucher_service)
    service.reset_voucher_store()

    created = service.create_voucher(_request())
    reviewed = service.review_voucher(created.id, "财务主管")
    attached = service.attach_voucher_file(reviewed.id, "invoice.txt", "text/plain", 128)

    assert attached.voucher_number == "记-202606-0001"
    assert db_path.exists()

    reloaded_service = reload(service)
    listed = reloaded_service.list_vouchers()

    assert listed.total == 1
    persisted = listed.vouchers[0]
    assert persisted.id == created.id
    assert persisted.status == "reviewed"
    assert persisted.reviewed_by == "财务主管"
    assert persisted.attachments[0].filename == "invoice.txt"

    next_voucher = reloaded_service.create_voucher(_request("重载后新增"))
    assert next_voucher.voucher_number == "记-202606-0002"
