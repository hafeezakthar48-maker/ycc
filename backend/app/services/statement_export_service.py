from __future__ import annotations

from dataclasses import dataclass
from html import escape
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from app.models.financial_statement import FinancialStatementBundle, StatementLineItem
from app.models.statement_archive import StatementSnapshot


EXCEL_STATEMENT_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF_STATEMENT_MIME_TYPE = "application/pdf"


@dataclass(frozen=True)
class StatementExportPayload:
    filename: str
    content_type: str
    content: bytes


def statement_export_filename(snapshot: StatementSnapshot, export_format: str) -> str:
    return f"financial-statements-{snapshot.account_set_id}-{snapshot.period}-v{snapshot.version}.{export_format}"


def build_statement_export(snapshot: StatementSnapshot, export_format: str) -> StatementExportPayload:
    if export_format == "xlsx":
        return StatementExportPayload(
            filename=statement_export_filename(snapshot, "xlsx"),
            content_type=EXCEL_STATEMENT_MIME_TYPE,
            content=build_statement_xlsx(snapshot),
        )
    if export_format == "pdf":
        return StatementExportPayload(
            filename=statement_export_filename(snapshot, "pdf"),
            content_type=PDF_STATEMENT_MIME_TYPE,
            content=build_statement_pdf(snapshot),
        )
    raise ValueError(f"不支持的报表导出格式：{export_format}")


def build_statement_xlsx(snapshot: StatementSnapshot) -> bytes:
    output = BytesIO()
    sheets = _statement_sheets(snapshot.bundle)
    with ZipFile(output, "w", ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", _xlsx_content_types(len(sheets)))
        package.writestr("_rels/.rels", _xlsx_root_relationships())
        package.writestr("xl/workbook.xml", _xlsx_workbook(sheets))
        package.writestr("xl/_rels/workbook.xml.rels", _xlsx_workbook_relationships(len(sheets)))
        for index, sheet in enumerate(sheets, start=1):
            package.writestr(f"xl/worksheets/sheet{index}.xml", _xlsx_sheet(sheet["rows"]))
    return output.getvalue()


def build_statement_pdf(snapshot: StatementSnapshot) -> bytes:
    lines = _pdf_lines(snapshot)
    content = _pdf_content_stream(lines)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type0 /BaseFont /STSong-Light "
        b"/Encoding /UniGB-UCS2-H /DescendantFonts [6 0 R] >>",
        f"<< /Length {len(content)} >>\nstream\n".encode("ascii") + content + b"\nendstream",
        b"<< /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light "
        b"/CIDSystemInfo << /Registry (Adobe) /Ordering (GB1) /Supplement 2 >> "
        b"/FontDescriptor 7 0 R >>",
        b"<< /Type /FontDescriptor /FontName /STSong-Light /Flags 4 "
        b"/FontBBox [-25 -254 1000 880] /ItalicAngle 0 /Ascent 880 "
        b"/Descent -254 /CapHeight 880 /StemV 80 >>",
    ]
    return _assemble_pdf(objects)


def _statement_sheets(bundle: FinancialStatementBundle) -> list[dict]:
    return [
        {"name": "资产负债表", "rows": _statement_rows(bundle.balance_sheet.title, bundle.balance_sheet.items)},
        {"name": "利润表", "rows": _statement_rows(bundle.income_statement.title, bundle.income_statement.items)},
        {"name": "现金流量表", "rows": _statement_rows(bundle.cash_flow_statement.title, bundle.cash_flow_statement.items)},
        {"name": "所有者权益变动表", "rows": _statement_rows(bundle.equity_statement.title, bundle.equity_statement.items)},
        {"name": "校验结果", "rows": _validation_rows(bundle)},
        {"name": "追溯明细", "rows": _trace_rows(bundle)},
    ]


def _statement_rows(title: str, items: list[StatementLineItem]) -> list[list[str]]:
    rows = [[title, "", ""], ["项目编码", "项目名称", "金额", "取数口径"]]
    for item in items:
        rows.append([item.code, item.name, str(item.amount), item.formula])
    return rows


def _validation_rows(bundle: FinancialStatementBundle) -> list[list[str]]:
    rows = [["校验编码", "校验名称", "状态", "说明"]]
    for item in bundle.validation_items:
        rows.append([item.validation_code, item.validation_name, item.status, item.message])
    if len(rows) == 1:
        rows.append(["none", "校验结果", "passed", "当前报表无结构化校验项"])
    return rows


def _trace_rows(bundle: FinancialStatementBundle) -> list[list[str]]:
    rows = [["项目编码", "规则", "来源", "科目", "现金流项目", "公式", "金额"]]
    for item in bundle.trace_items:
        rows.append(
            [
                item.line_code,
                item.rule_id,
                item.source_type,
                " / ".join(item.source_account_codes),
                " / ".join(item.cash_flow_item_codes),
                item.formula,
                str(item.amount),
            ]
        )
    if len(rows) == 1:
        rows.append(["none", "legacy", "formula", "", "", "当前报表无追溯明细", "0.00"])
    return rows


def _xlsx_content_types(sheet_count: int) -> str:
    sheet_overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, sheet_count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        f"{sheet_overrides}</Types>"
    )


def _xlsx_root_relationships() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )


def _xlsx_workbook(sheets: list[dict]) -> str:
    sheet_xml = "".join(
        f'<sheet name="{escape(sheet["name"])}" sheetId="{index}" r:id="rId{index}"/>'
        for index, sheet in enumerate(sheets, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheet_xml}</sheets></workbook>"
    )


def _xlsx_workbook_relationships(sheet_count: int) -> str:
    relationships = "".join(
        f'<Relationship Id="rId{index}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, sheet_count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{relationships}</Relationships>"
    )


def _xlsx_sheet(rows: list[list[str]]) -> str:
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            cell_ref = f"{chr(64 + column_index)}{row_index}"
            cells.append(f'<c r="{cell_ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>')
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_xml)}</sheetData></worksheet>'
    )


def _pdf_lines(snapshot: StatementSnapshot) -> list[tuple[str, int]]:
    bundle = snapshot.bundle
    return [
        ("财务报表", 18),
        (f"企业：{snapshot.company_name}", 11),
        (f"期间：{snapshot.period}", 11),
        (f"账套：{snapshot.account_set_id}", 11),
        (f"版本：v{snapshot.version}", 11),
        (f"内容哈希：{snapshot.content_hash[:16]}", 8),
        ("资产负债表", 13),
        (f"资产合计：{bundle.balance_sheet.total_assets}", 10),
        (f"负债和权益合计：{bundle.balance_sheet.total_liabilities_and_equity}", 10),
        ("利润表", 13),
        (f"营业收入：{bundle.income_statement.total_revenue}", 10),
        (f"净利润：{bundle.income_statement.net_profit}", 10),
        ("现金流量表", 13),
        (f"现金净增加额：{bundle.cash_flow_statement.net_cash_flow}", 10),
        ("所有者权益变动表", 13),
        (f"期末权益：{bundle.equity_statement.closing_equity}", 10),
        ("校验状态", 13),
        (snapshot.validation_status, 10),
    ]


def _pdf_content_stream(lines: list[tuple[str, int]]) -> bytes:
    commands: list[str] = []
    y = 790
    for text, size in lines:
        if y < 70:
            break
        if not text:
            y -= 10
            continue
        encoded = text.encode("utf-16-be").hex().upper()
        commands.append(f"BT /F1 {size} Tf 52 {y} Td <{encoded}> Tj ET")
        y -= size + 8
    return "\n".join(commands).encode("ascii")


def _assemble_pdf(objects: list[bytes]) -> bytes:
    output = BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = [0]
    for index, payload in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{index} 0 obj\n".encode("ascii"))
        output.write(payload)
        output.write(b"\nendobj\n")

    xref_position = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.write(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_position}\n%%EOF".encode("ascii")
    )
    return output.getvalue()
