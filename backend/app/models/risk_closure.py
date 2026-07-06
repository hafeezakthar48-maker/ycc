from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.finance import RiskItem


RiskClosureStatus = Literal["open", "assigned", "processing", "resolved", "closed"]
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"
MONTH_PATTERN = r"^\d{4}-\d{2}$"


class RiskProcessRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    handler: str
    action: str
    note: str
    created_at: str


class RiskReviewRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    reviewer: str
    conclusion: str
    created_at: str


class RiskClosureItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: str = Field(pattern=MONTH_PATTERN)
    risk: RiskItem
    status: RiskClosureStatus
    owner: str | None = None
    due_date: str | None = Field(default=None, pattern=DATE_PATTERN)
    process_records: list[RiskProcessRecord] = Field(default_factory=list)
    review_records: list[RiskReviewRecord] = Field(default_factory=list)


class RiskClosureListResponse(BaseModel):
    period: str
    total: int
    open_count: int
    closed_count: int
    items: list[RiskClosureItem]


class RiskAssignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: str = Field(pattern=MONTH_PATTERN)
    owner: str = Field(min_length=1, max_length=60)
    due_date: str = Field(pattern=DATE_PATTERN)
    note: str = Field(default="", max_length=400)


class RiskProcessRecordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: str = Field(pattern=MONTH_PATTERN)
    handler: str = Field(min_length=1, max_length=60)
    action: str = Field(min_length=1, max_length=120)
    note: str = Field(min_length=1, max_length=800)
    next_status: Literal["assigned", "processing", "resolved"] = "processing"


class RiskReviewRecordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: str = Field(pattern=MONTH_PATTERN)
    reviewer: str = Field(min_length=1, max_length=60)
    conclusion: str = Field(min_length=1, max_length=800)
    next_status: Literal["processing", "resolved", "closed"] = "closed"
