from io import BytesIO
from zipfile import ZipFile

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _report_payload() -> dict:
    return {
        "period": "2026-06",
        "company_name": "测试企业",
        "title": "测试企业2026-06经营分析报告",
        "sections": [
            {
                "title": "利润分析",
                "content": "本期收入增长，毛利率保持稳定，期间费用需要继续复核。",
            },
            {
                "title": "风险提示",
                "content": "存在现金流和税负率复核事项，建议财务经理检查原始凭证。",
            },
        ],
    }


def test_export_report_docx_returns_downloadable_word_document():
    response = client.post("/api/v1/dashboard/report/export/docx", json=_report_payload())

    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "china-finance-report-2026-06.docx" in response.headers["content-disposition"]

    with ZipFile(BytesIO(response.content)) as document:
        document_xml = document.read("word/document.xml").decode("utf-8")

    assert "测试企业2026-06经营分析报告" in document_xml
    assert "利润分析" in document_xml


def test_export_report_pdf_returns_downloadable_pdf():
    response = client.post("/api/v1/dashboard/report/export/pdf", json=_report_payload())

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "china-finance-report-2026-06.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


def test_export_report_exposes_content_disposition_for_frontend_download_name():
    response = client.post(
        "/api/v1/dashboard/report/export/docx",
        headers={"Origin": "http://127.0.0.1:5173"},
        json=_report_payload(),
    )

    assert response.status_code == 200
    assert "Content-Disposition" in response.headers["access-control-expose-headers"]
