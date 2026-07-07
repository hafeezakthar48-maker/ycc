from decimal import Decimal

from app.models.tax_accounting import VatLedgerLine
from app.services.accounting_period_service import reset_accounting_period_store
from app.services.accounting_service import list_journal_entries, reset_accounting_store
from app.services.tax_accounting_service import calculate_vat_payable, post_unpaid_vat_transfer


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
