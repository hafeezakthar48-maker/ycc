from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_invoice_ocr_recognize_text_endpoint_returns_fields():
    response = client.post(
        "/api/v1/invoice-ocr/recognize-text",
        json={
            "text": "\n".join(
                [
                    "增值税电子普通发票",
                    "发票号码：87654321",
                    "销售方纳税人识别号：91310115MA1K000002",
                    "金额：200.00",
                    "税额：12.00",
                    "价税合计（小写）¥212.00",
                ]
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    fields = {field["key"]: field["value"] for field in payload["fields"]}
    assert payload["engine_status"] == "text_parsed"
    assert fields["invoice_number"] == "87654321"
    assert payload["citations"][0]["title"] == "中华人民共和国发票管理办法"


def test_invoice_ocr_upload_image_without_engine_returns_missing_status():
    response = client.post(
        "/api/v1/invoice-ocr/upload",
        files={"file": ("invoice.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["engine_status"] == "missing"
    assert payload["fields"] == []
    assert "未配置 OCR 引擎" in payload["warnings"][0]


def test_invoice_ocr_upload_rejects_unsupported_text_subtype():
    response = client.post(
        "/api/v1/invoice-ocr/upload",
        files={"file": ("invoice.html", b"<script>alert(1)</script>", "text/html")},
    )

    assert response.status_code == 400


def test_invoice_ocr_upload_rejects_oversized_text_file():
    response = client.post(
        "/api/v1/invoice-ocr/upload",
        files={"file": ("invoice.txt", b"0" * (1024 * 1024 + 1), "text/plain")},
    )

    assert response.status_code == 413
