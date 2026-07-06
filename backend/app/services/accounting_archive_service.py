from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import uuid4

from app.models.accounting_archive import (
    ArchiveDocument,
    ArchiveDocumentCreate,
    ArchiveDocumentListResponse,
)


_ARCHIVE_DOCUMENTS: dict[str, ArchiveDocument] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def reset_accounting_archive_store() -> None:
    _ARCHIVE_DOCUMENTS.clear()


def create_archive_document(payload: ArchiveDocumentCreate) -> ArchiveDocument:
    sha256_hash = hashlib.sha256(payload.content_bytes).hexdigest()
    document = ArchiveDocument(
        archive_document_id=f"arch_doc_{uuid4().hex}",
        account_set_id=payload.account_set_id,
        period=payload.period,
        source_type=payload.source_type,
        source_id=payload.source_id,
        document_type=payload.document_type,
        filename=payload.filename,
        content_type=payload.content_type,
        size=len(payload.content_bytes),
        sha256_hash=sha256_hash,
        storage_status="stored" if payload.storage_uri else "metadata_only",
        storage_uri=payload.storage_uri,
        ocr_status=_ocr_status(payload.filename, payload.content_type, payload.extracted_text),
        verification_status=_verification_status(payload.document_type),
        retention_years=_retention_years(payload.document_type),
        extracted_text=payload.extracted_text,
        uploaded_by=payload.uploaded_by,
        created_at=_now_iso(),
    )
    _ARCHIVE_DOCUMENTS[document.archive_document_id] = document
    return document


def get_archive_document(archive_document_id: str) -> ArchiveDocument:
    document = _ARCHIVE_DOCUMENTS.get(archive_document_id)
    if document is None:
        raise ValueError(f"未找到会计档案文档 {archive_document_id}")
    return document


def list_archive_documents(account_set_id: str, period: str | None = None) -> ArchiveDocumentListResponse:
    documents = [
        document
        for document in _ARCHIVE_DOCUMENTS.values()
        if document.account_set_id == account_set_id and (period is None or document.period == period)
    ]
    documents.sort(key=lambda item: item.created_at, reverse=True)
    return ArchiveDocumentListResponse(total=len(documents), documents=documents)


def _ocr_status(filename: str, content_type: str, extracted_text: str) -> str:
    if extracted_text:
        return "text_parsed"
    if filename.lower().endswith(".txt") or content_type.startswith("text/"):
        return "text_parsed"
    if content_type.startswith("image/") or content_type == "application/pdf":
        return "engine_required"
    return "not_required"


def _verification_status(document_type: str) -> str:
    if document_type in {"invoice", "bank_receipt"}:
        return "pending_external"
    return "not_required"


def _retention_years(document_type: str) -> int:
    if document_type in {"invoice", "bank_receipt", "contract", "voucher_attachment", "statement"}:
        return 30
    return 10
