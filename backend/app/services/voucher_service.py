from decimal import Decimal

from app.models.finance_qa import FinanceCitation
from app.models.voucher import VoucherDraftRequest, VoucherDraftResponse, VoucherLine, VoucherRiskItem
from app.services.policy_library_service import find_policy_by_id


CENT = Decimal("0.01")

SCENARIOS = {
    "expense_purchase": {
        "label": "费用采购",
        "debit_account_code": "6602",
        "debit_account_name": "管理费用",
        "debit_explanation": "按不含税金额确认期间费用。",
    },
    "inventory_purchase": {
        "label": "库存采购",
        "debit_account_code": "1405",
        "debit_account_name": "库存商品",
        "debit_explanation": "按不含税金额确认库存商品成本。",
    },
    "sales_revenue": {
        "label": "销售收入",
        "credit_account_code": "6001",
        "credit_account_name": "主营业务收入",
        "credit_explanation": "按不含税金额确认主营业务收入。",
    },
}


def generate_voucher_draft(request: VoucherDraftRequest) -> VoucherDraftResponse:
    scenario = SCENARIOS.get(request.business_type)
    if not scenario:
        return _unsupported_response(request)

    lines = _build_lines(request, scenario)
    debit_total = _sum_lines(lines, "借")
    credit_total = _sum_lines(lines, "贷")
    balanced = debit_total == credit_total
    risks = _build_risks(request, debit_total, credit_total, balanced)

    return VoucherDraftResponse(
        scenario_label=scenario["label"],
        voucher_date=request.voucher_date,
        summary=_summary(request, scenario["label"]),
        lines=lines,
        debit_total=debit_total,
        credit_total=credit_total,
        balanced=balanced,
        risks=risks,
        suggestions=_suggestions(request),
        citations=_citations(request),
    )


def _build_lines(request: VoucherDraftRequest, scenario: dict[str, str]) -> list[VoucherLine]:
    amount = _money(request.amount)
    tax_amount = _money(request.tax_amount)
    total_amount_with_tax = _money(request.total_amount_with_tax)
    settlement_account = _settlement_account(request)

    if request.business_type == "sales_revenue":
        return [
            VoucherLine(
                account_code=settlement_account["code"],
                account_name=settlement_account["name"],
                direction="借",
                amount=total_amount_with_tax,
                explanation="按含税价款确认应收或收款金额。",
            ),
            VoucherLine(
                account_code=scenario["credit_account_code"],
                account_name=scenario["credit_account_name"],
                direction="贷",
                amount=amount,
                explanation=scenario["credit_explanation"],
            ),
            VoucherLine(
                account_code="22210102",
                account_name="应交税费-应交增值税（销项税额）",
                direction="贷",
                amount=tax_amount,
                explanation="按发票税额确认销项税额。",
            ),
        ]

    return [
        VoucherLine(
            account_code=scenario["debit_account_code"],
            account_name=scenario["debit_account_name"],
            direction="借",
            amount=amount,
            explanation=scenario["debit_explanation"],
        ),
        VoucherLine(
            account_code="22210101",
            account_name="应交税费-应交增值税（进项税额）",
            direction="借",
            amount=tax_amount,
            explanation="按发票税额暂列进项税额，正式抵扣需复核发票和业务真实性。",
        ),
        VoucherLine(
            account_code=settlement_account["code"],
            account_name=settlement_account["name"],
            direction="贷",
            amount=total_amount_with_tax,
            explanation="按含税价款确认应付或付款金额。",
        ),
    ]


def _settlement_account(request: VoucherDraftRequest) -> dict[str, str]:
    if request.payment_status == "paid":
        return {"code": "1002", "name": "银行存款"}
    if request.business_type == "sales_revenue":
        return {"code": "1122", "name": "应收账款"}
    return {"code": "2202", "name": "应付账款"}


def _sum_lines(lines: list[VoucherLine], direction: str) -> Decimal:
    return sum((line.amount for line in lines if line.direction == direction), Decimal("0.00")).quantize(CENT)


def _build_risks(
    request: VoucherDraftRequest,
    debit_total: Decimal,
    credit_total: Decimal,
    balanced: bool,
) -> list[VoucherRiskItem]:
    risks: list[VoucherRiskItem] = []
    if abs(_money(request.amount + request.tax_amount) - _money(request.total_amount_with_tax)) > Decimal("0.02"):
        risks.append(
            VoucherRiskItem(
                id="amount_mismatch",
                title="价税合计与金额税额不一致",
                level=4,
                description="凭证草稿中的不含税金额和税额之和，与价税合计不一致。",
                suggestion="请复核发票原件、OCR 识别结果和合同结算金额，再决定是否生成正式凭证。",
            )
        )

    if not balanced:
        risks.append(
            VoucherRiskItem(
                id="voucher_not_balanced",
                title="借贷不平衡",
                level=5,
                description=f"借方合计 {debit_total}，贷方合计 {credit_total}，不符合借贷记账法平衡要求。",
                suggestion="禁止直接入账，请先修正金额、税额或结算金额。",
            )
        )

    return risks


def _suggestions(request: VoucherDraftRequest) -> list[str]:
    common = [
        "正式入账前请复核发票、合同、订单、验收或交付记录、付款流水。",
        "本功能只生成凭证草稿，不替代财务人员审核、制单、复核和记账。",
    ]
    if request.business_type == "sales_revenue":
        return [
            "确认收入是否满足企业会计准则下的履约义务和控制权转移条件。",
            "核对销项税额、纳税义务发生时间和开票金额。",
            *common,
        ]
    return [
        "确认交易真实、发票抬头和纳税人识别号与企业档案一致。",
        "进项税额能否抵扣需结合发票类型、用途、认证勾选和最新税收政策复核。",
        *common,
    ]


def _citations(request: VoucherDraftRequest) -> list[FinanceCitation]:
    policy_ids = ["invoice-management-measures", "vat-temporary-regulations"]
    if request.business_type == "sales_revenue":
        policy_ids.append("cas-14-revenue-2017")

    citations: list[FinanceCitation] = []
    for policy_id in policy_ids:
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


def _summary(request: VoucherDraftRequest, label: str) -> str:
    memo = request.memo.strip() or label
    return f"{memo}；交易对方：{request.counterparty}"


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT)


def _unsupported_response(request: VoucherDraftRequest) -> VoucherDraftResponse:
    return VoucherDraftResponse(
        scenario_label="未支持业务",
        voucher_date=request.voucher_date,
        summary=_summary(request, "未支持业务"),
        lines=[],
        debit_total=Decimal("0.00"),
        credit_total=Decimal("0.00"),
        balanced=False,
        risks=[
            VoucherRiskItem(
                id="unsupported_business_type",
                title="暂不支持该业务类型",
                level=3,
                description=f"当前 MVP 暂不支持 {request.business_type} 的自动凭证草稿生成。",
                suggestion="请选择费用采购、库存采购或销售收入场景，或由财务人员手动编制凭证。",
            )
        ],
        suggestions=["请补充业务类型、交易单据、合同、发票和付款资料后人工判断。"],
        citations=_citations(request),
    )
