from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CheckStatus = Literal["pass", "fail", "warning"]
MigrationItemStatus = Literal["ready", "already_migrated", "blocked"]


class AccountingIntegrityCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_code: str
    check_name: str
    status: CheckStatus
    severity: Literal["blocking", "warning", "info"]
    message: str
    affected_count: int = Field(default=0, ge=0)
    evidence: list[str] = Field(default_factory=list)


class AccountingIntegrityReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str
    period: str
    overall_status: CheckStatus
    generated_at: str
    checks: list[AccountingIntegrityCheck]


class AccountingMigrationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    voucher_id: str
    voucher_number: str
    voucher_date: str
    summary: str
    status: MigrationItemStatus
    reason_code: str | None = None
    reason: str = ""
    debit_total: Decimal
    credit_total: Decimal
    difference: Decimal
    formal_journal_entry_id: str | None = None


class AccountingMigrationPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str
    period: str
    mode: Literal["dry_run"] = "dry_run"
    actor_id: str = "system"
    migration_type: Literal["mvp_voucher_to_formal_journal"] = "mvp_voucher_to_formal_journal"
    generated_at: str
    total_count: int = Field(ge=0)
    ready_count: int = Field(ge=0)
    migrated_count: int = Field(ge=0)
    blocked_count: int = Field(ge=0)
    proposed_entry_count: int = Field(ge=0)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    items: list[AccountingMigrationItem]


class AccountingMigrationApplyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_id: str
    account_set_id: str
    period: str
    actor_id: str
    backup_manifest_id: str
    applied_at: str
    applied_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    blocked_count: int = Field(ge=0)
    journal_entry_ids: list[str] = Field(default_factory=list)
    preview: AccountingMigrationPreview
