from decimal import Decimal

from app.models.fixed_asset_accounting import FormalAssetAccountingCard


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
