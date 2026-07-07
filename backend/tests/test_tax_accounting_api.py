from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from app.models.accounting import JournalEntryCreate, JournalLineCreate
from app.services.accounting_period_service import reset_accounting_period_store
from app.services.accounting_service import post_journal_entry, reset_accounting_store
from app.services.system_admin_service import reset_system_admin_store


client = TestClient(app)


def setup_function():
    reset_accounting_store()
    reset_accounting_period_store()
    reset_system_admin_store()


def teardown_function():
    reset_accounting_period_store()


def test_tax_accounting_api_runs_tax_workflow_and_reads_worksheet():
    _post_output_vat_entry()
    _post_input_vat_entry()

    ledger_response = client.get(
        "/api/v1/tax-accounting/vat-ledger",
        params={"account_set_id": "default", "period": "2026-06"},
        headers={"X-Actor-Id": "u-finance-manager"},
    )
    worksheet_response = client.get(
        "/api/v1/tax-accounting/filing-worksheet",
        params={"account_set_id": "default", "period": "2026-06"},
        headers={"X-Actor-Id": "u-finance-manager"},
    )
    transfer_response = client.post(
        "/api/v1/tax-accounting/unpaid-vat-transfer",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={"account_set_id": "default", "period": "2026-06", "amount": "26.00"},
    )
    surtax_response = client.post(
        "/api/v1/tax-accounting/surtax-accrual",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={"account_set_id": "default", "period": "2026-06", "vat_payable": "26.00"},
    )
    income_tax_response = client.post(
        "/api/v1/tax-accounting/income-tax-accrual",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={"account_set_id": "default", "period": "2026-06", "amount": "5000.00"},
    )
    payment_response = client.post(
        "/api/v1/tax-accounting/tax-payments",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={
            "account_set_id": "default",
            "period": "2026-07",
            "tax_account_code": "222102",
            "amount": "26.00",
            "bank_account_code": "1002",
        },
    )

    assert ledger_response.status_code == 200
    assert ledger_response.json()["total"] == 2
    assert worksheet_response.status_code == 200
    assert worksheet_response.json()["vat_payable"] == "26.00"
    assert transfer_response.status_code == 200
    assert transfer_response.json()["source_type"] == "tax_unpaid_vat_transfer"
    assert surtax_response.status_code == 200
    assert surtax_response.json()["source_type"] == "tax_surtax_accrual"
    assert income_tax_response.status_code == 200
    assert income_tax_response.json()["source_type"] == "tax_income_tax_accrual"
    assert payment_response.status_code == 200
    assert payment_response.json()["source_type"] == "tax_payment"

    audit_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=20")
    events = [log["event"] for log in audit_response.json()["logs"]]
    assert "tax_accounting.vat_ledger.read" in events
    assert "tax_accounting.worksheet.read" in events
    assert "tax_accounting.vat.transfer" in events
    assert "tax_accounting.surtax.accrue" in events
    assert "tax_accounting.income_tax.accrue" in events
    assert "tax_accounting.payment.post" in events


def test_tax_accounting_api_rejects_unauthorized_accrual_and_records_audit():
    response = client.post(
        "/api/v1/tax-accounting/surtax-accrual",
        headers={"X-Actor-Id": "u-auditor"},
        json={"account_set_id": "default", "period": "2026-06", "vat_payable": "26.00"},
    )

    assert response.status_code == 403
    audit_response = client.get(
        "/api/v1/system/audit-logs",
        params={"event": "tax_accounting.surtax.accrue", "actor_id": "u-auditor"},
    )
    log = audit_response.json()["logs"][0]
    assert log["result"] == "denied"
    assert log["metadata"]["permission_code"] == "tax_accounting.accrue"


def _post_output_vat_entry():
    return post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-20",
            source_type="tax_api_test",
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
            source_type="tax_api_test",
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
