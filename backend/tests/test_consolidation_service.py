from decimal import Decimal

from app.models.consolidation import ConsolidationEntity
from app.services.consolidation_service import (
    build_intercompany_balance_elimination,
    build_intercompany_revenue_cost_elimination,
    build_reporting_package,
    calculate_unrealized_inventory_profit,
)


def test_consolidation_entity_records_ownership_percentage():
    entity = ConsolidationEntity(
        consolidation_group_id="group-001",
        account_set_id="subsidiary-a",
        entity_name="子公司A",
        ownership_percentage=Decimal("0.80"),
        consolidation_method="proportionate",
    )

    assert entity.ownership_percentage == Decimal("0.80")


def test_build_reporting_package_reads_balance_and_income_statement():
    package = build_reporting_package("default", "2026-06")

    assert package.account_set_id == "default"
    assert package.period == "2026-06"
    assert package.balance_sheet is not None
    assert package.income_statement is not None
    assert package.cash_flow_statement is not None


def test_build_intercompany_balance_elimination_offsets_ar_and_ap():
    entry = build_intercompany_balance_elimination(
        group_id="group-001",
        period="2026-06",
        receivable_account_code="1122",
        payable_account_code="2202",
        amount=Decimal("50000.00"),
    )

    assert entry.elimination_type == "intercompany_balance"
    assert entry.debit_account_code == "2202"
    assert entry.credit_account_code == "1122"
    assert entry.amount == Decimal("50000.00")


def test_calculate_unrealized_inventory_profit_uses_margin_rate():
    result = calculate_unrealized_inventory_profit(
        ending_internal_inventory_amount=Decimal("100000.00"),
        internal_gross_margin_rate=Decimal("0.20"),
    )

    assert result == Decimal("20000.00")


def test_build_intercompany_revenue_cost_elimination_offsets_internal_sales():
    entries = build_intercompany_revenue_cost_elimination(
        group_id="group-001",
        period="2026-06",
        revenue_amount=Decimal("80000.00"),
        cost_amount=Decimal("60000.00"),
    )

    assert len(entries) == 1
    assert entries[0].elimination_type == "intercompany_revenue_cost"
    assert entries[0].debit_account_code == "6001"
    assert entries[0].credit_account_code == "6401"
    assert entries[0].amount == Decimal("60000.00")
