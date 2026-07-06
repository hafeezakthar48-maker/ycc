import re
from io import BytesIO
from zipfile import BadZipFile

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile

from app.api.upload_security import (
    EXCEL_CONTENT_TYPES,
    EXCEL_EXTENSIONS,
    MAX_EXCEL_UPLOAD_BYTES,
    read_validated_upload,
)
from app.data.sample_finance_data import SAMPLE_FINANCE_DATA
from app.models.finance import (
    DashboardAnalyzeRequest,
    DashboardAnalyzeResponse,
    ManagementReport,
    MonthlyFinanceRecord,
)
from app.services.analysis_service import build_dashboard_overview
from app.services.report_export_service import (
    DOCX_MIME_TYPE,
    PDF_MIME_TYPE,
    build_report_docx,
    build_report_pdf,
    report_export_filename,
)
from app.services.report_service import build_management_report, build_management_report_from_records
from app.services.risk_service import detect_risks
from app.services.spreadsheet_import_service import parse_finance_workbook
from app.services.template_service import EXCEL_MIME_TYPE, TEMPLATE_FILENAME, build_finance_template_workbook


router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def _validate_period(period: str) -> None:
    if not re.fullmatch(r"\d{4}-\d{2}", period):
        raise HTTPException(status_code=422, detail="period 格式必须为 YYYY-MM")


def _to_http_error(error: ValueError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(error))


@router.get("/overview")
def get_overview(period: str = Query(default="2026-06")):
    _validate_period(period)
    try:
        return build_dashboard_overview(period, SAMPLE_FINANCE_DATA)
    except ValueError as error:
        raise _to_http_error(error) from error


@router.get("/risks")
def get_risks(period: str = Query(default="2026-06")):
    _validate_period(period)
    try:
        return detect_risks(period, SAMPLE_FINANCE_DATA)
    except ValueError as error:
        raise _to_http_error(error) from error


@router.get("/report")
def get_report(period: str = Query(default="2026-06")):
    _validate_period(period)
    try:
        return build_management_report(period)
    except ValueError as error:
        raise _to_http_error(error) from error


@router.post("/report/export/docx")
def export_report_docx(report: ManagementReport):
    _validate_period(report.period)
    filename = report_export_filename(report, "docx")
    return Response(
        content=build_report_docx(report),
        media_type=DOCX_MIME_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/report/export/pdf")
def export_report_pdf(report: ManagementReport):
    _validate_period(report.period)
    filename = report_export_filename(report, "pdf")
    return Response(
        content=build_report_pdf(report),
        media_type=PDF_MIME_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/sample-data")
def get_sample_data():
    return SAMPLE_FINANCE_DATA


@router.get("/template/excel")
def download_excel_template():
    return Response(
        content=build_finance_template_workbook(),
        media_type=EXCEL_MIME_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{TEMPLATE_FILENAME}"'},
    )


@router.post("/analyze")
def analyze_dashboard(request: DashboardAnalyzeRequest):
    _validate_period(request.period)
    records = [_normalize_manual_record(record) for record in request.records]
    try:
        return DashboardAnalyzeResponse(
            overview=build_dashboard_overview(request.period, records),
            report=build_management_report_from_records(request.period, records),
        )
    except ValueError as error:
        raise _to_http_error(error) from error


@router.post("/import/excel")
async def import_excel(file: UploadFile = File(...)):
    content = await read_validated_upload(
        file,
        max_bytes=MAX_EXCEL_UPLOAD_BYTES,
        allowed_extensions=EXCEL_EXTENSIONS,
        allowed_content_types=EXCEL_CONTENT_TYPES,
        required_magic_prefixes=(b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    )
    try:
        return parse_finance_workbook(BytesIO(content))
    except BadZipFile as error:
        raise HTTPException(status_code=400, detail="Excel 文件内容无效或已损坏。") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def _normalize_manual_record(record: MonthlyFinanceRecord) -> MonthlyFinanceRecord:
    updates: dict[str, float] = {}
    if record.tax_burden_rate > 1:
        updates["tax_burden_rate"] = record.tax_burden_rate / 100
    if record.total_profit == 0 and record.net_profit != 0:
        updates["total_profit"] = record.net_profit
    if record.operating_cash_inflow == 0 and record.operating_cash_flow_net > 0:
        updates["operating_cash_inflow"] = record.operating_cash_flow_net
    if record.operating_cash_outflow == 0 and record.operating_cash_flow_net < 0:
        updates["operating_cash_outflow"] = abs(record.operating_cash_flow_net)
    if record.customer_collection == 0 and record.operating_cash_flow_net > 0:
        updates["customer_collection"] = record.operating_cash_flow_net
    if record.sales_orders == 0 and record.revenue > 0:
        updates["sales_orders"] = record.revenue
    if record.purchase_amount == 0 and record.cost > 0:
        updates["purchase_amount"] = record.cost
    return record.model_copy(update=updates) if updates else record
