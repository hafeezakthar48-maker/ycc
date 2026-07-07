from decimal import Decimal

from app.models.tax_accounting import VatLedgerLine


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
