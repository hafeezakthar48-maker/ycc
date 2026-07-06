from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ArchiveSourceType = Literal["voucher", "journal_entry", "fixed_asset", "payroll", "statement_snapshot", "manual"]
ArchiveDocumentType = Literal[
    "invoice",
    "bank_receipt",
    "contract",
    "delivery_note",
    "voucher_attachment",
    "statement",
    "other",
]
ArchiveStatus = Literal["draft", "indexed", "archived", "locked"]
ArchiveStorageStatus = Literal["metadata_only", "stored"]
ArchiveOcrStatus = Literal["not_required", "text_parsed", "engine_required", "failed"]
ArchiveVerificationStatus = Literal["not_required", "pending_external", "verified", "failed"]
ArchiveCaseType = Literal["voucher", "ledger", "statement", "mixed"]


class ArchiveDocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = "default"
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    source_type: ArchiveSourceType
    source_id: str
    document_type: ArchiveDocumentType
    filename: str
    content_type: str
    content_bytes: bytes
    extracted_text: str = ""
    uploaded_by: str
    storage_uri: str | None = None


class ArchiveDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    archive_document_id: str
    account_set_id: str
    period: str
    source_type: ArchiveSourceType
    source_id: str
    document_type: ArchiveDocumentType
    filename: str
    content_type: str
    size: int
    sha256_hash: str
    storage_status: ArchiveStorageStatus
    storage_uri: str | None = None
    archive_status: ArchiveStatus = "indexed"
    ocr_status: ArchiveOcrStatus
    verification_status: ArchiveVerificationStatus
    retention_years: int
    extracted_text: str = ""
    uploaded_by: str
    created_at: str


class ArchiveDocumentListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int
    documents: list[ArchiveDocument]


class ArchiveCaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = "default"
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    case_type: ArchiveCaseType
    title: str
    document_ids: list[str] = Field(min_length=1, max_length=500)
    created_by: str


class ArchiveCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    archive_case_id: str
    account_set_id: str
    period: str
    case_type: ArchiveCaseType
    title: str
    document_ids: list[str]
    document_count: int
    archive_status: ArchiveStatus = "archived"
    retention_years: int
    created_by: str
    created_at: str


class ArchivePackagePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    archive_case_id: str
    filename: str
    content_type: str
    content: bytes
