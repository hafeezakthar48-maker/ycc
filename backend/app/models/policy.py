from pydantic import BaseModel, Field


class PolicyDocument(BaseModel):
    id: str
    title: str
    authority: str
    document_number: str | None = None
    category: str
    published_date: str
    effective_date: str | None = None
    status: str
    source_url: str
    updated_at: str
    keywords: list[str]
    summary: str
    content: str


class PolicySearchRequest(BaseModel):
    query: str = Field(min_length=1)
    category: str | None = None
    limit: int = Field(default=5, ge=1, le=20)


class PolicySearchResult(BaseModel):
    document: PolicyDocument
    relevance_score: float
    snippets: list[str]


class PolicySearchResponse(BaseModel):
    query: str
    total: int
    results: list[PolicySearchResult]
    latest_policy_check_required: bool = True
