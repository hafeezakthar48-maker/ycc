from app.models.accounting_archive import ArchiveDocumentCreate
from app.services.accounting_archive_service import (
    create_archive_document,
    get_archive_document,
    list_archive_documents,
    reset_accounting_archive_store,
)


def setup_function():
    reset_accounting_archive_store()


def test_create_archive_document_calculates_hash_and_retention():
    document = create_archive_document(
        ArchiveDocumentCreate(
            account_set_id="default",
            period="2026-06",
            source_type="voucher",
            source_id="voucher-001",
            document_type="invoice",
            filename="invoice.txt",
            content_type="text/plain",
            content_bytes=b"invoice text",
            extracted_text="invoice text",
            uploaded_by="finance-user",
        )
    )

    loaded = get_archive_document(document.archive_document_id)
    listed = list_archive_documents(account_set_id="default", period="2026-06")

    assert document.sha256_hash == "9adcc70a5f32964ef54c16a3f3e2138f3bfe85e88b12402b248e8f28a1b2a884"
    assert document.retention_years == 30
    assert document.storage_status == "metadata_only"
    assert document.ocr_status == "text_parsed"
    assert document.verification_status == "pending_external"
    assert loaded.archive_document_id == document.archive_document_id
    assert listed.total == 1
