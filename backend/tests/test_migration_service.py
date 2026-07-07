from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.voucher_center import VoucherCenterCreateRequest, VoucherCenterLine
from app.services.accounting_period_service import reset_accounting_period_store
from app.services.accounting_service import list_journal_entries, reset_accounting_store
from app.services.integrity_check_service import run_accounting_integrity_checks
from app.services.migration_service import apply_mvp_to_formal_migration, preview_mvp_voucher_migration
from app.services.voucher_center_service import create_voucher, post_voucher, reset_voucher_store, review_voucher


def setup_function():
    reset_voucher_store()
    reset_accounting_store()
    reset_accounting_period_store()


def test_migration_preview_classifies_ready_migrated_and_blocked_vouchers():
    draft = create_voucher(_voucher_request("草稿凭证", "100.00", "100.00"))
    ready = review_voucher(create_voucher(_voucher_request("已审核凭证", "100.00", "100.00")).id, "财务主管")
    migrated = post_voucher(
        review_voucher(create_voucher(_voucher_request("已迁移凭证", "80.00", "80.00")).id, "财务主管").id,
        "财务主管",
    )

    preview = preview_mvp_voucher_migration(account_set_id="default", period="2026-06")

    assert preview.account_set_id == "default"
    assert preview.period == "2026-06"
    assert preview.migration_type == "mvp_voucher_to_formal_journal"
    assert preview.total_count == 3
    assert preview.ready_count == 1
    assert preview.migrated_count == 1
    assert preview.blocked_count == 1
    items_by_id = {item.voucher_id: item for item in preview.items}
    assert items_by_id[ready.id].status == "ready"
    assert items_by_id[ready.id].debit_total == Decimal("100.00")
    assert items_by_id[ready.id].credit_total == Decimal("100.00")
    assert items_by_id[migrated.id].status == "already_migrated"
    assert items_by_id[migrated.id].formal_journal_entry_id == migrated.journal_entry_id
    assert items_by_id[draft.id].status == "blocked"
    assert items_by_id[draft.id].reason_code == "voucher_not_reviewed"
    assert preview.blockers == [draft.id]


def test_migration_preview_blocks_reviewed_unbalanced_voucher():
    voucher = review_voucher(create_voucher(_voucher_request("借贷不平凭证", "120.00", "100.00")).id, "财务主管")

    preview = preview_mvp_voucher_migration(account_set_id="default", period="2026-06")

    item = preview.items[0]
    assert item.voucher_id == voucher.id
    assert item.status == "blocked"
    assert item.reason_code == "voucher_unbalanced"
    assert item.difference == Decimal("20.00")
    assert preview.blocked_count == 1
    assert preview.ready_count == 0


def test_apply_migration_requires_backup_permission_and_clean_checks():
    review_voucher(create_voucher(_voucher_request("待迁移凭证", "100.00", "100.00")).id, "财务主管")
    integrity_report = run_accounting_integrity_checks("default", "2026-06")

    with pytest.raises(HTTPException) as missing_backup:
        apply_mvp_to_formal_migration(
            account_set_id="default",
            period="2026-06",
            actor_id="migration-user",
            integrity_report=integrity_report,
        )
    assert missing_backup.value.status_code == 409

    with pytest.raises(HTTPException) as missing_permission:
        apply_mvp_to_formal_migration(
            account_set_id="default",
            period="2026-06",
            actor_id="migration-user",
            backup_manifest_id="backup-202606",
            integrity_report=integrity_report,
            actor_has_permission=False,
        )
    assert missing_permission.value.status_code == 403

    result = apply_mvp_to_formal_migration(
        account_set_id="default",
        period="2026-06",
        actor_id="migration-user",
        backup_manifest_id="backup-202606",
        integrity_report=integrity_report,
        actor_has_permission=True,
    )

    assert result.applied_count == 1
    assert result.skipped_count == 0
    assert result.blocked_count == 0
    assert result.journal_entry_ids == [list_journal_entries("default", "2026-06").entries[0].id]


def _voucher_request(summary: str, debit_amount: str, credit_amount: str) -> VoucherCenterCreateRequest:
    return VoucherCenterCreateRequest(
        account_set_id="default",
        voucher_date="2026-06-18",
        summary=summary,
        counterparty="上海服务商",
        invoice_number="INV-001",
        amount=Decimal(debit_amount),
        tax_amount=Decimal("0.00"),
        total_amount_with_tax=Decimal(debit_amount),
        lines=[
            VoucherCenterLine(
                account_code="6602",
                account_name="管理费用",
                direction="借",
                amount=Decimal(debit_amount),
                explanation="费用",
            ),
            VoucherCenterLine(
                account_code="2202",
                account_name="应付账款",
                direction="贷",
                amount=Decimal(credit_amount),
                explanation="应付",
            ),
        ],
    )
