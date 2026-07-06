from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from app.models.financial_statement import FinancialStatementBundle
from app.models.statement_archive import (
    StatementExportRecord,
    StatementSnapshot,
    StatementSnapshotListResponse,
)


_STATEMENT_SNAPSHOTS: dict[str, StatementSnapshot] = {}
_STATEMENT_EXPORTS: dict[str, StatementExportRecord] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def reset_statement_archive_store() -> None:
    _STATEMENT_SNAPSHOTS.clear()
    _STATEMENT_EXPORTS.clear()


def create_statement_snapshot(bundle: FinancialStatementBundle, created_by: str) -> StatementSnapshot:
    version = _next_version(bundle.account_set_id, bundle.period)
    snapshot = StatementSnapshot(
        snapshot_id=f"stmt_snap_{uuid4().hex}",
        account_set_id=bundle.account_set_id,
        period=bundle.period,
        company_name=bundle.company_name,
        version=version,
        mapping_set_id=bundle.mapping_set_id,
        source=bundle.source,
        content_hash=statement_bundle_hash(bundle),
        validation_status=_validation_status(bundle),
        archive_status="demo_only" if bundle.source == "sample_finance_data" else "draft",
        created_by=created_by,
        created_at=_now_iso(),
        bundle=bundle,
    )
    _STATEMENT_SNAPSHOTS[snapshot.snapshot_id] = snapshot
    return snapshot


def get_statement_snapshot(snapshot_id: str) -> StatementSnapshot:
    snapshot = _STATEMENT_SNAPSHOTS.get(snapshot_id)
    if snapshot is None:
        raise ValueError(f"未找到报表快照 {snapshot_id}")
    return snapshot


def list_statement_snapshots(account_set_id: str, period: str | None = None) -> StatementSnapshotListResponse:
    items = [
        snapshot
        for snapshot in _STATEMENT_SNAPSHOTS.values()
        if snapshot.account_set_id == account_set_id and (period is None or snapshot.period == period)
    ]
    items.sort(key=lambda item: (item.period, item.version), reverse=True)
    return StatementSnapshotListResponse(total=len(items), items=items)


def statement_bundle_hash(bundle: FinancialStatementBundle) -> str:
    payload = bundle.model_dump(mode="json")
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _next_version(account_set_id: str, period: str) -> int:
    versions = [
        snapshot.version
        for snapshot in _STATEMENT_SNAPSHOTS.values()
        if snapshot.account_set_id == account_set_id and snapshot.period == period
    ]
    return max(versions, default=0) + 1


def _validation_status(bundle: FinancialStatementBundle) -> str:
    if any(item.status == "failed" for item in bundle.validation_items):
        return "failed"
    if any(item.status == "warning" for item in bundle.validation_items):
        return "warning"
    return "passed"
