from fastapi.testclient import TestClient

from app.main import app
from app.services.accounting_service import reset_accounting_store


client = TestClient(app)


def setup_function():
    reset_accounting_store()


def test_finance_manager_can_create_exchange_rate():
    response = client.post(
        "/api/v1/accounting/exchange-rates",
        json={
            "account_set_id": "default",
            "rate_date": "2026-06-18",
            "source_currency": "USD",
            "target_currency": "CNY",
            "rate": "7.120000",
            "source": "manual",
        },
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert response.status_code == 200
    assert response.json()["rate"] == "7.120000"


def test_finance_manager_can_create_foreign_currency_journal_entry():
    client.post(
        "/api/v1/accounting/exchange-rates",
        json={
            "account_set_id": "default",
            "rate_date": "2026-06-18",
            "source_currency": "USD",
            "target_currency": "CNY",
            "rate": "7.120000",
        },
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    response = client.post(
        "/api/v1/accounting/journal-entries",
        json={
            "account_set_id": "default",
            "entry_date": "2026-06-18",
            "source_type": "manual_adjustment",
            "source_id": "fx-api-1",
            "description": "美元收入",
            "base_currency": "CNY",
            "created_by": "财务主管",
            "posted_by": "财务主管",
            "lines": [
                {
                    "account_code": "1122",
                    "account_name": "应收账款",
                    "direction": "debit",
                    "currency": "USD",
                    "original_amount": "100.00",
                    "exchange_rate": "7.120000",
                    "base_amount": "712.00",
                    "description": "美元应收",
                },
                {
                    "account_code": "6001",
                    "account_name": "主营业务收入",
                    "direction": "credit",
                    "currency": "USD",
                    "original_amount": "100.00",
                    "exchange_rate": "7.120000",
                    "base_amount": "712.00",
                    "description": "美元收入",
                },
            ],
        },
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert response.status_code == 200
    assert response.json()["lines"][0]["currency"] == "USD"
