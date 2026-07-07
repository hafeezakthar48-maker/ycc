from decimal import Decimal

from app.models.consolidation import ConsolidationEntity


def test_consolidation_entity_records_ownership_percentage():
    entity = ConsolidationEntity(
        consolidation_group_id="group-001",
        account_set_id="subsidiary-a",
        entity_name="子公司A",
        ownership_percentage=Decimal("0.80"),
        consolidation_method="proportionate",
    )

    assert entity.ownership_percentage == Decimal("0.80")
