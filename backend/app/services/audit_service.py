from decimal import Decimal

from app.models.audit import AuditCheck, AuditFinding, AuditRequest, AuditResponse
from app.models.finance_qa import FinanceCitation
from app.services.policy_library_service import find_policy_by_id


CENT = Decimal("0.01")


def review_audit_subject(request: AuditRequest) -> AuditResponse:
    findings: list[AuditFinding] = []
    checks: list[AuditCheck] = []

    _check_voucher_balanced(request, checks, findings)
    _check_amount_tie_out(request, checks, findings)
    _check_required_metadata(request, checks, findings)
    _check_line_amounts(request, checks, findings)
    _check_vat_direction(request, checks, findings)

    score = _score(findings)
    return AuditResponse(
        rating=_rating(findings),
        score=score,
        checks=checks,
        findings=findings,
        suggestions=_suggestions(findings),
        citations=_citations(),
    )


def _check_voucher_balanced(
    request: AuditRequest,
    checks: list[AuditCheck],
    findings: list[AuditFinding],
) -> None:
    debit_total = _sum_lines(request, "借")
    credit_total = _sum_lines(request, "贷")
    if debit_total == credit_total:
        checks.append(
            AuditCheck(
                id="voucher_balanced",
                title="借贷平衡",
                status="pass",
                evidence=f"借方合计 {debit_total}，贷方合计 {credit_total}。",
            )
        )
        return

    checks.append(
        AuditCheck(
            id="voucher_balanced",
            title="借贷平衡",
            status="fail",
            evidence=f"借方合计 {debit_total}，贷方合计 {credit_total}。",
        )
    )
    findings.append(
        AuditFinding(
            id="voucher_not_balanced",
            title="凭证借贷不平衡",
            category="会计分录",
            severity=5,
            description="凭证分录不满足借贷记账法的基本平衡关系。",
            evidence=f"借方合计 {debit_total}，贷方合计 {credit_total}。",
            suggestion="禁止直接入账，请先复核分录方向、金额、税额和往来科目。",
        )
    )


def _check_amount_tie_out(
    request: AuditRequest,
    checks: list[AuditCheck],
    findings: list[AuditFinding],
) -> None:
    expected = _money(request.amount + request.tax_amount)
    actual = _money(request.total_amount_with_tax)
    if abs(expected - actual) <= Decimal("0.02"):
        checks.append(
            AuditCheck(
                id="amount_tie_out",
                title="价税勾稽",
                status="pass",
                evidence=f"金额 {request.amount} + 税额 {request.tax_amount} = {expected}。",
            )
        )
        return

    checks.append(
        AuditCheck(
            id="amount_tie_out",
            title="价税勾稽",
            status="fail",
            evidence=f"金额税额合计 {expected}，价税合计 {actual}。",
        )
    )
    findings.append(
        AuditFinding(
            id="amount_mismatch",
            title="价税合计不一致",
            category="发票金额",
            severity=4,
            description="发票或凭证中的不含税金额、税额和价税合计无法相互勾稽。",
            evidence=f"金额税额合计 {expected}，价税合计 {actual}。",
            suggestion="请复核发票原件、OCR 识别结果、合同结算金额和凭证金额。",
        )
    )


def _check_required_metadata(
    request: AuditRequest,
    checks: list[AuditCheck],
    findings: list[AuditFinding],
) -> None:
    required_items = [
        ("summary_present", "摘要", request.summary.strip(), "missing_summary", 2, "凭证摘要缺失"),
        ("counterparty_present", "交易对方", request.counterparty.strip(), "missing_counterparty", 3, "交易对方缺失"),
        ("invoice_number_present", "发票号码", (request.invoice_number or "").strip(), "missing_invoice_number", 3, "发票号码缺失"),
    ]

    for check_id, title, value, finding_id, severity, finding_title in required_items:
        if value:
            checks.append(AuditCheck(id=check_id, title=title, status="pass", evidence="已填写。"))
            continue
        checks.append(AuditCheck(id=check_id, title=title, status="warn", evidence="未填写或为空。"))
        findings.append(
            AuditFinding(
                id=finding_id,
                title=finding_title,
                category="单据完整性",
                severity=severity,
                description=f"{title}为空，影响业务真实性、重复入账或后续追溯。",
                evidence=f"{title}未填写。",
                suggestion=f"请补充{title}，并与发票、合同、订单、验收和付款流水交叉核对。",
            )
        )


def _check_line_amounts(
    request: AuditRequest,
    checks: list[AuditCheck],
    findings: list[AuditFinding],
) -> None:
    invalid_lines = [line for line in request.lines if line.amount <= 0]
    if not invalid_lines:
        checks.append(AuditCheck(id="line_amount_positive", title="分录金额", status="pass", evidence="所有分录金额均大于 0。"))
        return

    checks.append(AuditCheck(id="line_amount_positive", title="分录金额", status="fail", evidence=f"{len(invalid_lines)} 行金额小于或等于 0。"))
    findings.append(
        AuditFinding(
            id="non_positive_line_amount",
            title="分录金额异常",
            category="会计分录",
            severity=4,
            description="存在金额小于或等于 0 的分录行。",
            evidence="；".join(f"{line.account_name} {line.direction} {line.amount}" for line in invalid_lines),
            suggestion="请删除无效分录或修正金额后再审核。",
        )
    )


def _check_vat_direction(
    request: AuditRequest,
    checks: list[AuditCheck],
    findings: list[AuditFinding],
) -> None:
    errors: list[str] = []
    for line in request.lines:
        if "进项税额" in line.account_name and line.direction != "借":
            errors.append(f"{line.account_name} 应在借方，当前为{line.direction}方")
        if "销项税额" in line.account_name and line.direction != "贷":
            errors.append(f"{line.account_name} 应在贷方，当前为{line.direction}方")

    if not errors:
        checks.append(AuditCheck(id="vat_direction", title="增值税科目方向", status="pass", evidence="进项税额/销项税额方向未见异常。"))
        return

    checks.append(AuditCheck(id="vat_direction", title="增值税科目方向", status="fail", evidence="；".join(errors)))
    findings.append(
        AuditFinding(
            id="vat_direction_error",
            title="增值税科目方向异常",
            category="税务处理",
            severity=4,
            description="进项税额或销项税额的借贷方向与常见会计处理不一致。",
            evidence="；".join(errors),
            suggestion="请复核业务性质、发票类型、进销项税额方向和凭证模板。",
        )
    )


def _sum_lines(request: AuditRequest, direction: str) -> Decimal:
    return sum((line.amount for line in request.lines if line.direction == direction), Decimal("0.00")).quantize(CENT)


def _score(findings: list[AuditFinding]) -> int:
    score = 100
    penalties = {5: 35, 4: 25, 3: 15, 2: 8, 1: 5}
    for finding in findings:
        score -= penalties.get(finding.severity, 10)
    return max(0, score)


def _rating(findings: list[AuditFinding]) -> str:
    if any(finding.severity >= 5 for finding in findings):
        return "高风险"
    if findings:
        return "需复核"
    return "通过"


def _suggestions(findings: list[AuditFinding]) -> list[str]:
    if not findings:
        return [
            "本次规则审核未发现基础错误，正式入账前仍需财务人员复核原始单据。",
            "请留存发票、合同、订单、验收或交付记录、付款流水等证据链。",
        ]
    return [
        "先处理高星级错误，再复核警告项，修正后重新运行审核。",
        "涉及发票、税额、抵扣或收入确认的问题，应结合最新税务政策和企业会计政策复核。",
        "本模块仅作自动审核提示，不替代财务负责人、税务负责人或审计人员判断。",
    ]


def _citations() -> list[FinanceCitation]:
    citations: list[FinanceCitation] = []
    for policy_id in ("invoice-management-measures", "vat-temporary-regulations", "cas-14-revenue-2017"):
        document = find_policy_by_id(policy_id)
        if not document:
            continue
        citations.append(
            FinanceCitation(
                title=document.title,
                authority=document.authority,
                document_number=document.document_number,
                published_date=document.published_date,
                status=document.status,
                source_url=document.source_url,
                updated_at=document.updated_at,
            )
        )
    return citations


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT)
