from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.accounting import JournalEntryCreate, JournalLineCreate
from app.services.accounting_service import (
    get_chart_of_accounts,
    get_journal_entry,
    list_journal_entries,
    post_journal_entry,
    reset_accounting_store,
    reverse_journal_entry,
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


def _balanced_entry(source_id="voucher-1"):
    return JournalEntryCreate(
        account_set_id="default",
        entry_date="2026-06-18",
        source_type="voucher_center",
        source_id=source_id,
        description="费用采购正式过账",
        created_by="财务主管",
        posted_by="财务主管",
        lines=[
            JournalLineCreate(
                account_code="6602",
                account_name="管理费用",
                direction="debit",
                original_amount=Decimal("100.00"),
                base_amount=Decimal("100.00"),
                description="费用",
            ),
            JournalLineCreate(
                account_code="2202",
                account_name="应付账款",
                direction="credit",
                original_amount=Decimal("100.00"),
                base_amount=Decimal("100.00"),
                description="应付",
            ),
        ],
    )


def test_post_journal_entry_persists_immutable_entry():
    entry = post_journal_entry(_balanced_entry())

    loaded = get_journal_entry(entry.id)
    assert loaded.entry_number == "JE-202606-0001"
    assert loaded.period == "2026-06"
    assert loaded.status == "posted"
    assert loaded.lines[0].line_no == 1
    assert list_journal_entries("default", "2026-06").total == 1


def test_post_journal_entry_rejects_unbalanced_base_amounts():
    request = _balanced_entry("voucher-unbalanced")
    request.lines[1].base_amount = Decimal("99.99")

    with pytest.raises(HTTPException) as exc_info:
        post_journal_entry(request)

    assert exc_info.value.status_code == 422
    assert "借贷不平衡" in exc_info.value.detail


def test_reverse_journal_entry_creates_reversal_without_deleting_original():
    entry = post_journal_entry(_balanced_entry())

    reversal = reverse_journal_entry(entry.id, operator="财务主管")

    original = get_journal_entry(entry.id)
    assert original.status == "reversed"
    assert reversal.reversal_of_entry_id == entry.id
    assert reversal.lines[0].direction == "credit"
    assert reversal.lines[1].direction == "debit"
    assert list_journal_entries("default", "2026-06").total == 2
