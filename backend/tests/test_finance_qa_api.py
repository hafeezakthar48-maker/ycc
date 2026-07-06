from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_finance_qa_endpoint_returns_answer_with_citations():
    response = client.post(
        "/api/v1/finance-qa/ask",
        json={"question": "固定资产折旧需要注意哪些会计处理？"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "fixed_asset"
    assert payload["answer"]
    assert payload["citations"]
    assert payload["citations"][0]["authority"] in {"财政部", "国务院", "国家税务总局"}
    assert payload["requires_human_review"] is True
