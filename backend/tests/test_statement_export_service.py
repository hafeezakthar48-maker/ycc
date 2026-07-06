from io import BytesIO
from zipfile import ZipFile

from app.models.financial_statement import FinancialStatementGenerateRequest
from app.services.financial_statement_service import generate_financial_statements
from app.services.statement_archive_service import create_statement_snapshot, reset_statement_archive_store
from app.services.statement_export_service import (
    EXCEL_STATEMENT_MIME_TYPE,
    PDF_STATEMENT_MIME_TYPE,
    build_statement_export,
    statement_export_filename,
)


def setup_function():
    reset_statement_archive_store()


def test_build_statement_xlsx_contains_required_worksheets():
    bundle = generate_financial_statements(FinancialStatementGenerateRequest(period="2026-06"))
    snapshot = create_statement_snapshot(bundle=bundle, created_by="finance-user")

    payload = build_statement_export(snapshot, "xlsx")

    assert payload.content_type == EXCEL_STATEMENT_MIME_TYPE
    assert payload.filename == "financial-statements-default-2026-06-v1.xlsx"
    with ZipFile(BytesIO(payload.content)) as workbook:
        workbook_names = set(workbook.namelist())
    assert "xl/workbook.xml" in workbook_names
    assert "xl/worksheets/sheet1.xml" in workbook_names


def test_build_statement_pdf_returns_pdf_bytes():
    bundle = generate_financial_statements(FinancialStatementGenerateRequest(period="2026-06"))
    snapshot = create_statement_snapshot(bundle=bundle, created_by="finance-user")

    payload = build_statement_export(snapshot, "pdf")

    assert payload.content_type == PDF_STATEMENT_MIME_TYPE
    assert payload.filename == statement_export_filename(snapshot, "pdf")
    assert payload.content.startswith(b"%PDF")
