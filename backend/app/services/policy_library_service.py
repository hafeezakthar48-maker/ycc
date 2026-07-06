import re

from app.data.policy_documents import POLICY_DOCUMENTS
from app.models.policy import PolicyDocument, PolicySearchRequest, PolicySearchResponse, PolicySearchResult


def search_policy_documents(request: PolicySearchRequest) -> PolicySearchResponse:
    query_terms = _tokenize(request.query)
    scored: list[PolicySearchResult] = []

    for document in POLICY_DOCUMENTS:
        if request.category and document.category != request.category:
            continue
        score = _score_document(document, query_terms)
        if score <= 0:
            continue
        scored.append(
            PolicySearchResult(
                document=document,
                relevance_score=round(score, 4),
                snippets=_build_snippets(document, query_terms),
            )
        )

    results = sorted(scored, key=lambda item: item.relevance_score, reverse=True)[: request.limit]
    return PolicySearchResponse(
        query=request.query,
        total=len(results),
        results=results,
        latest_policy_check_required=True,
    )


def find_policy_by_id(policy_id: str) -> PolicyDocument | None:
    return next((document for document in POLICY_DOCUMENTS if document.id == policy_id), None)


def _tokenize(query: str) -> list[str]:
    tokens = [part.strip().lower() for part in re.split(r"[\s,，。；;、]+", query) if part.strip()]
    if tokens:
        return tokens
    return [query.lower()]


def _score_document(document: PolicyDocument, query_terms: list[str]) -> float:
    title = document.title.lower()
    category = document.category.lower()
    keyword_text = " ".join(document.keywords).lower()
    summary = document.summary.lower()
    content = document.content.lower()
    score = 0.0

    for term in query_terms:
        if term in title:
            score += 4
        if term in keyword_text:
            score += 3
        if term in category:
            score += 1.5
        if term in summary:
            score += 1.2
        if term in content:
            score += 1

    return score


def _build_snippets(document: PolicyDocument, query_terms: list[str]) -> list[str]:
    candidates = [document.summary, document.content]
    snippets: list[str] = []
    for text in candidates:
        lowered = text.lower()
        if any(term in lowered for term in query_terms):
            snippets.append(_trim_snippet(text))
    return snippets or [document.summary]


def _trim_snippet(text: str, max_length: int = 110) -> str:
    return text if len(text) <= max_length else f"{text[:max_length]}..."
