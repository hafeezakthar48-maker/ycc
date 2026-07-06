from app.models.invoice_ocr import InvoiceOcrRequest
from app.services.invoice_ocr_service import recognize_invoice_text


SAMPLE_INVOICE_TEXT = """
增值税电子普通发票
发票代码：044032300111
发票号码：12345678
开票日期：2026年06月30日
购买方名称：示例制造企业
购买方纳税人识别号：91310000MA1TEST001
销售方名称：上海云智科技有限公司
销售方纳税人识别号：91310115MA1K000002
金额：1000.00
税额：60.00
价税合计（大写）：壹仟零陆拾元整 （小写）¥1060.00
"""


def test_recognize_invoice_text_extracts_core_fields_with_citations():
    response = recognize_invoice_text(InvoiceOcrRequest(text=SAMPLE_INVOICE_TEXT))

    fields = {field.key: field.value for field in response.fields}
    assert response.engine_status == "text_parsed"
    assert response.invoice_type == "增值税电子普通发票"
    assert fields["invoice_number"] == "12345678"
    assert fields["seller_tax_id"] == "91310115MA1K000002"
    assert fields["total_amount"] == "1000.00"
    assert fields["tax_amount"] == "60.00"
    assert fields["total_amount_with_tax"] == "1060.00"
    assert response.risks == []
    assert response.citations
    assert response.citations[0].title == "中华人民共和国发票管理办法"


def test_recognize_invoice_text_flags_amount_mismatch_risk():
    response = recognize_invoice_text(
        InvoiceOcrRequest(text=SAMPLE_INVOICE_TEXT.replace("¥1060.00", "¥1099.00"))
    )

    risk_ids = {risk.id for risk in response.risks}
    assert "amount_mismatch" in risk_ids


def test_recognize_invoice_text_flags_missing_required_invoice_fields():
    response = recognize_invoice_text(
        InvoiceOcrRequest(
            text="""
            增值税电子普通发票
            金额：100.00
            税额：6.00
            价税合计（小写）¥106.00
            """
        )
    )

    risk_ids = {risk.id for risk in response.risks}
    assert "missing_invoice_number" in risk_ids
    assert "missing_seller_tax_id" in risk_ids
