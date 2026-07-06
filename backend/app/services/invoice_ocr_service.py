import re
from decimal import Decimal, InvalidOperation

from app.models.finance_qa import FinanceCitation
from app.models.invoice_ocr import InvoiceField, InvoiceOcrRequest, InvoiceOcrResponse, InvoiceRiskItem
from app.services.policy_library_service import find_policy_by_id


FIELD_LABELS: tuple[tuple[str, str], ...] = (
    ("invoice_code", "发票代码"),
    ("invoice_number", "发票号码"),
    ("issue_date", "开票日期"),
    ("buyer_name", "购买方名称"),
    ("buyer_tax_id", "购买方纳税人识别号"),
    ("seller_name", "销售方名称"),
    ("seller_tax_id", "销售方纳税人识别号"),
    ("total_amount", "金额"),
    ("tax_amount", "税额"),
    ("total_amount_with_tax", "价税合计"),
)


def recognize_invoice_text(request: InvoiceOcrRequest) -> InvoiceOcrResponse:
    parsed = _parse_invoice_text(request.text)
    return InvoiceOcrResponse(
        engine_status="text_parsed",
        invoice_type=parsed.get("invoice_type"),
        fields=[
            InvoiceField(
                key=key,
                label=label,
                value=parsed.get(key),
                confidence=0.88 if parsed.get(key) else 0.0,
            )
            for key, label in FIELD_LABELS
        ],
        risks=_build_risks(parsed),
        warnings=[],
        citations=_invoice_citations(),
    )


def missing_ocr_engine_response(filename: str | None = None) -> InvoiceOcrResponse:
    file_note = f"文件 {filename} " if filename else ""
    return InvoiceOcrResponse(
        engine_status="missing",
        invoice_type=None,
        fields=[],
        risks=[],
        warnings=[
            f"{file_note}当前运行环境未配置 OCR 引擎，请安装本地 OCR 引擎或接入可信 OCR 服务后重新识别；系统不会伪造图片/PDF 识别结果。"
        ],
        citations=_invoice_citations(),
    )


def _parse_invoice_text(text: str) -> dict[str, str]:
    lines = [_normalize_line(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    parsed: dict[str, str] = {}

    parsed["invoice_type"] = next((line for line in lines if "发票" in line and "号码" not in line and "代码" not in line), "")

    for line in lines:
        if line.startswith("发票代码"):
            parsed["invoice_code"] = _extract_after_colon(line)
        elif line.startswith("发票号码"):
            parsed["invoice_number"] = _extract_after_colon(line)
        elif line.startswith("开票日期"):
            parsed["issue_date"] = _normalize_date(_extract_after_colon(line))
        elif line.startswith("购买方名称"):
            parsed["buyer_name"] = _extract_after_colon(line)
        elif line.startswith("购买方纳税人识别号"):
            parsed["buyer_tax_id"] = _extract_after_colon(line)
        elif line.startswith("销售方名称"):
            parsed["seller_name"] = _extract_after_colon(line)
        elif line.startswith("销售方纳税人识别号"):
            parsed["seller_tax_id"] = _extract_after_colon(line)
        elif line.startswith("金额"):
            parsed["total_amount"] = _extract_money(line)
        elif line.startswith("税额"):
            parsed["tax_amount"] = _extract_money(line)
        elif "价税合计" in line or "小写" in line:
            parsed["total_amount_with_tax"] = _extract_money(line)

    return {key: value for key, value in parsed.items() if value}


def _normalize_line(line: str) -> str:
    return line.strip().replace("：", ":").replace("￥", "¥")


def _extract_after_colon(line: str) -> str:
    return line.split(":", 1)[1].strip() if ":" in line else ""


def _normalize_date(value: str) -> str:
    match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", value)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return value


def _extract_money(line: str) -> str:
    matches = re.findall(r"[¥]?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})|[0-9]+(?:\.[0-9]{1,2})?)", line)
    return matches[-1].replace(",", "") if matches else ""


def _build_risks(parsed: dict[str, str]) -> list[InvoiceRiskItem]:
    risks: list[InvoiceRiskItem] = []
    if not parsed.get("invoice_number"):
        risks.append(
            InvoiceRiskItem(
                id="missing_invoice_number",
                title="发票号码缺失",
                level=4,
                description="OCR 文本中未识别到发票号码，无法完成发票唯一性和重复入账检查。",
                suggestion="请重新上传更清晰的发票或手动补录发票号码，并与电子发票服务平台记录核对。",
            )
        )

    if not parsed.get("seller_tax_id"):
        risks.append(
            InvoiceRiskItem(
                id="missing_seller_tax_id",
                title="销售方纳税人识别号缺失",
                level=3,
                description="OCR 文本中未识别到销售方纳税人识别号，影响交易对手和发票真实性复核。",
                suggestion="请核对发票原件、供应商档案、合同和付款记录，确认开票主体一致。",
            )
        )

    amount = _to_decimal(parsed.get("total_amount"))
    tax = _to_decimal(parsed.get("tax_amount"))
    amount_with_tax = _to_decimal(parsed.get("total_amount_with_tax"))

    if amount is not None and tax is not None and amount_with_tax is not None:
        if abs((amount + tax) - amount_with_tax) > Decimal("0.02"):
            risks.append(
                InvoiceRiskItem(
                    id="amount_mismatch",
                    title="价税合计勾稽异常",
                    level=4,
                    description="发票金额与税额相加后，与价税合计不一致。",
                    suggestion="请复核 OCR 识别结果、发票原件、开票系统数据以及入账金额，避免错误抵扣或入账。",
                )
            )

    return risks


def _to_decimal(value: str | None) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _invoice_citations() -> list[FinanceCitation]:
    document = find_policy_by_id("invoice-management-measures")
    if not document:
        return []
    return [
        FinanceCitation(
            title=document.title,
            authority=document.authority,
            document_number=document.document_number,
            published_date=document.published_date,
            status=document.status,
            source_url=document.source_url,
            updated_at=document.updated_at,
        )
    ]
