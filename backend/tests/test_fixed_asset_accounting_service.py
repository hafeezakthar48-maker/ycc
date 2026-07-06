from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.fixed_asset import FixedAssetCreateRequest
from app.models.fixed_asset_accounting import FormalAssetAccountingCard
from app.services.accounting_period_service import close_accounting_period, reset_accounting_period_store
from app.services.accounting_service import list_journal_entries, reset_accounting_store
from app.services.fixed_asset_accounting_service import capitalize_fixed_asset, reset_fixed_asset_accounting_store
from app.services.fixed_asset_service import create_fixed_asset, reset_fixed_asset_store


def setup_function():
    reset_accounting_store()
    reset_accounting_period_store()
    reset_fixed_asset_store()
    reset_fixed_asset_accounting_store()


def test_formal_asset_accounting_card_uses_decimal_amounts():
    card = FormalAssetAccountingCard(
        account_set_id="default",
        asset_id="fixed-asset-001",
        asset_code="FA-202601-0001",
        asset_name="生产设备A",
        category="生产设备",
        acquisition_date="2026-01-15",
        original_cost=Decimal("120000.00"),
        salvage_value=Decimal("12000.00"),
        useful_life_months=60,
        monthly_depreciation=Decimal("1800.00"),
        accumulated_depreciation=Decimal("0.00"),
        impairment_amount=Decimal("0.00"),
        net_book_value=Decimal("120000.00"),
        asset_status="active",
        formal_accounting_status="not_capitalized",
    )

    assert card.original_cost == Decimal("120000.00")
    assert card.monthly_depreciation == Decimal("1800.00")
    assert card.formal_accounting_status == "not_capitalized"


def test_capitalize_fixed_asset_posts_formal_entry_with_asset_dimension():
    asset = create_fixed_asset(_asset_request())

    entry = capitalize_fixed_asset(
        account_set_id="default",
        asset_id=asset.id,
        period="2026-01",
        credit_account_code="2202",
        actor_id="asset-user",
    )

    assert entry.source_type == "fixed_asset_capitalization"
    assert entry.source_id == f"fixed_asset_capitalization:default:{asset.id}"
    assert [(line.account_code, line.direction, line.base_amount) for line in entry.lines] == [
        ("1601", "debit", Decimal("120000.00")),
        ("2202", "credit", Decimal("120000.00")),
    ]
    assert entry.lines[0].dimensions[0].dimension_type == "asset"
    assert entry.lines[0].dimensions[0].dimension_code == asset.asset_code


def test_capitalize_fixed_asset_is_idempotent_by_asset():
    asset = create_fixed_asset(_asset_request())

    first = capitalize_fixed_asset("default", asset.id, "2026-01", "2202", "asset-user")
    second = capitalize_fixed_asset("default", asset.id, "2026-01", "2202", "asset-user")

    entries = list_journal_entries("default", "2026-01").entries
    assert second.id == first.id
    assert len([entry for entry in entries if entry.source_type == "fixed_asset_capitalization"]) == 1


def test_capitalize_fixed_asset_rejects_closed_period():
    asset = create_fixed_asset(_asset_request())
    close_accounting_period("2026-01", "finance-user")

    with pytest.raises(HTTPException) as exc_info:
        capitalize_fixed_asset("default", asset.id, "2026-01", "2202", "asset-user")

    assert exc_info.value.status_code == 409


def _asset_request() -> FixedAssetCreateRequest:
    return FixedAssetCreateRequest(
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
