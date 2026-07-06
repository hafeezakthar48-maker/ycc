from io import BytesIO

from openpyxl import Workbook

from app.services.spreadsheet_import_service import parse_finance_workbook


def test_parse_finance_workbook_returns_field_mapping_confirmation():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Finance"
    sheet.append(["period", "revenue", "cost", "net_profit", "operating_cash_flow_net"])
    sheet.append(["2026-06", 1200, 800, 160, 90])
    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    preview = parse_finance_workbook(output)

    revenue_mapping = [
        mapping for mapping in preview.field_mappings if mapping.field == "revenue"
    ][0]
    optional_tax_mapping = [
        mapping for mapping in preview.field_mappings if mapping.field == "tax_burden_rate"
    ][0]

    assert revenue_mapping.label == "营业收入"
    assert revenue_mapping.source_header == "revenue"
    assert revenue_mapping.required is True
    assert revenue_mapping.matched is True
    assert revenue_mapping.status == "matched"
    assert optional_tax_mapping.label == "税负率"
    assert optional_tax_mapping.source_header is None
    assert optional_tax_mapping.required is False
    assert optional_tax_mapping.matched is False
    assert optional_tax_mapping.status == "missing_optional"
