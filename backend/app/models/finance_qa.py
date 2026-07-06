from pydantic import BaseModel, Field


class FinanceQuestionRequest(BaseModel):
    question: str = Field(min_length=2)


class FinanceCitation(BaseModel):
    title: str
    authority: str
    document_number: str | None = None
    published_date: str
    status: str
    source_url: str
    updated_at: str


class FinanceQuestionResponse(BaseModel):
    question: str
    intent: str
    answer: str
    confidence: float = Field(ge=0, le=1)
    action_items: list[str]
    citations: list[FinanceCitation]
    risk_level: str
    requires_human_review: bool = True
    latest_policy_check_required: bool = True
