from decimal import Decimal

from app.models.tax_accounting import VatLedgerLine
from app.services.accounting_period_service import reset_accounting_period_store
from app.models.accounting import JournalEntryCreate, JournalLineCreate
from app.services.accounting_service import list_journal_entries, post_journal_entry, reset_accounting_store
from app.services.tax_accounting_service import (
    build_tax_filing_worksheet,
    calculate_income_tax_payable,
    calculate_surtax,
    calculate_vat_payable,
    list_vat_ledger_lines,
    post_income_tax_accrual,
    post_surtax_accrual,
    post_tax_payment,
    post_unpaid_vat_transfer,
)


def setup_function():
    reset_accounting_store()
    reset_accounting_period_store()


def teardown_function():
    reset_accounting_period_store()


def test_vat_ledger_line_keeps_tax_base_and_tax_amount():
    line = VatLedgerLine(
        account_set_id="default",
        period="2026-06",
        tax_direction="output",
        invoice_no="INV-001",
        tax_base=Decimal("1000.00"),
        tax_amount=Decimal("130.00"),
        counterparty_id="CUST-001",
        source_journal_entry_id="je-001",
    )

    assert line.tax_amount == Decimal("130.00")


def test_calculate_vat_payable_offsets_input_against_output():
    result = calculate_vat_payable(
        output_vat=Decimal("1300.00"),
        input_vat=Decimal("800.00"),
        input_transfer_out=Decimal("100.00"),
    )

    assert result == Decimal("600.00")


def test_post_unpaid_vat_transfer_moves_payable_to_unpaid_vat():
    entry = post_unpaid_vat_transfer(
        account_set_id="default",
        period="2026-06",
        amount=Decimal("600.00"),
        actor_id="tax-user",
    )
    entries = list_journal_entries("default", "2026-06").entries

    assert entry.source_id == "tax_unpaid_vat_transfer:default:2026-06"
    assert len(entries) == 1
    assert [(line.account_code, line.direction, line.base_amount) for line in entry.lines] == [
        ("22210103", "debit", Decimal("600.00")),
        ("222102", "credit", Decimal("600.00")),
    ]


def test_calculate_surtax_uses_configured_rates():
    result = calculate_surtax(
        vat_payable=Decimal("1000.00"),
        urban_maintenance_rate=Decimal("0.07"),
        education_rate=Decimal("0.03"),
        local_education_rate=Decimal("0.02"),
    )

    assert result.urban == Decimal("70.00")
    assert result.education == Decimal("30.00")
    assert result.local == Decimal("20.00")
    assert result.total == Decimal("120.00")


def test_post_surtax_accrual_posts_tax_and_surcharge_liability():
    result = calculate_surtax(
        vat_payable=Decimal("1000.00"),
        urban_maintenance_rate=Decimal("0.07"),
        education_rate=Decimal("0.03"),
        local_education_rate=Decimal("0.02"),
    )

    entry = post_surtax_accrual(
        account_set_id="default",
        period="2026-06",
        surtax_result=result,
        actor_id="tax-user",
    )

    assert entry.source_id == "tax_surtax_accrual:default:2026-06"
    assert [(line.account_code, line.direction, line.base_amount) for line in entry.lines] == [
        ("6403", "debit", Decimal("120.00")),
        ("222103", "credit", Decimal("120.00")),
    ]


def test_calculate_income_tax_payable_uses_tax_adjustments():
    result = calculate_income_tax_payable(
        accounting_profit=Decimal("100000.00"),
        taxable_increase=Decimal("5000.00"),
        taxable_decrease=Decimal("10000.00"),
        tax_rate=Decimal("0.25"),
    )

    assert result.taxable_income == Decimal("95000.00")
    assert result.income_tax_payable == Decimal("23750.00")


def test_post_income_tax_accrual_posts_income_tax_expense():
    entry = post_income_tax_accrual(
        account_set_id="default",
        period="2026-06",
        amount=Decimal("23750.00"),
        actor_id="tax-user",
    )

    assert entry.source_id == "tax_income_tax_accrual:default:2026-06"
    assert [(line.account_code, line.direction, line.base_amount) for line in entry.lines] == [
        ("6801", "debit", Decimal("23750.00")),
        ("222104", "credit", Decimal("23750.00")),
    ]


def test_list_vat_ledger_lines_reads_input_and_output_tax_entries():
    _post_output_vat_entry()
    _post_input_vat_entry()

    lines = list_vat_ledger_lines("default", "2026-06")

    assert [(line.tax_direction, line.tax_base, line.tax_amount) for line in lines] == [
        ("input", Decimal("800.00"), Decimal("104.00")),
        ("output", Decimal("1000.00"), Decimal("130.00")),
    ]
    assert all(line.source_journal_entry_id.startswith("je-") for line in lines)


def test_build_tax_filing_worksheet_summarizes_vat_and_accruals():
    _post_output_vat_entry()
    _post_input_vat_entry()
    post_unpaid_vat_transfer("default", "2026-06", Decimal("26.00"), "tax-user")
    post_surtax_accrual("default", "2026-06", calculate_surtax(Decimal("26.00"), Decimal("0.07"), Decimal("0.03"), Decimal("0.02")), "tax-user")
    post_income_tax_accrual("default", "2026-06", Decimal("5000.00"), "tax-user")

    worksheet = build_tax_filing_worksheet("default", "2026-06")

    assert worksheet.output_vat == Decimal("130.00")
    assert worksheet.input_vat == Decimal("104.00")
    assert worksheet.vat_payable == Decimal("26.00")
    assert worksheet.surtax_payable == Decimal("3.12")
    assert worksheet.income_tax_payable == Decimal("5000.00")


def test_post_tax_payment_debits_tax_liability_and_credits_bank():
    entry = post_tax_payment(
        account_set_id="default",
        period="2026-07",
        tax_account_code="222102",
        amount=Decimal("600.00"),
        bank_account_code="1002",
        actor_id="tax-user",
    )

    assert entry.source_id == "tax_payment:default:2026-07:222102"
    assert [(line.account_code, line.direction, line.base_amount) for line in entry.lines] == [
        ("222102", "debit", Decimal("600.00")),
        ("1002", "credit", Decimal("600.00")),
    ]


def _post_output_vat_entry():
    return post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-20",
            source_type="tax_test",
            source_id="output-vat",
            description="销售销项税",
            lines=[
                JournalLineCreate(
                    account_code="1122",
                    account_name="应收账款",
                    direction="debit",
                    original_amount=Decimal("1130.00"),
                    base_amount=Decimal("1130.00"),
                ),
                JournalLineCreate(
                    account_code="6001",
                    account_name="主营业务收入",
                    direction="credit",
                    original_amount=Decimal("1000.00"),
                    base_amount=Decimal("1000.00"),
                ),
                JournalLineCreate(
                    account_code="22210102",
                    account_name="应交税费-应交增值税（销项税额）",
                    direction="credit",
                    original_amount=Decimal("130.00"),
                    base_amount=Decimal("130.00"),
                ),
            ],
        )
    )


def _post_input_vat_entry():
    return post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-21",
            source_type="tax_test",
            source_id="input-vat",
            description="采购进项税",
            lines=[
                JournalLineCreate(
                    account_code="6602",
                    account_name="管理费用",
                    direction="debit",
                    original_amount=Decimal("800.00"),
                    base_amount=Decimal("800.00"),
                ),
                JournalLineCreate(
                    account_code="22210101",
                    account_name="应交税费-应交增值税（进项税额）",
                    direction="debit",
                    original_amount=Decimal("104.00"),
                    base_amount=Decimal("104.00"),
                ),
                JournalLineCreate(
                    account_code="2202",
                    account_name="应付账款",
                    direction="credit",
                    original_amount=Decimal("904.00"),
                    base_amount=Decimal("904.00"),
                ),
            ],
        )
    )
