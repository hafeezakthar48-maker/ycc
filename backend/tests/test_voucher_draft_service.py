from decimal import Decimal

from app.models.voucher import VoucherDraftRequest
from app.services.voucher_service import generate_voucher_draft


def test_generate_expense_purchase_voucher_draft_is_balanced():
    response = generate_voucher_draft(
        VoucherDraftRequest(
            business_type="expense_purchase",
            voucher_date="2026-06-30",
            counterparty="上海云智科技有限公司",
            amount=Decimal("1000.00"),
            tax_amount=Decimal("60.00"),
            total_amount_with_tax=Decimal("1060.00"),
            payment_status="unpaid",
            memo="办公服务费",
        )
    )

    assert response.scenario_label == "费用采购"
    assert response.balanced is True
    assert response.debit_total == Decimal("1060.00")
    assert response.credit_total == Decimal("1060.00")
    lines = {(line.account_name, line.direction): line.amount for line in response.lines}
    assert lines[("管理费用", "借")] == Decimal("1000.00")
    assert lines[("应交税费-应交增值税（进项税额）", "借")] == Decimal("60.00")
    assert lines[("应付账款", "贷")] == Decimal("1060.00")
    assert response.risks == []
    assert response.requires_human_review is True
    assert {citation.title for citation in response.citations} >= {"中华人民共和国发票管理办法", "中华人民共和国增值税暂行条例"}


def test_generate_sales_revenue_voucher_draft_uses_output_vat():
    response = generate_voucher_draft(
        VoucherDraftRequest(
            business_type="sales_revenue",
            voucher_date="2026-06-30",
            counterparty="示例制造企业",
            amount=Decimal("1000.00"),
            tax_amount=Decimal("60.00"),
            total_amount_with_tax=Decimal("1060.00"),
            payment_status="paid",
            memo="商品销售收入",
        )
    )

    lines = {(line.account_name, line.direction): line.amount for line in response.lines}
    assert response.scenario_label == "销售收入"
    assert response.balanced is True
    assert lines[("银行存款", "借")] == Decimal("1060.00")
    assert lines[("主营业务收入", "贷")] == Decimal("1000.00")
    assert lines[("应交税费-应交增值税（销项税额）", "贷")] == Decimal("60.00")


def test_generate_voucher_draft_flags_unbalanced_amount_mismatch():
    response = generate_voucher_draft(
        VoucherDraftRequest(
            business_type="inventory_purchase",
            voucher_date="2026-06-30",
            counterparty="上海云智科技有限公司",
            amount=Decimal("1000.00"),
            tax_amount=Decimal("60.00"),
            total_amount_with_tax=Decimal("1099.00"),
            payment_status="unpaid",
            memo="采购库存商品",
        )
    )

    risk_ids = {risk.id for risk in response.risks}
    assert response.balanced is False
    assert "amount_mismatch" in risk_ids
    assert "voucher_not_balanced" in risk_ids
