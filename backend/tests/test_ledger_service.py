from decimal import Decimal

import pytest

from app.models.accounting import ExchangeRateCreate, JournalEntryCreate, JournalLineCreate
from app.models.voucher_center import VoucherCenterCreateRequest, VoucherCenterLine
from app.services.accounting_service import post_journal_entry, reset_accounting_store, upsert_exchange_rate
from app.services.ledger_service import build_account_balance_table, build_detail_ledger, build_general_ledger
from app.services.voucher_center_service import create_voucher, reset_voucher_store, review_voucher


@pytest.fixture(autouse=True)
def isolated_voucher_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_VOUCHER_DB_PATH", str(tmp_path / "voucher-center.sqlite3"))
    monkeypatch.setenv("FINANCE_AI_ACCOUNTING_DB_PATH", str(tmp_path / "formal-accounting.sqlite3"))
    reset_voucher_store()
    reset_accounting_store()


def _request(voucher_date: str = "2026-06-30", summary: str = "办公服务费") -> VoucherCenterCreateRequest:
    return VoucherCenterCreateRequest(
        voucher_date=voucher_date,
        summary=summary,
        counterparty="上海云智科技有限公司",
        invoice_number="12345678",
        amount=Decimal("1000.00"),
        tax_amount=Decimal("60.00"),
        total_amount_with_tax=Decimal("1060.00"),
        lines=[
            VoucherCenterLine(
                account_code="6602",
                account_name="管理费用",
                direction="借",
                amount=Decimal("1000.00"),
                explanation="办公服务费",
            ),
            VoucherCenterLine(
                account_code="22210101",
                account_name="应交税费-应交增值税（进项税额）",
                direction="借",
                amount=Decimal("60.00"),
                explanation="进项税额",
            ),
            VoucherCenterLine(
                account_code="2202",
                account_name="应付账款",
                direction="贷",
                amount=Decimal("1060.00"),
                explanation="应付未付款",
            ),
        ],
    )


def _reviewed_voucher(voucher_date: str = "2026-06-30", summary: str = "办公服务费"):
    voucher = create_voucher(_request(voucher_date=voucher_date, summary=summary))
    return review_voucher(voucher.id, "财务主管")


def test_general_ledger_uses_only_reviewed_vouchers_in_period():
    reviewed = _reviewed_voucher(summary="已审核办公费")
    create_voucher(_request(summary="草稿办公费"))
    _reviewed_voucher(voucher_date="2026-05-31", summary="上月办公费")

    ledger = build_general_ledger("2026-06")

    assert ledger.period == "2026-06"
    assert ledger.voucher_count == 1
    assert ledger.entry_count == 3
    assert ledger.total_debit == Decimal("1060.00")
    assert ledger.total_credit == Decimal("1060.00")
    assert ledger.balanced is True
    assert ledger.accounts[0].account_code == "2202"
    assert ledger.accounts[0].credit_total == Decimal("1060.00")
    assert ledger.accounts[-1].account_code == "6602"
    assert reviewed.summary == "已审核办公费"


def test_detail_ledger_returns_account_lines_and_running_balance():
    reviewed = _reviewed_voucher(summary="已审核办公费")

    ledger = build_detail_ledger("2026-06", "6602")

    assert ledger.period == "2026-06"
    assert ledger.account_code == "6602"
    assert ledger.account_name == "管理费用"
    assert ledger.line_count == 1
    assert ledger.debit_total == Decimal("1000.00")
    assert ledger.credit_total == Decimal("0.00")
    assert ledger.balance_direction == "借"
    assert ledger.balance_amount == Decimal("1000.00")
    assert ledger.lines[0].voucher_id == reviewed.id
    assert ledger.lines[0].voucher_number == reviewed.voucher_number
    assert ledger.lines[0].debit_amount == Decimal("1000.00")
    assert ledger.lines[0].credit_amount == Decimal("0.00")


def test_account_balance_table_reports_all_reviewed_account_balances():
    _reviewed_voucher()

    balance_table = build_account_balance_table("2026-06")

    assert balance_table.period == "2026-06"
    assert balance_table.account_count == 3
    assert balance_table.total_debit == Decimal("1060.00")
    assert balance_table.total_credit == Decimal("1060.00")
    assert balance_table.balanced is True
    assert [account.account_code for account in balance_table.accounts] == ["2202", "22210101", "6602"]
    assert balance_table.accounts[0].balance_direction == "贷"
    assert balance_table.accounts[0].balance_amount == Decimal("1060.00")


def test_general_ledger_prefers_formal_journal_entries():
    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-18",
            source_type="manual_adjustment",
            source_id="manual-1",
            description="正式分录测试",
            lines=[
                JournalLineCreate(
                    account_code="6602",
                    account_name="管理费用",
                    direction="debit",
                    original_amount=Decimal("100.00"),
                    base_amount=Decimal("100.00"),
                ),
                JournalLineCreate(
                    account_code="2202",
                    account_name="应付账款",
                    direction="credit",
                    original_amount=Decimal("100.00"),
                    base_amount=Decimal("100.00"),
                ),
            ],
        )
    )

    ledger = build_general_ledger("2026-06", "default")

    assert ledger.source == "formal_journal_entries"
    assert ledger.entry_count == 2
    assert ledger.total_debit == Decimal("100.00")
    assert ledger.total_credit == Decimal("100.00")


def test_detail_ledger_shows_original_currency_and_base_amount():
    reset_accounting_store()
    upsert_exchange_rate(
        ExchangeRateCreate(
            account_set_id="default",
            rate_date="2026-06-18",
            source_currency="USD",
            target_currency="CNY",
            rate=Decimal("7.120000"),
        )
    )
    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-18",
            source_type="manual_adjustment",
            source_id="fx-ledger-1",
            description="美元收入",
            lines=[
                JournalLineCreate(
                    account_code="1122",
                    account_name="应收账款",
                    direction="debit",
                    currency="USD",
                    original_amount=Decimal("100.00"),
                    exchange_rate=Decimal("7.120000"),
                    base_amount=Decimal("712.00"),
                ),
                JournalLineCreate(
                    account_code="6001",
                    account_name="主营业务收入",
                    direction="credit",
                    currency="USD",
                    original_amount=Decimal("100.00"),
                    exchange_rate=Decimal("7.120000"),
                    base_amount=Decimal("712.00"),
                ),
            ],
        )
    )

    detail = build_detail_ledger("2026-06", "1122", "default")

    assert detail.source == "formal_journal_entries"
    assert detail.lines[0].currency == "USD"
    assert detail.lines[0].original_amount == Decimal("100.00")
    assert detail.lines[0].exchange_rate == Decimal("7.120000")
    assert detail.lines[0].debit_amount == Decimal("712.00")
