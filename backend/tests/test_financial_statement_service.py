from decimal import Decimal
from typing import get_args

import pytest

from app.models.accounting import JournalEntryCreate, JournalLineCreate
from app.models.financial_statement import FinancialStatementGenerateRequest
from app.models.voucher_center import VoucherCenterCreateRequest, VoucherCenterLine
from app.services.accounting_service import post_journal_entry, reset_accounting_store
from app.services.financial_statement_service import generate_financial_statements
from app.services.voucher_center_service import create_voucher, reset_voucher_store, review_voucher


@pytest.fixture(autouse=True)
def isolated_voucher_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_VOUCHER_DB_PATH", str(tmp_path / "voucher-center.sqlite3"))
    monkeypatch.setenv("FINANCE_AI_ACCOUNTING_DB_PATH", str(tmp_path / "formal-accounting.sqlite3"))
    reset_voucher_store()
    reset_accounting_store()


def test_financial_statements_fallback_to_sample_finance_data():
    result = generate_financial_statements(FinancialStatementGenerateRequest(period="2026-06"))

    assert result.period == "2026-06"
    assert result.source == "sample_finance_data"
    assert result.summary.asset_liability_balanced is True
    assert result.balance_sheet.total_assets == Decimal("2216.00")
    assert result.balance_sheet.total_liabilities_and_equity == Decimal("2216.00")
    assert result.income_statement.total_revenue == Decimal("1286.00")
    assert result.cash_flow_statement.net_cash_flow == Decimal("62.00")
    assert result.management_summary.key_metrics["净利率"] == "11.35%"
    assert {item.name for item in result.equity_statement.items} >= {
        "期初所有者权益",
        "本期净利润",
        "期末所有者权益",
    }


def test_financial_statements_use_reviewed_voucher_account_balances():
    debit_direction, credit_direction = get_args(VoucherCenterLine.model_fields["direction"].annotation)
    voucher = create_voucher(
        VoucherCenterCreateRequest(
            voucher_date="2026-06-30",
            summary="主营业务收入确认",
            counterparty="上海客户",
            invoice_number="INV-202606",
            amount=Decimal("1000.00"),
            tax_amount=Decimal("60.00"),
            total_amount_with_tax=Decimal("1060.00"),
            lines=[
                VoucherCenterLine(
                    account_code="1122",
                    account_name="应收账款",
                    direction=debit_direction,
                    amount=Decimal("1060.00"),
                    explanation="确认应收",
                ),
                VoucherCenterLine(
                    account_code="6001",
                    account_name="主营业务收入",
                    direction=credit_direction,
                    amount=Decimal("1000.00"),
                    explanation="确认收入",
                ),
                VoucherCenterLine(
                    account_code="22210102",
                    account_name="应交税费-销项税额",
                    direction=credit_direction,
                    amount=Decimal("60.00"),
                    explanation="销项税",
                ),
            ],
        )
    )
    review_voucher(voucher.id, "财务主管")

    result = generate_financial_statements(FinancialStatementGenerateRequest(period="2026-06"))

    assert result.source == "reviewed_vouchers"
    assert result.balance_sheet.total_assets == Decimal("1060.00")
    assert result.balance_sheet.total_liabilities == Decimal("60.00")
    assert result.income_statement.total_revenue == Decimal("1000.00")
    assert result.income_statement.net_profit == Decimal("1000.00")
    assert result.summary.reviewed_voucher_count == 1


def test_financial_statements_prefer_formal_journal_entries():
    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-18",
            source_type="manual_adjustment",
            source_id="revenue-1",
            description="正式收入分录",
            lines=[
                JournalLineCreate(
                    account_code="1122",
                    account_name="应收账款",
                    direction="debit",
                    original_amount=Decimal("1000.00"),
                    base_amount=Decimal("1000.00"),
                ),
                JournalLineCreate(
                    account_code="6001",
                    account_name="主营业务收入",
                    direction="credit",
                    original_amount=Decimal("1000.00"),
                    base_amount=Decimal("1000.00"),
                ),
            ],
        )
    )

    bundle = generate_financial_statements(FinancialStatementGenerateRequest(period="2026-06", account_set_id="default"))

    assert bundle.source == "formal_journal_entries"
    assert bundle.income_statement.total_revenue == Decimal("1000.00")
