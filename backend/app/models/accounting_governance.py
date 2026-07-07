from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CheckStatus = Literal["pass", "fail", "warning"]


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
