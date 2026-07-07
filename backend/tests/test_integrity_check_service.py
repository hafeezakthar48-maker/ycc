from decimal import Decimal

from app.models.accounting import JournalEntryCreate, JournalLineCreate
from app.models.accounting_archive import ArchiveDocumentCreate
from app.services.accounting_archive_service import create_archive_document, reset_accounting_archive_store
from app.services.accounting_period_service import reset_accounting_period_store
from app.services.accounting_service import post_journal_entry, reset_accounting_store
from app.services.integrity_check_service import run_accounting_integrity_checks
from app.services.statement_mapping_service import reset_statement_mapping_store


def setup_function():
    reset_accounting_store()
    reset_accounting_archive_store()
    reset_accounting_period_store()
    reset_statement_mapping_store()


def test_integrity_checks_cover_formal_accounting_governance_rules():
    entry = post_journal_entry(_balanced_entry())

    report = run_accounting_integrity_checks("default", "2026-06")

    assert report.account_set_id == "default"
    assert report.period == "2026-06"
    assert report.overall_status == "warning"
    checks_by_code = {check.check_code: check for check in report.checks}
    assert {
        "journal_entries_balanced",
        "duplicate_source_keys",
        "closed_period_unapproved_entries",
        "statement_mapping_coverage",
        "attachment_archive_links",
    }.issubset(checks_by_code)
    assert checks_by_code["journal_entries_balanced"].status == "pass"
    assert checks_by_code["journal_entries_balanced"].affected_count == 1
    assert checks_by_code["duplicate_source_keys"].status == "pass"
    assert checks_by_code["statement_mapping_coverage"].status == "pass"
    assert checks_by_code["attachment_archive_links"].status == "warning"
    assert entry.id in checks_by_code["attachment_archive_links"].evidence[0]


def test_archive_links_pass_when_journal_entry_attachment_exists():
    entry = post_journal_entry(_balanced_entry("voucher-with-archive"))
    create_archive_document(
        ArchiveDocumentCreate(
            account_set_id="default",
            period="2026-06",
            source_type="journal_entry",
            source_id=entry.id,
            document_type="voucher_attachment",
            filename="voucher-with-archive.txt",
            content_type="text/plain",
            content_bytes=b"voucher attachment",
            extracted_text="voucher attachment",
            uploaded_by="finance-manager",
        )
    )

    report = run_accounting_integrity_checks("default", "2026-06")

    archive_check = next(check for check in report.checks if check.check_code == "attachment_archive_links")
    assert archive_check.status == "pass"
    assert archive_check.affected_count == 1


def _balanced_entry(source_id="voucher-1"):
    return JournalEntryCreate(
        account_set_id="default",
        entry_date="2026-06-18",
        source_type="voucher_center",
        source_id=source_id,
        description="费用采购正式过账",
        created_by="财务主管",
        posted_by="财务主管",
        lines=[
            JournalLineCreate(
                account_code="6602",
                account_name="管理费用",
                direction="debit",
                original_amount=Decimal("100.00"),
                base_amount=Decimal("100.00"),
                description="费用",
            ),
            JournalLineCreate(
                account_code="2202",
                account_name="应付账款",
                direction="credit",
                original_amount=Decimal("100.00"),
                base_amount=Decimal("100.00"),
                description="应付",
            ),
        ],
    )
