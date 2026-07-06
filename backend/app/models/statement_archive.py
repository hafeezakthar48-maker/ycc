from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.financial_statement import FinancialStatementBundle


StatementArchiveStatus = Literal["draft", "locked", "archived", "demo_only"]
StatementValidationStatus = Literal["passed", "warning", "failed"]
StatementExportFormat = Literal["xlsx", "pdf"]


class StatementSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: str
    account_set_id: str
    period: str
    company_name: str
    version: int
    mapping_set_id: str
    source: str
    content_hash: str
    validation_status: StatementValidationStatus
    archive_status: StatementArchiveStatus
    locked: bool = False
    created_by: str
    created_at: str
    locked_by: str | None = None
    locked_at: str | None = None
    bundle: FinancialStatementBundle


class StatementSnapshotListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int
    items: list[StatementSnapshot]


class StatementSnapshotCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    account_set_id: str = "default"
    operator: str = "财务主管"
    created_by: str = "finance-user"


class StatementSnapshotLockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    locked_by: str = Field(min_length=1, max_length=64)


class StatementExportRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    export_id: str
    snapshot_id: str
    export_format: StatementExportFormat
    filename: str
    content_type: str
    exported_by: str
    exported_at: str
