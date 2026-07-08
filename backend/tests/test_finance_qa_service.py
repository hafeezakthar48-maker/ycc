from app.models.finance_qa import FinanceQuestionRequest
from app.services.finance_qa_service import answer_finance_question


def test_answer_finance_question_returns_auditable_revenue_answer():
    response = answer_finance_question(
        FinanceQuestionRequest(question="电商平台订单已经发货，收入应该什么时候确认？")
    )

    assert response.intent == "revenue_recognition"
    assert response.confidence >= 0.7
    assert "收入确认" in response.answer
    assert response.citations
    assert response.citations[0].title == "企业会计准则第14号——收入"
    assert response.citations[0].published_date
    assert response.citations[0].status in {"现行有效", "需复核"}
    assert response.requires_human_review is True
    assert response.latest_policy_check_required is False
    assert response.action_items


def test_answer_finance_question_requires_review_for_unknown_policy_question():
    response = answer_finance_question(
        FinanceQuestionRequest(question="我们公司这个月能不能享受最新地方税收优惠？")
    )

    assert response.intent == "unknown"
    assert 0.3 <= response.confidence < 0.5
    assert response.requires_human_review is True
    assert response.latest_policy_check_required is True
    assert "本地法规库已匹配到基础法规卡片" in response.answer
    assert "不能据此判断最新地方优惠" in response.answer
    assert {citation.title for citation in response.citations} >= {"中华人民共和国企业所得税法"}
