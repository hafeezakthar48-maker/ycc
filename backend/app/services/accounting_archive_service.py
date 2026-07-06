from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from app.models.accounting_archive import (
    ArchiveCase,
    ArchiveCaseCreate,
    ArchiveDocument,
    ArchiveDocumentCreate,
    ArchiveDocumentListResponse,
    ArchivePackagePayload,
)


_ARCHIVE_DOCUMENTS: dict[str, ArchiveDocument] = {}
_ARCHIVE_CASES: dict[str, ArchiveCase] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def reset_accounting_archive_store() -> None:
    _ARCHIVE_DOCUMENTS.clear()
    _ARCHIVE_CASES.clear()


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


def create_archive_case(payload: ArchiveCaseCreate) -> ArchiveCase:
    for document_id in payload.document_ids:
        get_archive_document(document_id)
    archive_case = ArchiveCase(
        archive_case_id=f"arch_case_{uuid4().hex}",
        account_set_id=payload.account_set_id,
        period=payload.period,
        case_type=payload.case_type,
        title=payload.title,
        document_ids=payload.document_ids,
        document_count=len(payload.document_ids),
        retention_years=30,
        created_by=payload.created_by,
        created_at=_now_iso(),
    )
    _ARCHIVE_CASES[archive_case.archive_case_id] = archive_case
    return archive_case


def get_archive_case(archive_case_id: str) -> ArchiveCase:
    archive_case = _ARCHIVE_CASES.get(archive_case_id)
    if archive_case is None:
        raise ValueError(f"未找到会计档案案卷 {archive_case_id}")
    return archive_case


def build_archive_package(archive_case_id: str) -> ArchivePackagePayload:
    archive_case = get_archive_case(archive_case_id)
    documents = [get_archive_document(document_id) for document_id in archive_case.document_ids]
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as package:
        package.writestr("manifest.json", _manifest_json(archive_case, documents))
        for document in documents:
            package.writestr(
                f"documents/{document.archive_document_id}.json",
                document.model_dump_json(indent=2),
            )
            if document.extracted_text:
                package.writestr(f"text/{document.archive_document_id}.txt", document.extracted_text)
    return ArchivePackagePayload(
        archive_case_id=archive_case.archive_case_id,
        filename=f"accounting-archive-{archive_case.account_set_id}-{archive_case.period}-{archive_case.case_type}.zip",
        content_type="application/zip",
        content=output.getvalue(),
    )


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


def _manifest_json(archive_case: ArchiveCase, documents: list[ArchiveDocument]) -> str:
    payload = {
        "archive_case_id": archive_case.archive_case_id,
        "account_set_id": archive_case.account_set_id,
        "period": archive_case.period,
        "case_type": archive_case.case_type,
        "title": archive_case.title,
        "document_count": archive_case.document_count,
        "retention_years": archive_case.retention_years,
        "documents": [
            {
                "archive_document_id": document.archive_document_id,
                "filename": document.filename,
                "sha256_hash": document.sha256_hash,
                "source_type": document.source_type,
                "source_id": document.source_id,
                "ocr_status": document.ocr_status,
                "verification_status": document.verification_status,
            }
            for document in documents
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
