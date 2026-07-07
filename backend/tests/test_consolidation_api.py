from fastapi.testclient import TestClient

from app.main import app
from app.services.consolidation_service import reset_consolidation_store
from app.services.system_admin_service import reset_system_admin_store


client = TestClient(app)


def setup_function():
    reset_consolidation_store()
    reset_system_admin_store()


def test_consolidation_api_runs_group_elimination_and_statement_workflow():
    group_response = client.post(
        "/api/v1/consolidation/groups",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={
            "group_id": "group-001",
            "group_name": "中国财务AI集团",
            "entities": [
                {
                    "consolidation_group_id": "group-001",
                    "account_set_id": "default",
                    "entity_name": "母公司",
                    "ownership_percentage": "1.000000",
                    "consolidation_method": "full",
                },
                {
                    "consolidation_group_id": "group-001",
                    "account_set_id": "cross_border",
                    "entity_name": "子公司A",
                    "ownership_percentage": "0.800000",
                    "consolidation_method": "proportionate",
                },
            ],
        },
    )
    list_response = client.get(
        "/api/v1/consolidation/groups",
        headers={"X-Actor-Id": "u-finance-manager"},
    )
    package_response = client.get(
        "/api/v1/consolidation/reporting-package",
        params={"account_set_id": "default", "period": "2026-06"},
        headers={"X-Actor-Id": "u-finance-manager"},
    )
    rebuild_response = client.post(
        "/api/v1/consolidation/eliminations/rebuild",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={
            "group_id": "group-001",
            "period": "2026-06",
            "intercompany_balance_amount": "50000.00",
            "intercompany_revenue_amount": "80000.00",
            "intercompany_cost_amount": "60000.00",
            "ending_internal_inventory_amount": "100000.00",
            "internal_gross_margin_rate": "0.200000",
            "investment_amount": "800000.00",
            "subsidiary_equity_amount": "1000000.00",
            "ownership_percentage": "0.800000",
        },
    )
    eliminations_response = client.get(
        "/api/v1/consolidation/eliminations",
        params={"group_id": "group-001", "period": "2026-06"},
        headers={"X-Actor-Id": "u-finance-manager"},
    )
    statements_response = client.get(
        "/api/v1/consolidation/statements",
        params={"group_id": "group-001", "period": "2026-06"},
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert group_response.status_code == 200
    assert group_response.json()["group_id"] == "group-001"
    assert list_response.status_code == 200
    assert list_response.json()["total_groups"] == 1
    assert package_response.status_code == 200
    assert package_response.json()["balance_sheet"]["title"] == "资产负债表"
    assert rebuild_response.status_code == 200
    assert rebuild_response.json()["total_eliminations"] >= 4
    assert eliminations_response.status_code == 200
    elimination_types = {entry["elimination_type"] for entry in eliminations_response.json()["eliminations"]}
    assert {"intercompany_balance", "intercompany_revenue_cost", "unrealized_profit", "investment_equity"}.issubset(elimination_types)
    assert statements_response.status_code == 200
    assert statements_response.json()["group_id"] == "group-001"
    assert statements_response.json()["minority_interest"] == "200000.00"

    audit_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=20")
    events = [log["event"] for log in audit_response.json()["logs"]]
    assert "consolidation.group.write" in events
    assert "consolidation.group.read" in events
    assert "consolidation.package.read" in events
    assert "consolidation.elimination.rebuild" in events
    assert "consolidation.statement.read" in events


def test_consolidation_api_rejects_unauthorized_rebuild_and_records_audit():
    response = client.post(
        "/api/v1/consolidation/eliminations/rebuild",
        headers={"X-Actor-Id": "u-auditor"},
        json={"group_id": "group-001", "period": "2026-06"},
    )

    assert response.status_code == 403
    audit_response = client.get(
        "/api/v1/system/audit-logs",
        params={"event": "consolidation.elimination.rebuild", "actor_id": "u-auditor"},
    )
    log = audit_response.json()["logs"][0]
    assert log["result"] == "denied"
    assert log["metadata"]["permission_code"] == "consolidation.rebuild"
