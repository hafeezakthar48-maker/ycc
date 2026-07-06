from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.accounting import ExchangeRateCreate, JournalEntryCreate, JournalLineCreate
from app.services.accounting_service import (
    get_exchange_rate,
    get_journal_entry,
    list_currencies,
    post_journal_entry,
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


def test_post_foreign_currency_entry_keeps_original_and_base_amounts():
    upsert_exchange_rate(
        ExchangeRateCreate(
            account_set_id="default",
            rate_date="2026-06-18",
            source_currency="USD",
            target_currency="CNY",
            rate=Decimal("7.120000"),
        )
    )

    entry = post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-18",
            source_type="manual_adjustment",
            source_id="fx-sale-1",
            description="美元销售收入",
            base_currency="CNY",
            lines=[
                JournalLineCreate(
                    account_code="1122",
                    account_name="应收账款",
                    direction="debit",
                    currency="USD",
                    original_amount=Decimal("100.00"),
                    exchange_rate=Decimal("7.120000"),
                    base_amount=Decimal("712.00"),
                    description="美元应收",
                ),
                JournalLineCreate(
                    account_code="6001",
                    account_name="主营业务收入",
                    direction="credit",
                    currency="USD",
                    original_amount=Decimal("100.00"),
                    exchange_rate=Decimal("7.120000"),
                    base_amount=Decimal("712.00"),
                    description="美元收入",
                ),
            ],
        )
    )

    loaded = get_journal_entry(entry.id)
    assert loaded.lines[0].currency == "USD"
    assert loaded.lines[0].original_amount == Decimal("100.00")
    assert loaded.lines[0].base_amount == Decimal("712.00")


def test_post_foreign_currency_entry_rejects_wrong_base_amount():
    upsert_exchange_rate(
        ExchangeRateCreate(
            account_set_id="default",
            rate_date="2026-06-18",
            source_currency="USD",
            target_currency="CNY",
            rate=Decimal("7.120000"),
        )
    )

    request = JournalEntryCreate(
        account_set_id="default",
        entry_date="2026-06-18",
        source_type="manual_adjustment",
        source_id="fx-wrong-base",
        description="错误折算",
        base_currency="CNY",
        lines=[
            JournalLineCreate(
                account_code="1122",
                account_name="应收账款",
                direction="debit",
                currency="USD",
                original_amount=Decimal("100.00"),
                exchange_rate=Decimal("7.120000"),
                base_amount=Decimal("711.99"),
            ),
            JournalLineCreate(
                account_code="6001",
                account_name="主营业务收入",
                direction="credit",
                currency="USD",
                original_amount=Decimal("100.00"),
                exchange_rate=Decimal("7.120000"),
                base_amount=Decimal("711.99"),
            ),
        ],
    )

    with pytest.raises(HTTPException) as exc_info:
        post_journal_entry(request)

    assert exc_info.value.status_code == 422
    assert "折算金额" in exc_info.value.detail
