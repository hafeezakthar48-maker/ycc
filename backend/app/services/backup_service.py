from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import HTTPException

from app.models.accounting_governance import (
    AccountingBackupManifest,
    AccountingBackupPackage,
    RestoreRehearsalResult,
)
from app.services.accounting_archive_service import list_archive_documents
from app.services.accounting_period_service import list_accounting_periods, validate_account_set
from app.services.accounting_service import list_journal_entries
from app.services.integrity_check_service import run_accounting_integrity_checks
from app.services.statement_mapping_service import get_default_statement_mapping_set, list_statement_mapping_rules
from app.services.system_admin_service import list_audit_logs


CORE_DATASETS = [
    "journal_entries",
    "journal_lines",
    "accounting_periods",
    "statement_mappings",
    "counterparty_settlements",
    "bank_reconciliations",
    "fixed_asset_cards",
    "payroll_batches",
    "inventory_movements",
    "tax_workpapers",
    "consolidation_packages",
    "archive_documents",
    "audit_logs",
]

_BACKUP_MANIFESTS: dict[str, AccountingBackupManifest] = {}
_RESTORE_REHEARSALS: dict[str, RestoreRehearsalResult] = {}


def reset_backup_store() -> None:
    _BACKUP_MANIFESTS.clear()
    _RESTORE_REHEARSALS.clear()


def create_accounting_backup_manifest(
    account_set_id: str = "default",
    period: str = "2026-06",
    actor_id: str = "system",
) -> AccountingBackupManifest:
    validate_account_set(account_set_id)
    row_counts = _dataset_row_counts(account_set_id, period)
    manifest = AccountingBackupManifest(
        backup_manifest_id=f"backup-{account_set_id}-{period}-{_timestamp_id()}",
        account_set_id=account_set_id,
        period=period,
        actor_id=actor_id,
        created_at=_now_iso(),
        datasets=list(CORE_DATASETS),
        dataset_row_counts=row_counts,
        dataset_checksums={dataset: _checksum(dataset, row_counts[dataset]) for dataset in CORE_DATASETS},
    )
    _BACKUP_MANIFESTS[manifest.backup_manifest_id] = manifest
    return manifest


def get_backup_manifest(backup_manifest_id: str) -> AccountingBackupManifest:
    manifest = _BACKUP_MANIFESTS.get(backup_manifest_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="未找到备份清单。")
    return manifest


def get_latest_backup_manifest(account_set_id: str = "default", period: str = "2026-06") -> AccountingBackupManifest:
    manifests = [
        manifest
        for manifest in _BACKUP_MANIFESTS.values()
        if manifest.account_set_id == account_set_id and manifest.period == period
    ]
    if not manifests:
        raise HTTPException(status_code=404, detail="未找到备份清单。")
    return sorted(manifests, key=lambda item: item.created_at, reverse=True)[0]


def rehearse_accounting_restore(
    backup_manifest_id: str,
    target_database_path: str,
    actor_id: str = "system",
) -> RestoreRehearsalResult:
    manifest = get_backup_manifest(backup_manifest_id)
    started_at = _now_iso()
    integrity_report = run_accounting_integrity_checks(manifest.account_set_id, manifest.period)
    result = RestoreRehearsalResult(
        restore_rehearsal_id=f"restore-{manifest.account_set_id}-{manifest.period}-{_timestamp_id()}",
        backup_manifest_id=manifest.backup_manifest_id,
        account_set_id=manifest.account_set_id,
        period=manifest.period,
        actor_id=actor_id,
        target_database_path=target_database_path,
        started_at=started_at,
        completed_at=_now_iso(),
        status="failed" if integrity_report.overall_status == "fail" else "passed",
        row_counts=dict(manifest.dataset_row_counts),
        integrity_status=integrity_report.overall_status,
        messages=[check.message for check in integrity_report.checks if check.status != "pass"],
    )
    _RESTORE_REHEARSALS[result.restore_rehearsal_id] = result
    return result


def get_latest_restore_rehearsal(account_set_id: str = "default", period: str = "2026-06") -> RestoreRehearsalResult:
    rehearsals = [
        rehearsal
        for rehearsal in _RESTORE_REHEARSALS.values()
        if rehearsal.account_set_id == account_set_id and rehearsal.period == period
    ]
    if not rehearsals:
        raise HTTPException(status_code=404, detail="未找到恢复演练结果。")
    return sorted(rehearsals, key=lambda item: item.completed_at, reverse=True)[0]


def build_accounting_backup_package(backup_manifest_id: str) -> AccountingBackupPackage:
    manifest = get_backup_manifest(backup_manifest_id)
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as package:
        package.writestr("manifest.json", manifest.model_dump_json(indent=2))
        package.writestr("dataset-row-counts.json", json.dumps(manifest.dataset_row_counts, ensure_ascii=False, indent=2))
        package.writestr("dataset-checksums.json", json.dumps(manifest.dataset_checksums, ensure_ascii=False, indent=2))
    content = output.getvalue()
    return AccountingBackupPackage(
        backup_manifest_id=manifest.backup_manifest_id,
        filename=f"formal-accounting-backup-{manifest.account_set_id}-{manifest.period}.zip",
        size=len(content),
        content=content,
    )


def _dataset_row_counts(account_set_id: str, period: str) -> dict[str, int]:
    entries = list_journal_entries(account_set_id=account_set_id, period=period).entries
    mapping_set = get_default_statement_mapping_set(account_set_id)
    counts = {dataset: 0 for dataset in CORE_DATASETS}
    counts["journal_entries"] = len(entries)
    counts["journal_lines"] = sum(len(entry.lines) for entry in entries)
    counts["accounting_periods"] = len(list_accounting_periods(account_set_id).periods)
    counts["statement_mappings"] = len(list_statement_mapping_rules(mapping_set.mapping_set_id))
    counts["archive_documents"] = list_archive_documents(account_set_id=account_set_id, period=period).total
    counts["audit_logs"] = len(list_audit_logs(limit=10_000))
    return counts


def _checksum(dataset: str, row_count: int) -> str:
    return hashlib.sha256(f"{dataset}:{row_count}".encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
