from app.models.accounting import AuxiliaryDimensionCreate
from app.services.accounting_service import (
    get_auxiliary_dimension,
    list_auxiliary_dimensions,
    reset_accounting_store,
    upsert_auxiliary_dimension,
)


def setup_function():
    reset_accounting_store()


def test_upsert_and_list_customer_dimension():
    created = upsert_auxiliary_dimension(
        AuxiliaryDimensionCreate(
            account_set_id="default",
            dimension_type="customer",
            dimension_code="CUST-SH-001",
            dimension_name="上海云智科技有限公司",
        )
    )

    loaded = get_auxiliary_dimension("default", "customer", "CUST-SH-001")
    listed = list_auxiliary_dimensions("default", "customer")

    assert created.dimension_name == "上海云智科技有限公司"
    assert loaded.dimension_code == "CUST-SH-001"
    assert listed.total == 1
    assert listed.dimensions[0].dimension_type == "customer"


def test_list_dimension_types_contains_core_finance_dimensions():
    dimensions = list_auxiliary_dimensions("default").supported_dimension_types

    assert "customer" in dimensions
    assert "supplier" in dimensions
    assert "department" in dimensions
    assert "asset" in dimensions
    assert "sku" in dimensions
