from app.models.finance_qa import FinanceCitation
from pydantic import BaseModel, ConfigDict, Field


class InvoiceOcrRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=1024 * 1024)


class InvoiceField(BaseModel):
    key: str
    label: str
    value: str | None = None
    confidence: float = Field(ge=0, le=1)


class InvoiceRiskItem(BaseModel):
    id: str
    title: str
    level: int = Field(ge=1, le=5)
    description: str
    suggestion: str


class InvoiceOcrResponse(BaseModel):
    engine_status: str
    invoice_type: str | None = None
    fields: list[InvoiceField]
    risks: list[InvoiceRiskItem]
    warnings: list[str]
    citations: list[FinanceCitation]
