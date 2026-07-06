from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from app.models.fixed_asset import FixedAssetCreateRequest
from app.services.accounting_period_service import reset_accounting_period_store
from app.services.accounting_service import reset_accounting_store
from app.services.fixed_asset_accounting_service import reset_fixed_asset_accounting_store
from app.services.fixed_asset_service import create_fixed_asset, reset_fixed_asset_store
from app.services.system_admin_service import reset_system_admin_store
from app.services.voucher_center_service import reset_voucher_store


client = TestClient(app)


def setup_function():
    reset_voucher_store()
    reset_accounting_store()
    reset_accounting_period_store()
    reset_fixed_asset_store()
    reset_fixed_asset_accounting_store()
    reset_system_admin_store()


def test_fixed_asset_accounting_api_runs_formal_lifecycle_and_reads_cards():
    asset = _create_asset()

    capitalize_response = client.post(
        "/api/v1/fixed-asset-accounting/capitalize",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={"account_set_id": "default", "asset_id": asset.id, "period": "2026-01", "credit_account_code": "2202"},
    )
    depreciation_response = client.post(
        "/api/v1/fixed-asset-accounting/depreciation",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={"account_set_id": "default", "period": "2026-06"},
    )
    impairment_response = client.post(
        "/api/v1/fixed-asset-accounting/impairment",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={"account_set_id": "default", "asset_id": asset.id, "period": "2026-06", "amount": "3000.00"},
    )
    disposal_response = client.post(
        "/api/v1/fixed-asset-accounting/disposal",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={
            "account_set_id": "default",
            "asset_id": asset.id,
            "period": "2026-07",
            "proceeds_amount": "100000.00",
            "disposal_date": "2026-07-31",
        },
    )
    cards_response = client.get(
        "/api/v1/fixed-asset-accounting/cards",
        params={"account_set_id": "default"},
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert capitalize_response.status_code == 200
    assert capitalize_response.json()["source_type"] == "fixed_asset_capitalization"
    assert depreciation_response.status_code == 200
    assert depreciation_response.json()["depreciated_count"] == 1
    assert impairment_response.status_code == 200
    assert impairment_response.json()["source_type"] == "fixed_asset_impairment"
    assert disposal_response.status_code == 200
    assert Decimal(str(disposal_response.json()["disposal_gain_or_loss"])) == Decimal("-15200.00")
    assert cards_response.status_code == 200
    card = cards_response.json()["cards"][0]
    assert card["formal_accounting_status"] == "sold"
    assert card["impairment_amount"] == "3000.00"

    audit_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=10")
    events = [log["event"] for log in audit_response.json()["logs"]]
    assert "fixed_asset_accounting.disposal.post" in events
    assert "fixed_asset_accounting.impairment.post" in events
    assert "fixed_asset_accounting.depreciation.post" in events
    assert "fixed_asset_accounting.capitalize" in events


def test_fixed_asset_accounting_api_rejects_unauthorized_post_and_records_audit():
    asset = _create_asset()

    response = client.post(
        "/api/v1/fixed-asset-accounting/impairment",
        headers={"X-Actor-Id": "u-auditor"},
        json={"account_set_id": "default", "asset_id": asset.id, "period": "2026-06", "amount": "3000.00"},
    )

    assert response.status_code == 403
    audit_response = client.get(
        "/api/v1/system/audit-logs",
        params={"event": "fixed_asset_accounting.impairment.post", "actor_id": "u-auditor"},
    )
    log = audit_response.json()["logs"][0]
    assert log["result"] == "denied"
    assert log["metadata"]["permission_code"] == "fixed_asset_accounting.impair"


def _create_asset():
    return create_fixed_asset(
        FixedAssetCreateRequest(
            account_set_id="default",
            name="生产设备A",
            category="生产设备",
            acquisition_date="2026-01-15",
            original_cost=Decimal("120000.00"),
            salvage_value=Decimal("12000.00"),
            useful_life_months=60,
            location="一号车间",
            custodian="设备管理员",
        )
    )
