from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException

from app.models.accounting_governance import (
    AccountingIntegrityReport,
    AccountingMigrationApplyResult,
    AccountingMigrationItem,
    AccountingMigrationPreview,
)
from app.models.voucher_center import VoucherCenterRecord
from app.services.accounting_period_service import validate_account_set
from app.services.voucher_center_service import list_vouchers, post_voucher


ZERO = Decimal("0.00")


def preview_mvp_voucher_migration(
    account_set_id: str = "default",
    period: str = "2026-06",
    actor_id: str = "system",
) -> AccountingMigrationPreview:
    validate_account_set(account_set_id)
    vouchers = [
        voucher
        for voucher in list_vouchers(account_set_id=account_set_id).vouchers
        if voucher.voucher_date[:7] == period
    ]
    items = [_build_migration_item(voucher) for voucher in vouchers]
    return AccountingMigrationPreview(
        account_set_id=account_set_id,
        period=period,
        actor_id=actor_id,
        generated_at=_now_iso(),
        total_count=len(items),
        ready_count=sum(1 for item in items if item.status == "ready"),
        migrated_count=sum(1 for item in items if item.status == "already_migrated"),
        blocked_count=sum(1 for item in items if item.status == "blocked"),
        proposed_entry_count=sum(1 for item in items if item.status == "ready"),
        blockers=[item.voucher_id for item in items if item.status == "blocked"],
        warnings=[item.reason for item in items if item.status == "blocked"],
        items=items,
    )


def preview_mvp_to_formal_migration(account_set_id: str, period: str, actor_id: str) -> AccountingMigrationPreview:
    return preview_mvp_voucher_migration(account_set_id=account_set_id, period=period, actor_id=actor_id)


def apply_mvp_to_formal_migration(
    account_set_id: str,
    period: str,
    actor_id: str,
    backup_manifest_id: str | None = None,
    integrity_report: AccountingIntegrityReport | None = None,
    actor_has_permission: bool = True,
) -> AccountingMigrationApplyResult:
    if not actor_has_permission:
        raise HTTPException(status_code=403, detail="缺少迁移执行权限。")
    if not backup_manifest_id:
        raise HTTPException(status_code=409, detail="迁移执行前必须先生成备份快照。")
    if integrity_report is None:
        raise HTTPException(status_code=409, detail="迁移执行前必须先完成完整性校验。")
    if any(check.status == "fail" for check in integrity_report.checks):
        raise HTTPException(status_code=409, detail="完整性校验存在失败项，不能执行迁移。")

    preview = preview_mvp_voucher_migration(account_set_id=account_set_id, period=period, actor_id=actor_id)
    if preview.blocked_count:
        raise HTTPException(status_code=409, detail="迁移预览存在阻塞凭证，不能执行迁移。")

    journal_entry_ids: list[str] = []
    for item in preview.items:
        if item.status != "ready":
            continue
        posted = post_voucher(item.voucher_id, operator=actor_id)
        if posted.journal_entry_id:
            journal_entry_ids.append(posted.journal_entry_id)

    return AccountingMigrationApplyResult(
        batch_id=f"migration-{account_set_id}-{period}-{_timestamp_id()}",
        account_set_id=account_set_id,
        period=period,
        actor_id=actor_id,
        backup_manifest_id=backup_manifest_id,
        applied_at=_now_iso(),
        applied_count=len(journal_entry_ids),
        skipped_count=preview.migrated_count,
        blocked_count=preview.blocked_count,
        journal_entry_ids=journal_entry_ids,
        preview=preview,
    )


def _build_migration_item(voucher: VoucherCenterRecord) -> AccountingMigrationItem:
    debit_total, credit_total = _voucher_debit_credit_totals(voucher)
    difference = abs(debit_total - credit_total)
    if voucher.posting_status == "posted":
        status = "already_migrated"
        reason_code = None
        reason = "凭证已生成正式分录。"
    elif voucher.status != "reviewed":
        status = "blocked"
        reason_code = "voucher_not_reviewed"
        reason = "凭证尚未审核，不能迁移到正式分录。"
    elif difference != ZERO:
        status = "blocked"
        reason_code = "voucher_unbalanced"
        reason = "凭证借贷金额不平，需先修正来源凭证。"
    else:
        status = "ready"
        reason_code = None
        reason = "凭证已审核且借贷平衡，可迁移到正式分录。"

    return AccountingMigrationItem(
        voucher_id=voucher.id,
        voucher_number=voucher.voucher_number,
        voucher_date=voucher.voucher_date,
        summary=voucher.summary,
        status=status,
        reason_code=reason_code,
        reason=reason,
        debit_total=debit_total,
        credit_total=credit_total,
        difference=difference,
        formal_journal_entry_id=voucher.journal_entry_id,
    )


def _voucher_debit_credit_totals(voucher: VoucherCenterRecord) -> tuple[Decimal, Decimal]:
    debit_total = ZERO
    credit_total = ZERO
    for line in voucher.lines:
        if line.direction == "借":
            debit_total += line.amount
        else:
            credit_total += line.amount
    return debit_total, credit_total


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
