from io import BytesIO

from openpyxl import Workbook

from app.services.spreadsheet_import_service import parse_finance_workbook


def _workbook_bytes() -> BytesIO:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "财务数据"
    sheet.append(
        [
            "期间",
            "营业收入",
            "营业成本",
            "销售费用",
            "管理费用",
            "研发费用",
            "财务费用",
            "净利润",
            "货币资金",
            "应收账款",
            "存货",
            "固定资产",
            "资产总额",
            "短期借款",
            "应付账款",
            "负债总额",
            "所有者权益",
            "经营现金流净额",
            "投资现金流净额",
            "筹资现金流净额",
            "库存周转天数",
            "税负率",
        ]
    )
    sheet.append(
        [
            "2026-06",
            1286,
            880,
            78,
            62,
            28,
            15,
            146,
            402,
            428,
            482,
            828,
            2216,
            242,
            276,
            812,
            1404,
            92,
            -42,
            12,
            74,
            0.038,
        ]
    )

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


def test_parse_finance_workbook_recognizes_chinese_headers():
    preview = parse_finance_workbook(_workbook_bytes())

    assert preview.sheet_name == "财务数据"
    assert preview.records[0].period == "2026-06"
    assert preview.records[0].revenue == 1286
    assert preview.records[0].operating_cash_flow_net == 92
    assert preview.records[0].tax_burden_rate == 0.038
    assert "营业收入" in preview.matched_fields
