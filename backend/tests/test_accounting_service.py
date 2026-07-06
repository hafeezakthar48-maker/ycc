from app.services.accounting_service import (
    get_chart_of_accounts,
    reset_accounting_store,
)


def setup_function():
    reset_accounting_store()


def test_chart_of_accounts_contains_required_mvp_accounts():
    accounts = get_chart_of_accounts("default").accounts

    account_codes = {account.account_code for account in accounts}
    assert {"1001", "1122", "2202", "6001", "6602"}.issubset(account_codes)
    cash = next(account for account in accounts if account.account_code == "1001")
    assert cash.account_name == "库存现金"
    assert cash.account_type == "asset"
    assert cash.normal_balance == "debit"
    assert cash.is_active is True
