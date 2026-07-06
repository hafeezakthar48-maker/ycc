from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_policy_search_endpoint_returns_ranked_results():
    response = client.post("/api/v1/policies/search", json={"query": "固定资产 折旧", "limit": 3})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "固定资产 折旧"
    assert payload["total"] >= 1
    assert payload["results"][0]["document"]["title"] == "企业会计准则第4号——固定资产"
    assert payload["results"][0]["snippets"]
