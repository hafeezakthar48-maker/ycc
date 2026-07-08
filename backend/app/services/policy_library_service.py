import re

from app.data.policy_documents import POLICY_DOCUMENTS
from app.models.policy import PolicyDocument, PolicySearchRequest, PolicySearchResponse, PolicySearchResult


def search_policy_documents(request: PolicySearchRequest) -> PolicySearchResponse:
    query_terms = _tokenize(request.query)
    scored: list[PolicySearchResult] = []

    for document in _get_policy_documents():
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
    return next((document for document in _get_policy_documents() if document.id == policy_id), None)


def _tokenize(query: str) -> list[str]:
    normalized_query = query.lower()
    tokens = [part.strip().lower() for part in re.split(r"[\s,，。；;、？?]+", query) if part.strip()]
    registered_keywords = [
        keyword.lower()
        for document in _get_policy_documents()
        for keyword in document.keywords
        if keyword.lower() in normalized_query
    ]
    unique_tokens = list(dict.fromkeys([*tokens, *registered_keywords]))
    if unique_tokens:
        return unique_tokens
    return [normalized_query]


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


def _get_policy_documents() -> tuple[PolicyDocument, ...]:
    from app.services.update_center_service import load_installed_policy_documents

    documents_by_id = {document.id: document for document in POLICY_DOCUMENTS}
    for document in load_installed_policy_documents():
        documents_by_id[document.id] = document
    return tuple(documents_by_id.values())
