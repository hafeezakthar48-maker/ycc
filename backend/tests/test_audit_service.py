from decimal import Decimal

from app.models.audit import AuditRequest, AuditVoucherLine
from app.services.audit_service import review_audit_subject


def _clean_lines() -> list[AuditVoucherLine]:
    return [
        AuditVoucherLine(
            account_code="6602",
            account_name="管理费用",
            direction="借",
            amount=Decimal("1000.00"),
            explanation="办公服务费",
        ),
        AuditVoucherLine(
            account_code="22210101",
            account_name="应交税费-应交增值税（进项税额）",
            direction="借",
            amount=Decimal("60.00"),
            explanation="进项税额",
        ),
        AuditVoucherLine(
            account_code="2202",
            account_name="应付账款",
            direction="贷",
            amount=Decimal("1060.00"),
            explanation="应付未付款",
        ),
    ]


def test_review_clean_voucher_returns_pass_rating():
    response = review_audit_subject(
        AuditRequest(
            audit_subject="voucher",
            voucher_date="2026-06-30",
            summary="办公服务费；交易对方：上海云智科技有限公司",
            counterparty="上海云智科技有限公司",
            invoice_number="12345678",
            amount=Decimal("1000.00"),
            tax_amount=Decimal("60.00"),
            total_amount_with_tax=Decimal("1060.00"),
            lines=_clean_lines(),
        )
    )

    assert response.rating == "通过"
    assert response.score >= 90
    assert response.findings == []
    assert {check.id: check.status for check in response.checks}["voucher_balanced"] == "pass"
    assert {citation.title for citation in response.citations} >= {"中华人民共和国发票管理办法", "中华人民共和国增值税暂行条例"}
    assert response.requires_human_review is True


def test_review_voucher_flags_unbalanced_and_amount_mismatch():
    lines = _clean_lines()
    lines[2] = AuditVoucherLine(
        account_code="2202",
        account_name="应付账款",
        direction="贷",
        amount=Decimal("1099.00"),
        explanation="错误的应付金额",
    )

    response = review_audit_subject(
        AuditRequest(
            audit_subject="voucher",
            voucher_date="2026-06-30",
            summary="采购库存商品",
            counterparty="上海云智科技有限公司",
            invoice_number="12345678",
            amount=Decimal("1000.00"),
            tax_amount=Decimal("60.00"),
            total_amount_with_tax=Decimal("1099.00"),
            lines=lines,
        )
    )

    finding_ids = {finding.id for finding in response.findings}
    assert response.rating == "高风险"
    assert "voucher_not_balanced" in finding_ids
    assert "amount_mismatch" in finding_ids
    assert response.score < 80


def test_review_voucher_flags_vat_direction_error_and_missing_invoice_number():
    lines = [
        AuditVoucherLine(
            account_code="22210101",
            account_name="应交税费-应交增值税（进项税额）",
            direction="贷",
            amount=Decimal("60.00"),
            explanation="进项税额方向错误",
        ),
        AuditVoucherLine(
            account_code="2202",
            account_name="应付账款",
            direction="借",
            amount=Decimal("60.00"),
            explanation="平衡行",
        ),
    ]

    response = review_audit_subject(
        AuditRequest(
            audit_subject="voucher",
            voucher_date="2026-06-30",
            summary="办公服务费",
            counterparty="上海云智科技有限公司",
            invoice_number="",
            amount=Decimal("0.00"),
            tax_amount=Decimal("60.00"),
            total_amount_with_tax=Decimal("60.00"),
            lines=lines,
        )
    )

    finding_ids = {finding.id for finding in response.findings}
    assert "vat_direction_error" in finding_ids
    assert "missing_invoice_number" in finding_ids
    assert response.rating == "需复核"
