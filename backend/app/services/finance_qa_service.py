from app.data.finance_qa_knowledge import KNOWLEDGE_CARDS, FinanceKnowledgeCard
from app.models.finance_qa import FinanceCitation, FinanceQuestionRequest, FinanceQuestionResponse
from app.services.policy_library_service import find_policy_by_id


def answer_finance_question(request: FinanceQuestionRequest) -> FinanceQuestionResponse:
    card, confidence = _match_card(request.question)
    if not card:
        return FinanceQuestionResponse(
            question=request.question,
            intent="unknown",
            answer=(
                "未匹配到足够可靠的本地法规卡片。当前 MVP 不会编造法规、税率或地方优惠口径；"
                "请接入实时法规库后，再由财务或税务负责人复核。"
            ),
            confidence=confidence,
            action_items=[
                "补充企业所在地区、纳税人身份、行业、业务发生时间和交易资料。",
                "检索国家税务总局、财政部、地方税务局最新政策后再形成正式结论。",
            ],
            citations=[],
            risk_level="high",
            requires_human_review=True,
            latest_policy_check_required=True,
        )

    return FinanceQuestionResponse(
        question=request.question,
        intent=card.intent,
        answer=f"{card.answer} 本回答为 AI 初步判断，不替代企业正式会计政策或税务申报结论。",
        confidence=confidence,
        action_items=list(card.action_items),
        citations=_citations_from_policy_ids(card.policy_ids),
        risk_level=card.risk_level,
        requires_human_review=True,
        latest_policy_check_required=False,
    )


def _citations_from_policy_ids(policy_ids: tuple[str, ...]) -> list[FinanceCitation]:
    citations: list[FinanceCitation] = []
    for policy_id in policy_ids:
        document = find_policy_by_id(policy_id)
        if not document:
            continue
        citations.append(
            FinanceCitation(
                title=document.title,
                authority=document.authority,
                document_number=document.document_number,
                published_date=document.published_date,
                status=document.status,
                source_url=document.source_url,
                updated_at=document.updated_at,
            )
        )
    return citations


def _match_card(question: str) -> tuple[FinanceKnowledgeCard | None, float]:
    normalized = question.lower()
    best_card: FinanceKnowledgeCard | None = None
    best_score = 0

    for card in KNOWLEDGE_CARDS:
        score = sum(1 for keyword in card.keywords if keyword.lower() in normalized)
        if score > best_score:
            best_card = card
            best_score = score

    if not best_card or best_score == 0:
        return None, 0.2

    confidence = min(0.92, 0.58 + best_score * 0.09)
    return best_card, confidence
