from fastapi import APIRouter, Header, HTTPException, Response

from app.models.financial_statement import FinancialStatementGenerateRequest
from app.models.statement_archive import StatementSnapshotCreateRequest, StatementSnapshotLockRequest
from app.models.system_admin import AuditLogCreateRequest
from app.services.financial_statement_service import generate_financial_statements
from app.services.statement_archive_service import (
    create_statement_snapshot,
    get_statement_snapshot,
    list_statement_snapshots,
    lock_statement_snapshot,
    record_statement_export,
)
from app.services.statement_export_service import build_statement_export
from app.services.statement_mapping_service import get_default_statement_mapping_set, list_statement_mapping_rules
from app.services.system_admin_service import authorize, record_audit_log


router = APIRouter(prefix="/api/v1/financial-statements", tags=["financial-statements"])


@router.post("/generate")
def generate_financial_statement_bundle(
    request: FinancialStatementGenerateRequest,
    x_actor_id: str = Header(default="system"),
):
    event = "statement.generate"
    target_id = f"financial-statements:{request.account_set_id}:{request.period}"
    _require_permission(
        actor_id=x_actor_id,
        permission_code="statement.generate",
        event=event,
        target_id=target_id,
        metadata={
            "account_set_id": request.account_set_id,
            "period": request.period,
            "operator": request.operator,
        },
    )
    try:
        result = generate_financial_statements(request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    _record_statement_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={
            "account_set_id": result.account_set_id,
            "period": result.period,
            "operator": request.operator,
            "source": result.source,
            "statement_count": result.summary.generated_statement_count,
            "reviewed_voucher_count": result.summary.reviewed_voucher_count,
            "asset_liability_balanced": result.summary.asset_liability_balanced,
        },
    )
    return result


@router.get("/mapping-sets/default")
def get_default_mapping_set(account_set_id: str = "default", x_actor_id: str = Header(default="system")):
    event = "statement.mapping.view"
    target_id = f"statement-mapping:{account_set_id}:default"
    metadata = {"account_set_id": account_set_id}
    _require_permission(
        actor_id=x_actor_id,
        permission_code="statement.mapping.view",
        event=event,
        target_id=target_id,
        metadata=metadata,
    )
    mapping_set = get_default_statement_mapping_set(account_set_id)
    rules = list_statement_mapping_rules(mapping_set.mapping_set_id)
    _record_statement_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={**metadata, "rule_count": len(rules)},
    )
    return {"mapping_set": mapping_set, "rules": rules}


@router.post("/snapshots")
def create_snapshot(request: StatementSnapshotCreateRequest, x_actor_id: str = Header(default="system")):
    event = "statement.snapshot.create"
    _require_permission(
        actor_id=x_actor_id,
        permission_code="statement.snapshot.create",
        event=event,
        target_id=f"statement-snapshot:{request.account_set_id}:{request.period}",
        metadata={"account_set_id": request.account_set_id, "period": request.period},
    )
    bundle = generate_financial_statements(
        FinancialStatementGenerateRequest(
            period=request.period,
            account_set_id=request.account_set_id,
            operator=request.operator,
        )
    )
    snapshot = create_statement_snapshot(bundle=bundle, created_by=request.created_by)
    _record_statement_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=snapshot.snapshot_id,
        metadata={"period": snapshot.period, "version": snapshot.version, "content_hash": snapshot.content_hash},
    )
    return snapshot


@router.get("/snapshots")
def list_snapshots(
    account_set_id: str = "default",
    period: str | None = None,
    x_actor_id: str = Header(default="system"),
):
    event = "statement.archive.view"
    _require_permission(
        actor_id=x_actor_id,
        permission_code="statement.archive.view",
        event=event,
        target_id=f"statement-archive:{account_set_id}:{period or 'all'}",
        metadata={"account_set_id": account_set_id, "period": period or ""},
    )
    response = list_statement_snapshots(account_set_id=account_set_id, period=period)
    _record_statement_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=f"statement-archive:{account_set_id}:{period or 'all'}",
        metadata={"account_set_id": account_set_id, "period": period or "", "snapshot_count": response.total},
    )
    return response


@router.post("/snapshots/{snapshot_id}/lock")
def lock_snapshot(snapshot_id: str, request: StatementSnapshotLockRequest, x_actor_id: str = Header(default="system")):
    event = "statement.snapshot.lock"
    _require_permission(
        actor_id=x_actor_id,
        permission_code="statement.snapshot.lock",
        event=event,
        target_id=snapshot_id,
        metadata={"snapshot_id": snapshot_id, "locked_by": request.locked_by},
    )
    try:
        snapshot = lock_statement_snapshot(snapshot_id, locked_by=request.locked_by)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    _record_statement_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=snapshot.snapshot_id,
        metadata={"period": snapshot.period, "version": snapshot.version},
    )
    return snapshot


@router.get("/snapshots/{snapshot_id}/export/{export_format}")
def export_snapshot(snapshot_id: str, export_format: str, x_actor_id: str = Header(default="system")):
    event = "statement.export"
    _require_permission(
        actor_id=x_actor_id,
        permission_code="statement.export",
        event=event,
        target_id=snapshot_id,
        metadata={"snapshot_id": snapshot_id, "format": export_format},
    )
    try:
        snapshot = get_statement_snapshot(snapshot_id)
        payload = build_statement_export(snapshot, export_format)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    record_statement_export(
        snapshot_id=snapshot_id,
        export_format=export_format,
        filename=payload.filename,
        content_type=payload.content_type,
        exported_by=x_actor_id,
    )
    _record_statement_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=snapshot_id,
        metadata={"format": export_format, "filename": payload.filename},
    )
    return Response(
        content=payload.content,
        media_type=payload.content_type,
        headers={"Content-Disposition": f'attachment; filename="{payload.filename}"'},
    )


def _record_statement_audit(
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


def _require_permission(
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

    _record_statement_audit(
        actor_id=actor_id,
        event=event,
        target_id=target_id,
        result="denied",
        metadata={
            **metadata,
            "permission_code": permission_code,
            "reason": decision.reason,
        },
    )
    raise HTTPException(status_code=403, detail=decision.reason)
