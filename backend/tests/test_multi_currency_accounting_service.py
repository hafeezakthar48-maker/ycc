from decimal import Decimal

from app.models.accounting import ExchangeRateCreate
from app.services.accounting_service import (
    get_exchange_rate,
    list_currencies,
    reset_accounting_store,
    upsert_exchange_rate,
)


def setup_function():
    reset_accounting_store()


def test_list_currencies_contains_supported_mvp_currencies():
    currencies = list_currencies().currencies

    codes = {currency.currency_code for currency in currencies}
    assert {"CNY", "USD", "EUR", "HKD"}.issubset(codes)
    cny = next(currency for currency in currencies if currency.currency_code == "CNY")
    assert cny.currency_name == "人民币"
    assert cny.decimal_places == 2


def test_upsert_and_get_exchange_rate():
    created = upsert_exchange_rate(
        ExchangeRateCreate(
            account_set_id="default",
            rate_date="2026-06-18",
            source_currency="USD",
            target_currency="CNY",
            rate=Decimal("7.120000"),
            source="manual",
        )
    )

    loaded = get_exchange_rate("default", "2026-06-18", "USD", "CNY")

    assert created.rate == Decimal("7.120000")
    assert loaded.rate == Decimal("7.120000")
    assert loaded.source == "manual"
