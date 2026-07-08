from app.models.policy import PolicySearchRequest
from app.services.policy_library_service import search_policy_documents


def test_search_policy_documents_returns_revenue_standard_with_source_metadata():
    response = search_policy_documents(PolicySearchRequest(query="电商收入确认 控制权", limit=5))

    assert response.total >= 1
    first = response.results[0]
    assert first.document.title == "企业会计准则第14号——收入"
    assert first.document.authority == "财政部"
    assert first.document.published_date == "2017-07-05"
    assert first.document.status == "现行有效"
    assert first.document.source_url.startswith("https://")
    assert first.snippets
    assert first.relevance_score > 0


def test_search_policy_documents_returns_invoice_policy_for_invoice_risk():
    response = search_policy_documents(PolicySearchRequest(query="电子发票 虚开 抵扣 风险", limit=5))

    titles = {result.document.title for result in response.results}
    assert "中华人民共和国发票管理办法" in titles
    assert response.latest_policy_check_required is True


def test_search_policy_documents_extracts_registered_keywords_from_chinese_sentence():
    response = search_policy_documents(
        PolicySearchRequest(query="我们公司这个月能不能享受最新地方税收优惠？", limit=5)
    )

    titles = {result.document.title for result in response.results}
    assert "中华人民共和国企业所得税法" in titles
    assert response.latest_policy_check_required is True
