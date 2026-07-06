from decimal import Decimal
from typing import Literal

from app.models.audit import AuditResponse
from pydantic import BaseModel, ConfigDict, Field


DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


class VoucherCenterLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_code: str = Field(min_length=1, max_length=32)
    account_name: str = Field(min_length=1, max_length=80)
    direction: Literal["借", "贷"]
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    explanation: str = Field(default="", max_length=200)


class VoucherAttachment(BaseModel):
    id: str
    filename: str
    content_type: str
    size: int
    ocr_status: str
    archive_document_id: str | None = None
    sha256_hash: str | None = None
    storage_status: str = "metadata_only"


class VoucherCenterCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    voucher_date: str = Field(pattern=DATE_PATTERN)
    summary: str = Field(min_length=1, max_length=200)
    counterparty: str = Field(min_length=1, max_length=120)
    invoice_number: str | None = Field(default=None, max_length=40)
    amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    tax_amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    total_amount_with_tax: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    lines: list[VoucherCenterLine] = Field(min_length=1, max_length=50)


class VoucherCenterRecord(BaseModel):
    id: str
    account_set_id: str = "default"
    voucher_number: str
    voucher_date: str
    summary: str
    counterparty: str
    invoice_number: str | None = None
    amount: Decimal
    tax_amount: Decimal
    total_amount_with_tax: Decimal
    lines: list[VoucherCenterLine]
    status: str
    reviewed_by: str | None = None
    posting_status: Literal["unposted", "posted"] = "unposted"
    posted_by: str | None = None
    posted_at: str | None = None
    journal_entry_id: str | None = None
    journal_reversal_entry_id: str | None = None
    audit_result: AuditResponse | None = None
    attachments: list[VoucherAttachment] = Field(default_factory=list)


class VoucherCenterListResponse(BaseModel):
    total: int
    vouchers: list[VoucherCenterRecord]


class VoucherCenterImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vouchers: list[VoucherCenterCreateRequest] = Field(min_length=1, max_length=200)


class VoucherCenterImportResponse(BaseModel):
    imported_count: int
    vouchers: list[VoucherCenterRecord]


class VoucherReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewer: str = Field(default="财务主管", min_length=1, max_length=60)


class VoucherPostingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator: str = Field(default="财务主管", min_length=1, max_length=60)
