from decimal import Decimal
from importlib import reload

import app.services.voucher_center_service as voucher_service
from app.models.voucher_center import VoucherCenterCreateRequest, VoucherCenterLine
from app.services.accounting_archive_service import get_archive_document, reset_accounting_archive_store


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
    reset_accounting_archive_store()

    created = service.create_voucher(_request())
    reviewed = service.review_voucher(created.id, "财务主管")
    attached = service.attach_voucher_file(
        reviewed.id,
        "invoice.txt",
        "text/plain",
        12,
        content_bytes=b"invoice text",
        uploaded_by="finance-user",
    )
    attachment = attached.attachments[0]
    document = get_archive_document(attachment.archive_document_id)

    assert attached.voucher_number == "记-202606-0001"
    assert attachment.sha256_hash == document.sha256_hash
    assert attachment.storage_status == "metadata_only"
    assert db_path.exists()

    reloaded_service = reload(service)
    listed = reloaded_service.list_vouchers()

    assert listed.total == 1
    persisted = listed.vouchers[0]
    assert persisted.id == created.id
    assert persisted.status == "reviewed"
    assert persisted.reviewed_by == "财务主管"
    assert persisted.attachments[0].filename == "invoice.txt"
    assert persisted.attachments[0].archive_document_id == attachment.archive_document_id
    assert persisted.attachments[0].sha256_hash == attachment.sha256_hash
    assert persisted.attachments[0].storage_status == "metadata_only"

    next_voucher = reloaded_service.create_voucher(_request("重载后新增"))
    assert next_voucher.voucher_number == "记-202606-0002"
