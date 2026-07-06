from fastapi import APIRouter, Query

from app.models.system_admin import (
    AuditLogCreateRequest,
    AuditLogEntry,
    AuditLogListResponse,
    AuthorizationDecision,
    AuthorizationRequest,
    PermissionListResponse,
    RoleListResponse,
    UserListResponse,
)
from app.services.system_admin_service import (
    authorize,
    list_audit_logs,
    list_permissions,
    list_roles,
    list_users,
    record_audit_log,
)


router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/permissions", response_model=PermissionListResponse)
def get_permissions():
    return PermissionListResponse(permissions=list_permissions())


@router.get("/roles", response_model=RoleListResponse)
def get_roles():
    return RoleListResponse(roles=list_roles())


@router.get("/users", response_model=UserListResponse)
def get_users():
    return UserListResponse(users=list_users())


@router.post("/authorize", response_model=AuthorizationDecision)
def check_authorization(request: AuthorizationRequest):
    return authorize(request.user_id, request.permission_code)


@router.get("/audit-logs", response_model=AuditLogListResponse)
def get_audit_logs(
    module_id: str | None = None,
    actor_id: str | None = None,
    event: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    return AuditLogListResponse(
        logs=list_audit_logs(
            module_id=module_id,
            actor_id=actor_id,
            event=event,
            limit=limit,
        )
    )


@router.post("/audit-logs", response_model=AuditLogEntry)
def create_audit_log(request: AuditLogCreateRequest):
    return record_audit_log(request)
