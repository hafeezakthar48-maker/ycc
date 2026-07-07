from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.models.system_admin import AuditLogCreateRequest
from app.services.accounting_governance_service import (
    build_formal_accounting_permission_matrix,
    evaluate_formal_accounting_go_live_gate,
)
from app.services.backup_service import create_accounting_backup_manifest, rehearse_accounting_restore
from app.services.integrity_check_service import run_accounting_integrity_checks
from app.services.migration_service import apply_mvp_to_formal_migration, preview_mvp_voucher_migration
from app.services.system_admin_service import authorize, record_audit_log


router = APIRouter(prefix="/api/v1/accounting-governance", tags=["accounting-governance"])


class GovernanceScopeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    period: str = Field(default="2026-06", pattern=r"^\d{4}-\d{2}$")
    actor_id: str = Field(default="system", min_length=1, max_length=80)


class MigrationApplyRequest(GovernanceScopeRequest):
    backup_manifest_id: str = Field(min_length=1, max_length=120)


class RestoreRehearsalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backup_manifest_id: str = Field(min_length=1, max_length=120)
    target_database_path: str = Field(min_length=1, max_length=260)
    actor_id: str = Field(default="system", min_length=1, max_length=80)


@router.get("/integrity-checks")
def get_integrity_checks(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    period: str = Query(default="2026-06", pattern=r"^\d{4}-\d{2}$"),
    x_actor_id: str = Header(default="system"),
):
    target_id = f"integrity:{account_set_id}:{period}"
    metadata = {"account_set_id": account_set_id, "period": period}
    _require_governance_permission(
        x_actor_id,
        "accounting_governance.read",
        "accounting_governance.integrity.read",
        target_id,
        metadata,
    )
    report = run_accounting_integrity_checks(account_set_id=account_set_id, period=period)
    _record_governance_audit(
        x_actor_id,
        "accounting_governance.integrity.read",
        target_id,
        {**metadata, "overall_status": report.overall_status},
    )
    return report


@router.post("/migration-preview")
def create_migration_preview(request: GovernanceScopeRequest, x_actor_id: str = Header(default="system")):
    actor_id = _operation_actor(request.actor_id, x_actor_id)
    target_id = f"migration-preview:{request.account_set_id}:{request.period}"
    metadata = {"account_set_id": request.account_set_id, "period": request.period, "actor_id": actor_id}
    _require_governance_permission(
        x_actor_id,
        "accounting_migration.preview",
        "accounting_governance.migration.preview",
        target_id,
        metadata,
    )
    preview = preview_mvp_voucher_migration(
        account_set_id=request.account_set_id,
        period=request.period,
        actor_id=actor_id,
    )
    _record_governance_audit(
        x_actor_id,
        "accounting_governance.migration.preview",
        target_id,
        {**metadata, "ready_count": preview.ready_count, "blocked_count": preview.blocked_count},
    )
    return preview


@router.post("/migration-apply")
def apply_migration(request: MigrationApplyRequest, x_actor_id: str = Header(default="system")):
    actor_id = _operation_actor(request.actor_id, x_actor_id)
    target_id = f"migration-apply:{request.account_set_id}:{request.period}"
    metadata = {
        "account_set_id": request.account_set_id,
        "period": request.period,
        "actor_id": actor_id,
        "backup_manifest_id": request.backup_manifest_id,
    }
    _require_governance_permission(
        x_actor_id,
        "accounting_migration.apply",
        "accounting_governance.migration.apply",
        target_id,
        metadata,
    )
    integrity_report = run_accounting_integrity_checks(request.account_set_id, request.period)
    result = apply_mvp_to_formal_migration(
        account_set_id=request.account_set_id,
        period=request.period,
        actor_id=actor_id,
        backup_manifest_id=request.backup_manifest_id,
        integrity_report=integrity_report,
        actor_has_permission=True,
    )
    _record_governance_audit(
        x_actor_id,
        "accounting_governance.migration.apply",
        result.batch_id,
        {**metadata, "applied_count": result.applied_count, "blocked_count": result.blocked_count},
    )
    return result


@router.post("/backups")
def create_backup(request: GovernanceScopeRequest, x_actor_id: str = Header(default="system")):
    actor_id = _operation_actor(request.actor_id, x_actor_id)
    target_id = f"backup:{request.account_set_id}:{request.period}"
    metadata = {"account_set_id": request.account_set_id, "period": request.period, "actor_id": actor_id}
    _require_governance_permission(
        x_actor_id,
        "accounting_backup.create",
        "accounting_governance.backup.create",
        target_id,
        metadata,
    )
    manifest = create_accounting_backup_manifest(
        account_set_id=request.account_set_id,
        period=request.period,
        actor_id=actor_id,
    )
    _record_governance_audit(
        x_actor_id,
        "accounting_governance.backup.create",
        manifest.backup_manifest_id,
        {**metadata, "dataset_count": len(manifest.datasets)},
    )
    return manifest


@router.post("/restore-rehearsals")
def create_restore_rehearsal(request: RestoreRehearsalRequest, x_actor_id: str = Header(default="system")):
    actor_id = _operation_actor(request.actor_id, x_actor_id)
    target_id = f"restore:{request.backup_manifest_id}"
    metadata = {
        "backup_manifest_id": request.backup_manifest_id,
        "target_database_path": request.target_database_path,
        "actor_id": actor_id,
    }
    _require_governance_permission(
        x_actor_id,
        "accounting_backup.create",
        "accounting_governance.restore.rehearsal",
        target_id,
        metadata,
    )
    rehearsal = rehearse_accounting_restore(
        backup_manifest_id=request.backup_manifest_id,
        target_database_path=request.target_database_path,
        actor_id=actor_id,
    )
    _record_governance_audit(
        x_actor_id,
        "accounting_governance.restore.rehearsal",
        rehearsal.restore_rehearsal_id,
        {**metadata, "status": rehearsal.status, "integrity_status": rehearsal.integrity_status},
    )
    return rehearsal


@router.get("/permission-matrix")
def get_permission_matrix(x_actor_id: str = Header(default="system")):
    _require_governance_permission(
        x_actor_id,
        "accounting_governance.read",
        "accounting_governance.permission_matrix.read",
        "permission-matrix",
        {},
    )
    matrix = build_formal_accounting_permission_matrix()
    _record_governance_audit(
        x_actor_id,
        "accounting_governance.permission_matrix.read",
        "permission-matrix",
        {"missing_count": len(matrix.missing_permissions)},
    )
    return matrix


@router.get("/go-live-gate")
def get_go_live_gate(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    period: str = Query(default="2026-06", pattern=r"^\d{4}-\d{2}$"),
    backend_tests: str | None = Query(default=None),
    frontend_tests: str | None = Query(default=None),
    frontend_build: str | None = Query(default=None),
    x_actor_id: str = Header(default="system"),
):
    target_id = f"go-live-gate:{account_set_id}:{period}"
    metadata = {"account_set_id": account_set_id, "period": period}
    _require_governance_permission(
        x_actor_id,
        "accounting_governance.read",
        "accounting_governance.go_live_gate.read",
        target_id,
        metadata,
    )
    regression_results = {
        key: value
        for key, value in {
            "backend_tests": backend_tests,
            "frontend_tests": frontend_tests,
            "frontend_build": frontend_build,
        }.items()
        if value is not None
    }
    gate = evaluate_formal_accounting_go_live_gate(
        account_set_id=account_set_id,
        period=period,
        regression_results=regression_results,
    )
    _record_governance_audit(
        x_actor_id,
        "accounting_governance.go_live_gate.read",
        target_id,
        {**metadata, "status": gate.status, "blocker_count": len(gate.blockers)},
    )
    return gate


def _operation_actor(request_actor_id: str, header_actor_id: str) -> str:
    if request_actor_id != "system":
        return request_actor_id
    return header_actor_id


def _record_governance_audit(
    actor_id: str,
    event: str,
    target_id: str,
    metadata: dict[str, str | int | float | bool | None],
    result: str = "success",
) -> None:
    record_audit_log(
        AuditLogCreateRequest(
            actor_id=actor_id,
            module_id="finance-center",
            event=event,
            target_id=target_id,
            result=result,
            metadata=metadata,
        )
    )


def _require_governance_permission(
    actor_id: str,
    permission_code: str,
    event: str,
    target_id: str,
    metadata: dict[str, str | int | float | bool | None],
) -> None:
    if actor_id == "system":
        return

    decision = authorize(actor_id, permission_code)
    if decision.allowed:
        return

    _record_governance_audit(
        actor_id,
        event,
        target_id,
        {**metadata, "permission_code": permission_code, "reason": decision.reason},
        result="denied",
    )
    raise HTTPException(status_code=403, detail=decision.reason)
