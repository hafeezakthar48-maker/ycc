from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_overview_endpoint_returns_dashboard_payload():
    response = client.get("/api/v1/dashboard/overview?period=2026-06")

    assert response.status_code == 200
    payload = response.json()
    assert payload["period"] == "2026-06"
    assert payload["metrics"]
    assert payload["trend_series"]
    assert payload["risks"]


def test_unknown_period_returns_404():
    response = client.get("/api/v1/dashboard/overview?period=2030-01")

    assert response.status_code == 404
    assert "可用期间" in response.json()["detail"]


def test_bad_period_returns_422():
    response = client.get("/api/v1/dashboard/overview?period=202606")

    assert response.status_code == 422
    assert "YYYY-MM" in response.json()["detail"]


def test_excel_template_endpoint_downloads_xlsx_with_expected_headers():
    response = client.get("/api/v1/dashboard/template/excel")

    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "finance-analysis-template.xlsx" in response.headers["content-disposition"]

    workbook = load_workbook(BytesIO(response.content), data_only=True)
    sheet = workbook["财务数据模板"]
    headers = [cell.value for cell in sheet[1]]

    assert headers == [
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
    assert sheet["A2"].value == "2026-06"
    assert workbook["填报说明"]["A1"].value == "填报说明"


def test_excel_import_rejects_oversized_upload():
    response = client.post(
        "/api/v1/dashboard/import/excel",
        files={
            "file": (
                "oversized.xlsx",
                b"PK\x03\x04" + (b"0" * (5 * 1024 * 1024 + 1)),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 413


def test_excel_import_rejects_mismatched_content_type():
    response = client.post(
        "/api/v1/dashboard/import/excel",
        files={"file": ("finance.xlsx", b"<html></html>", "text/html")},
    )

    assert response.status_code == 400


def test_report_endpoint_contains_required_sections():
    response = client.get("/api/v1/dashboard/report?period=2026-06")

    assert response.status_code == 200
    titles = {section["title"] for section in response.json()["sections"]}
    assert {"利润分析", "资金分析", "风险提示", "管理建议"}.issubset(titles)


def test_analyze_endpoint_uses_submitted_manual_records():
    response = client.post(
        "/api/v1/dashboard/analyze",
        json={
            "period": "2026-06",
            "records": [
                {
                    "period": "2026-05",
                    "revenue": 1000,
                    "cost": 700,
                    "sales_expense": 50,
                    "admin_expense": 40,
                    "rd_expense": 20,
                    "finance_expense": 10,
                    "total_profit": 180,
                    "net_profit": 135,
                    "cash": 300,
                    "accounts_receivable": 300,
                    "inventory": 360,
                    "fixed_assets": 780,
                    "total_assets": 1900,
                    "short_term_loans": 220,
                    "accounts_payable": 240,
                    "total_liabilities": 720,
                    "owner_equity": 1180,
                    "operating_cash_inflow": 900,
                    "operating_cash_outflow": 820,
                    "operating_cash_flow_net": 80,
                    "investing_cash_flow_net": -30,
                    "financing_cash_flow_net": 8,
                    "customer_collection": 860,
                    "sales_orders": 1020,
                    "purchase_amount": 560,
                    "inventory_turnover_days": 66,
                    "tax_burden_rate": 0.045,
                },
                {
                    "period": "2026-06",
                    "revenue": 1500,
                    "cost": 960,
                    "sales_expense": 90,
                    "admin_expense": 70,
                    "rd_expense": 32,
                    "finance_expense": 18,
                    "total_profit": 330,
                    "net_profit": 248,
                    "cash": 430,
                    "accounts_receivable": 450,
                    "inventory": 510,
                    "fixed_assets": 830,
                    "total_assets": 2300,
                    "short_term_loans": 240,
                    "accounts_payable": 280,
                    "total_liabilities": 830,
                    "owner_equity": 1470,
                    "operating_cash_inflow": 1120,
                    "operating_cash_outflow": 980,
                    "operating_cash_flow_net": 140,
                    "investing_cash_flow_net": -46,
                    "financing_cash_flow_net": 10,
                    "customer_collection": 1080,
                    "sales_orders": 1510,
                    "purchase_amount": 700,
                    "inventory_turnover_days": 72,
                    "tax_burden_rate": 0.039,
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["overview"]["period"] == "2026-06"
    assert payload["overview"]["metrics"][0]["value"] == "¥1,500万"
    assert payload["report"]["sections"]


def test_analyze_endpoint_normalizes_manual_percent_tax_rate():
    response = client.post(
        "/api/v1/dashboard/analyze",
        json={
            "period": "2026-06",
            "records": [
                {
                    "period": "2026-06",
                    "revenue": 1500,
                    "cost": 960,
                    "sales_expense": 90,
                    "admin_expense": 70,
                    "rd_expense": 32,
                    "finance_expense": 18,
                    "total_profit": 330,
                    "net_profit": 248,
                    "cash": 430,
                    "accounts_receivable": 450,
                    "inventory": 510,
                    "fixed_assets": 830,
                    "total_assets": 2300,
                    "short_term_loans": 240,
                    "accounts_payable": 280,
                    "total_liabilities": 830,
                    "owner_equity": 1470,
                    "operating_cash_inflow": 1120,
                    "operating_cash_outflow": 980,
                    "operating_cash_flow_net": 140,
                    "investing_cash_flow_net": -46,
                    "financing_cash_flow_net": 10,
                    "customer_collection": 1080,
                    "sales_orders": 1510,
                    "purchase_amount": 700,
                    "inventory_turnover_days": 72,
                    "tax_burden_rate": 3.9,
                }
            ],
        },
    )

    assert response.status_code == 200
    tax_risk = [
        risk
        for risk in response.json()["overview"]["risks"]
        if risk["title"] == "税负率需复核"
    ][0]
    assert "3.9%" in tax_risk["trigger_reason"]
