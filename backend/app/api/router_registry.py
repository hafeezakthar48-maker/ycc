from fastapi import FastAPI

from app.api.accounting import router as accounting_router
from app.api.accounting_archive import router as accounting_archive_router
from app.api.audit import router as audit_router
from app.api.bank_reconciliation import router as bank_reconciliation_router
from app.api.dashboard import router as dashboard_router
from app.api.ecommerce import router as ecommerce_router
from app.api.finance_qa import router as finance_qa_router
from app.api.financial_statements import router as financial_statements_router
from app.api.fixed_asset_accounting import router as fixed_asset_accounting_router
from app.api.fixed_assets import router as fixed_assets_router
from app.api.home import router as home_router
from app.api.invoice_ocr import router as invoice_ocr_router
from app.api.inventory_accounting import router as inventory_accounting_router
from app.api.ledger import router as ledger_router
from app.api.modules import router as modules_router
from app.api.payroll import router as payroll_router
from app.api.payroll_accounting import router as payroll_accounting_router
from app.api.period_close import router as period_close_router
from app.api.policies import router as policies_router
from app.api.receivable_payable import router as receivable_payable_router
from app.api.risk_closures import router as risk_closures_router
from app.api.system_admin import router as system_admin_router
from app.api.vouchers import router as vouchers_router


def include_api_routers(app: FastAPI) -> None:
    app.include_router(accounting_router)
    app.include_router(accounting_archive_router)
    app.include_router(bank_reconciliation_router)
    app.include_router(modules_router)
    app.include_router(dashboard_router)
    app.include_router(audit_router)
    app.include_router(ecommerce_router)
    app.include_router(finance_qa_router)
    app.include_router(financial_statements_router)
    app.include_router(fixed_asset_accounting_router)
    app.include_router(fixed_assets_router)
    app.include_router(home_router)
    app.include_router(invoice_ocr_router)
    app.include_router(inventory_accounting_router)
    app.include_router(ledger_router)
    app.include_router(payroll_router)
    app.include_router(payroll_accounting_router)
    app.include_router(period_close_router)
    app.include_router(policies_router)
    app.include_router(receivable_payable_router)
    app.include_router(risk_closures_router)
    app.include_router(system_admin_router)
    app.include_router(vouchers_router)
