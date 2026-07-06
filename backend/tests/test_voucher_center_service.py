from decimal import Decimal

from app.models.voucher_center import VoucherCenterCreateRequest, VoucherCenterImportRequest, VoucherCenterLine
from app.services.accounting_archive_service import get_archive_document, reset_accounting_archive_store
from app.services.voucher_center_service import (
    attach_voucher_file,
    create_voucher,
    export_vouchers_csv,
    import_vouchers,
    list_vouchers,
    reset_voucher_store,
    review_voucher,
    unreview_voucher,
    update_voucher,
)


def _lines() -> list[VoucherCenterLine]:
    return [
        VoucherCenterLine(account_code="6602", account_name="管理费用", direction="借", amount=Decimal("1000.00"), explanation="办公服务费"),
        VoucherCenterLine(account_code="22210101", account_name="应交税费-应交增值税（进项税额）", direction="借", amount=Decimal("60.00"), explanation="进项税额"),
        VoucherCenterLine(account_code="2202", account_name="应付账款", direction="贷", amount=Decimal("1060.00"), explanation="应付未付款"),
    ]


def _request(summary: str = "办公服务费") -> VoucherCenterCreateRequest:
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


def test_create_voucher_generates_number_and_ai_audit_result():
    reset_voucher_store()

    voucher = create_voucher(_request())

    assert voucher.voucher_number == "记-202606-0001"
    assert voucher.status == "draft"
    assert voucher.audit_result is not None
    assert voucher.audit_result.rating == "通过"
    assert list_vouchers().total == 1


def test_update_review_and_unreview_voucher_state_flow():
    reset_voucher_store()
    voucher = create_voucher(_request())

    updated = update_voucher(voucher.id, _request(summary="办公服务费-已修改"))
    assert updated.summary == "办公服务费-已修改"
    reviewed = review_voucher(voucher.id, reviewer="财务主管")
    assert reviewed.status == "reviewed"
    assert reviewed.reviewed_by == "财务主管"
    unreviewed = unreview_voucher(voucher.id)
    assert unreviewed.status == "draft"
    assert unreviewed.reviewed_by is None


def test_import_export_and_attachment_record():
    reset_voucher_store()
    reset_accounting_archive_store()

    imported = import_vouchers(VoucherCenterImportRequest(vouchers=[_request("导入凭证一"), _request("导入凭证二")]))
    assert imported.imported_count == 2
    assert imported.vouchers[1].voucher_number == "记-202606-0002"

    attached = attach_voucher_file(
        imported.vouchers[0].id,
        filename="invoice.txt",
        content_type="text/plain",
        size=12,
        content_bytes=b"invoice text",
        uploaded_by="finance-user",
    )
    attachment = attached.attachments[0]
    document = get_archive_document(attachment.archive_document_id)

    assert attachment.filename == "invoice.txt"
    assert attachment.ocr_status == "text_parsed"
    assert attachment.sha256_hash == document.sha256_hash
    assert attachment.storage_status == "metadata_only"
    assert document.source_type == "voucher"
    assert document.source_id == imported.vouchers[0].id

    csv_text = export_vouchers_csv()
    assert "voucher_number,status,voucher_date,summary" in csv_text
    assert "记-202606-0001" in csv_text
    assert "导入凭证二" in csv_text
