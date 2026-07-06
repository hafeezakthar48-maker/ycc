from decimal import Decimal

import pytest

from app.models.fixed_asset import (
    FixedAssetCreateRequest,
    FixedAssetInventoryRequest,
    FixedAssetSaleRequest,
)
from app.services.fixed_asset_service import (
    create_fixed_asset,
    dispose_fixed_asset,
    get_period_depreciation_summary,
    inventory_fixed_asset,
    list_fixed_assets,
    reset_fixed_asset_store,
    run_monthly_depreciation,
    sell_fixed_asset,
)


@pytest.fixture(autouse=True)
def isolated_fixed_assets():
    reset_fixed_asset_store()


def _asset_request(
    *,
    account_set_id: str = "default",
    name: str = "自动贴标机",
    original_cost: str = "120000.00",
    salvage_value: str = "12000.00",
    useful_life_months: int = 60,
) -> FixedAssetCreateRequest:
    return FixedAssetCreateRequest(
        account_set_id=account_set_id,
        name=name,
        category="生产设备",
        acquisition_date="2026-01-15",
        original_cost=Decimal(original_cost),
        salvage_value=Decimal(salvage_value),
        useful_life_months=useful_life_months,
        location="一号仓",
        custodian="设备管理员",
    )


def test_create_asset_calculates_straight_line_depreciation_and_summary_by_account_set():
    default_asset = create_fixed_asset(_asset_request())
    create_fixed_asset(_asset_request(account_set_id="cross_border", name="跨境分拣机", original_cost="60000.00"))

    payload = list_fixed_assets("default")

    assert default_asset.asset_code.startswith("FA-202601-")
    assert default_asset.status == "active"
    assert default_asset.monthly_depreciation == Decimal("1800.00")
    assert default_asset.net_book_value == Decimal("120000.00")
    assert payload.summary.asset_count == 1
    assert payload.summary.active_count == 1
    assert payload.summary.original_cost_total == Decimal("120000.00")
    assert payload.summary.net_book_value_total == Decimal("120000.00")


def test_monthly_depreciation_is_idempotent_and_updates_net_book_value():
    create_fixed_asset(_asset_request())

    result = run_monthly_depreciation("2026-06", "default", "财务主管")
    repeat = run_monthly_depreciation("2026-06", "default", "财务主管")
    updated = list_fixed_assets("default").assets[0]

    assert result.period == "2026-06"
    assert result.depreciated_count == 1
    assert result.total_depreciation == Decimal("1800.00")
    assert repeat.depreciated_count == 0
    assert repeat.total_depreciation == Decimal("0.00")
    assert updated.accumulated_depreciation == Decimal("1800.00")
    assert updated.net_book_value == Decimal("118200.00")
    assert updated.last_depreciated_period == "2026-06"


def test_period_depreciation_summary_returns_next_depreciation_without_mutating_asset():
    create_fixed_asset(_asset_request())

    summary = get_period_depreciation_summary("default", "2026-06")
    asset = list_fixed_assets("default").assets[0]

    assert summary[0]["amount"] == Decimal("1800.00")
    assert summary[0]["debit_account_code"] == "6602"
    assert summary[0]["credit_account_code"] == "1602"
    assert asset.accumulated_depreciation == Decimal("0.00")


def test_dispose_and_sell_stop_future_depreciation_and_record_gain_or_loss():
    disposed = dispose_fixed_asset(create_fixed_asset(_asset_request()).id, "2026-06-30", "损坏报废", "财务主管")
    sold_asset = create_fixed_asset(
        _asset_request(name="测试设备", original_cost="60000.00", salvage_value="6000.00")
    )
    sold = sell_fixed_asset(
        sold_asset.id,
        FixedAssetSaleRequest(
            sale_date="2026-06-30",
            sale_amount=Decimal("58000.00"),
            reason="更新换代",
            operator="财务主管",
        ),
    )

    result = run_monthly_depreciation("2026-07", "default", "财务主管")
    payload = list_fixed_assets("default")

    assert disposed.status == "disposed"
    assert sold.status == "sold"
    assert sold.sale_gain_or_loss == Decimal("-2000.00")
    assert result.depreciated_count == 0
    assert payload.summary.disposed_count == 1
    assert payload.summary.sold_count == 1


def test_inventory_updates_location_condition_and_checker():
    asset = create_fixed_asset(_asset_request())

    checked = inventory_fixed_asset(
        asset.id,
        FixedAssetInventoryRequest(
            inventory_date="2026-06-30",
            location="二号仓",
            custodian="资产专员",
            condition="正常",
            operator="盘点员",
            note="已贴标签",
        ),
    )

    assert checked.location == "二号仓"
    assert checked.custodian == "资产专员"
    assert checked.condition == "正常"
    assert checked.inventory_status == "checked"
    assert checked.last_inventory_by == "盘点员"
    assert checked.inventory_note == "已贴标签"
