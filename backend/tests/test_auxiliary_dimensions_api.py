from fastapi.testclient import TestClient

from app.main import app
from app.services.accounting_service import reset_accounting_store


client = TestClient(app)


def setup_function():
    reset_accounting_store()


def test_finance_manager_can_create_and_list_auxiliary_dimension():
    response = client.post(
        "/api/v1/accounting/dimensions",
        json={
            "account_set_id": "default",
            "dimension_type": "customer",
            "dimension_code": "CUST-SH-001",
            "dimension_name": "上海客户",
        },
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert response.status_code == 200
    assert response.json()["dimension_name"] == "上海客户"

    list_response = client.get(
        "/api/v1/accounting/dimensions?account_set_id=default&dimension_type=customer",
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1


def test_ledger_detail_accepts_dimension_filter_query_params():
    client.post(
        "/api/v1/accounting/dimensions",
        json={
            "account_set_id": "default",
            "dimension_type": "customer",
            "dimension_code": "CUST-SH-001",
            "dimension_name": "上海客户",
        },
        headers={"X-Actor-Id": "u-finance-manager"},
    )
    client.post(
        "/api/v1/accounting/journal-entries",
        json={
            "account_set_id": "default",
            "entry_date": "2026-06-18",
            "source_type": "manual_adjustment",
            "source_id": "api-dimension-entry",
            "description": "客户维度收入",
            "lines": [
                {
                    "account_code": "1122",
                    "account_name": "应收账款",
                    "direction": "debit",
                    "original_amount": "100.00",
                    "base_amount": "100.00",
                    "dimensions": [{"dimension_type": "customer", "dimension_code": "CUST-SH-001"}],
                },
                {
                    "account_code": "6001",
                    "account_name": "主营业务收入",
                    "direction": "credit",
                    "original_amount": "100.00",
                    "base_amount": "100.00",
                    "dimensions": [{"dimension_type": "customer", "dimension_code": "CUST-SH-001"}],
                },
            ],
        },
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    response = client.get(
        "/api/v1/ledger/detail?period=2026-06&account_code=1122&dimension_type=customer&dimension_code=CUST-SH-001",
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert response.status_code == 200
    assert response.json()["lines"][0]["dimensions"][0]["dimension_name"] == "上海客户"
