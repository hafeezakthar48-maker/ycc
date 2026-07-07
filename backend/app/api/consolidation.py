from fastapi import APIRouter, Header, Query

from app.models.consolidation import (
    ConsolidationEliminationRebuildRequest,
    ConsolidationGroupCreate,
)
from app.models.system_admin import AuditLogCreateRequest
from app.services.consolidation_service import (
    build_consolidated_statements,
    build_reporting_package,
    create_consolidation_group,
    list_consolidation_eliminations,
    list_consolidation_groups,
    rebuild_consolidation_eliminations,
)
from app.services.system_admin_service import authorize, record_audit_log


router = APIRouter(prefix="/api/v1/consolidation", tags=["consolidation"])


@router.get("/groups")
def get_consolidation_groups(x_actor_id: str = Header(default="system")):
    event = "consolidation.group.read"
    _require_permission(x_actor_id, "consolidation.read", event, "consolidation-groups", {})
    result = list_consolidation_groups()
    _record_audit(x_actor_id, event, "consolidation-groups", {"group_count": result.total_groups})
    return result


@router.post("/groups")
def post_consolidation_group(
    request: ConsolidationGroupCreate,
    x_actor_id: str = Header(default="system"),
):
    event = "consolidation.group.write"
    target_id = f"consolidation-group:{request.group_id}"
    metadata = {"group_id": request.group_id, "entity_count": len(request.entities)}
    _require_permission(x_actor_id, "consolidation.write", event, target_id, metadata)
    group = create_consolidation_group(request)
    _record_audit(x_actor_id, event, target_id, metadata)
    return group


@router.get("/reporting-package")
def get_consolidation_reporting_package(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    period: str = Query(pattern=r"^\d{4}-\d{2}$"),
    x_actor_id: str = Header(default="system"),
):
    event = "consolidation.package.read"
    target_id = f"consolidation-package:{account_set_id}:{period}"
    metadata = {"account_set_id": account_set_id, "period": period}
    _require_permission(x_actor_id, "consolidation.read", event, target_id, metadata)
    package = build_reporting_package(account_set_id, period)
    _record_audit(x_actor_id, event, target_id, metadata)
    return package


@router.get("/eliminations")
def get_consolidation_eliminations(
    group_id: str = Query(min_length=1, max_length=80),
    period: str = Query(pattern=r"^\d{4}-\d{2}$"),
    x_actor_id: str = Header(default="system"),
):
    event = "consolidation.elimination.read"
    target_id = f"consolidation-eliminations:{group_id}:{period}"
    metadata = {"group_id": group_id, "period": period}
    _require_permission(x_actor_id, "consolidation.read", event, target_id, metadata)
    result = list_consolidation_eliminations(group_id, period)
    _record_audit(x_actor_id, event, target_id, {**metadata, "elimination_count": result.total_eliminations})
    return result


@router.post("/eliminations/rebuild")
def post_consolidation_eliminations_rebuild(
    request: ConsolidationEliminationRebuildRequest,
    x_actor_id: str = Header(default="system"),
):
    event = "consolidation.elimination.rebuild"
    target_id = f"consolidation-eliminations:{request.group_id}:{request.period}"
    metadata = {"group_id": request.group_id, "period": request.period}
    _require_permission(x_actor_id, "consolidation.rebuild", event, target_id, metadata)
    result = rebuild_consolidation_eliminations(request)
    _record_audit(x_actor_id, event, target_id, {**metadata, "elimination_count": result.total_eliminations})
    return result


@router.get("/statements")
def get_consolidation_statements(
    group_id: str = Query(min_length=1, max_length=80),
    period: str = Query(pattern=r"^\d{4}-\d{2}$"),
    x_actor_id: str = Header(default="system"),
):
    event = "consolidation.statement.read"
    target_id = f"consolidation-statements:{group_id}:{period}"
    metadata = {"group_id": group_id, "period": period}
    _require_permission(x_actor_id, "consolidation.read", event, target_id, metadata)
    result = build_consolidated_statements(group_id, period)
    _record_audit(x_actor_id, event, target_id, {**metadata, "elimination_count": result.elimination_count})
    return result


def _record_audit(
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
    _record_audit(
        actor_id,
        event,
        target_id,
        {**metadata, "permission_code": permission_code, "reason": decision.reason},
        result="denied",
    )
    from fastapi import HTTPException

    raise HTTPException(status_code=403, detail=decision.reason)
