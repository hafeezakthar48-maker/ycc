from fastapi.testclient import TestClient

from app.main import app
from app.services.risk_closure_service import reset_risk_closure_store


client = TestClient(app)


def test_risk_closure_list_starts_from_detected_risks():
    reset_risk_closure_store()

    response = client.get("/api/v1/risks/closures?period=2026-06")

    assert response.status_code == 200
    payload = response.json()
    assert payload["period"] == "2026-06"
    assert payload["total"] >= 1
    assert payload["open_count"] == payload["total"]
    assert payload["closed_count"] == 0

    item = payload["items"][0]
    assert item["risk"]["id"]
    assert item["status"] == "open"
    assert item["owner"] is None
    assert item["process_records"] == []
    assert item["review_records"] == []


def test_risk_closure_assign_process_and_review_flow():
    reset_risk_closure_store()
    risk_id = "cash-profit-divergence"

    assign_response = client.post(
        f"/api/v1/risks/closures/{risk_id}/assign",
        json={
            "period": "2026-06",
            "owner": "财务主管",
            "due_date": "2026-07-10",
            "note": "先复核应收账款账龄与期后回款。",
        },
    )

    assert assign_response.status_code == 200
    assigned = assign_response.json()
    assert assigned["status"] == "assigned"
    assert assigned["owner"] == "财务主管"
    assert assigned["due_date"] == "2026-07-10"
    assert assigned["process_records"][0]["action"] == "assign"

    process_response = client.post(
        f"/api/v1/risks/closures/{risk_id}/process-records",
        json={
            "period": "2026-06",
            "handler": "财务主管",
            "action": "已复核账龄",
            "note": "发现两笔大额应收超过60天，已联系销售确认回款计划。",
            "next_status": "processing",
        },
    )

    assert process_response.status_code == 200
    processing = process_response.json()
    assert processing["status"] == "processing"
    assert len(processing["process_records"]) == 2
    assert processing["process_records"][-1]["handler"] == "财务主管"

    review_response = client.post(
        f"/api/v1/risks/closures/{risk_id}/review-records",
        json={
            "period": "2026-06",
            "reviewer": "内控复核员",
            "conclusion": "已确认回款计划和后续跟踪责任人，可以关闭。",
            "next_status": "closed",
        },
    )

    assert review_response.status_code == 200
    reviewed = review_response.json()
    assert reviewed["status"] == "closed"
    assert reviewed["review_records"][0]["reviewer"] == "内控复核员"

    list_response = client.get("/api/v1/risks/closures?period=2026-06&status=closed")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["closed_count"] == 1
    assert [item["risk"]["id"] for item in payload["items"]] == [risk_id]


def test_risk_closure_rejects_unknown_risk():
    reset_risk_closure_store()

    response = client.post(
        "/api/v1/risks/closures/not-exists/assign",
        json={"period": "2026-06", "owner": "财务主管", "due_date": "2026-07-10"},
    )

    assert response.status_code == 404
    assert "风险不存在" in response.json()["detail"]
