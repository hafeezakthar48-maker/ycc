from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.fixed_asset_service import reset_fixed_asset_store
from app.services.system_admin_service import reset_system_admin_store


client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_fixed_asset_api():
    reset_fixed_asset_store()
    reset_system_admin_store()


def _asset_payload(name: str = "自动贴标机", account_set_id: str = "default"):
    return {
        "account_set_id": account_set_id,
        "name": name,
        "category": "生产设备",
        "acquisition_date": "2026-01-15",
        "original_cost": "120000.00",
        "salvage_value": "12000.00",
        "useful_life_months": 60,
        "location": "一号仓",
        "custodian": "设备管理员",
    }


def _create_asset(name: str = "自动贴标机", account_set_id: str = "default"):
    response = client.post(
        "/api/v1/fixed-assets",
        headers={"X-Actor-Id": "u-finance-manager"},
        json=_asset_payload(name=name, account_set_id=account_set_id),
    )
    assert response.status_code == 200
    return response.json()


def test_fixed_asset_api_creates_lists_and_runs_depreciation_with_audit_logs():
    asset = _create_asset()

    list_response = client.get(
        "/api/v1/fixed-assets?account_set_id=default",
        headers={"X-Actor-Id": "u-finance-manager"},
    )
    depreciation_response = client.post(
        "/api/v1/fixed-assets/depreciation/run",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={"account_set_id": "default", "period": "2026-06", "operator": "财务主管"},
    )

    assert asset["asset_code"].startswith("FA-202601-")
    assert list_response.status_code == 200
    assert list_response.json()["summary"]["asset_count"] == 1
    assert depreciation_response.status_code == 200
    assert depreciation_response.json()["depreciated_count"] == 1
    assert Decimal(str(depreciation_response.json()["total_depreciation"])) == Decimal("1800.00")

    logs_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=10")
    events = [log["event"] for log in logs_response.json()["logs"] if log["event"].startswith("fixed_asset.")]
    assert events[:3] == [
        "fixed_asset.depreciation.run",
        "fixed_asset.list",
        "fixed_asset.create",
    ]
    depreciation_log = next(log for log in logs_response.json()["logs"] if log["event"] == "fixed_asset.depreciation.run")
    assert depreciation_log["metadata"]["account_set_id"] == "default"
    assert depreciation_log["metadata"]["period"] == "2026-06"
    assert depreciation_log["metadata"]["depreciated_count"] == 1


def test_fixed_asset_api_supports_inventory_dispose_and_sale():
    inventory_asset = _create_asset("盘点设备")
    sale_asset = _create_asset("出售设备")

    inventory_response = client.post(
        f"/api/v1/fixed-assets/{inventory_asset['id']}/inventory",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={
            "inventory_date": "2026-06-30",
            "location": "二号仓",
            "custodian": "资产专员",
            "condition": "正常",
            "operator": "盘点员",
            "note": "已贴标签",
        },
    )
    dispose_response = client.post(
        f"/api/v1/fixed-assets/{inventory_asset['id']}/dispose",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={"disposal_date": "2026-06-30", "reason": "损坏报废", "operator": "财务主管"},
    )
    sale_response = client.post(
        f"/api/v1/fixed-assets/{sale_asset['id']}/sell",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={"sale_date": "2026-06-30", "sale_amount": "118000.00", "reason": "更新换代", "operator": "财务主管"},
    )

    assert inventory_response.status_code == 200
    assert inventory_response.json()["inventory_status"] == "checked"
    assert inventory_response.json()["last_inventory_by"] == "盘点员"
    assert dispose_response.status_code == 200
    assert dispose_response.json()["status"] == "disposed"
    assert sale_response.status_code == 200
    assert sale_response.json()["status"] == "sold"
    assert Decimal(str(sale_response.json()["sale_gain_or_loss"])) == Decimal("-2000.00")


def test_fixed_asset_write_rejects_unauthorized_actor_and_records_denied_audit():
    response = client.post(
        "/api/v1/fixed-assets",
        headers={"X-Actor-Id": "u-auditor"},
        json=_asset_payload(),
    )

    assert response.status_code == 403
    assert "权限不足" in response.json()["detail"]

    logs_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=5")
    log = logs_response.json()["logs"][0]
    assert log["actor_id"] == "u-auditor"
    assert log["event"] == "fixed_asset.create"
    assert log["result"] == "denied"
    assert log["metadata"]["permission_code"] == "fixed_asset.write"


def test_finance_center_registry_declares_fixed_asset_api():
    response = client.get("/api/v1/modules/finance-center")

    assert response.status_code == 200
    module = response.json()
    assert "/api/v1/fixed-assets" in module["api_prefixes"]
    assert "fixed_asset.depreciation.run" in module["audit_events"]
