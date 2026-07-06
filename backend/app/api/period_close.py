from fastapi import APIRouter, Header, HTTPException, Query

from app.models.period_close import (
    PeriodCloseCheckRequest,
    PeriodCloseGenerateRequest,
    PeriodClosePeriodRequest,
    PeriodCloseRunCreate,
)
from app.models.system_admin import AuditLogCreateRequest
from app.services.accounting_period_service import close_accounting_period, reopen_accounting_period
from app.services.period_close_service import (
    generate_period_close_actions,
    list_period_close_runs,
    run_period_close_checks,
    start_period_close_run,
)
from app.services.system_admin_service import authorize, record_audit_log


router = APIRouter(prefix="/api/v1/period-close", tags=["period-close"])


@router.post("/runs")
def create_period_close_run(request: PeriodCloseRunCreate, x_actor_id: str = Header(default="system")):
    target_id = f"period-close-run:{request.account_set_id}:{request.period}"
    metadata = {"account_set_id": request.account_set_id, "period": request.period, "close_type": request.close_type}
    _require_period_close_permission(x_actor_id, "period_close.generate", "period_close.run_started", target_id, metadata)
    run = start_period_close_run(request)
    _record_period_close_audit(
        x_actor_id,
        "period_close.run_started",
        run.run_id,
        {**metadata, "requested_by": run.requested_by},
    )
    return run


@router.get("/runs")
def get_period_close_runs(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    period: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    x_actor_id: str = Header(default="system"),
):
    target_id = f"period-close-runs:{account_set_id}:{period or 'all'}"
    metadata = {"account_set_id": account_set_id, "period": period}
    _require_period_close_permission(x_actor_id, "period_close.view", "period_close.runs_viewed", target_id, metadata)
    response = list_period_close_runs(account_set_id, period)
    _record_period_close_audit(
        x_actor_id,
        "period_close.runs_viewed",
        target_id,
        {"account_set_id": account_set_id, "period": period, "run_count": response.total},
    )
    return response


@router.post("/checks")
def run_checks(request: PeriodCloseCheckRequest, x_actor_id: str = Header(default="system")):
    target_id = f"period-close-checks:{request.account_set_id}:{request.period}"
    metadata = {"account_set_id": request.account_set_id, "period": request.period}
    _require_period_close_permission(x_actor_id, "period_close.check", "period_close.checks_completed", target_id, metadata)
    items = run_period_close_checks(request.account_set_id, request.period)
    _record_period_close_audit(
        x_actor_id,
        "period_close.checks_completed",
        target_id,
        {**metadata, "failed_count": sum(1 for item in items if item.status == "failed")},
    )
    return {"items": items}


@router.post("/actions/preview")
def preview_actions(request: PeriodCloseGenerateRequest, x_actor_id: str = Header(default="system")):
    target_id = f"period-close-preview:{request.account_set_id}:{request.period}"
    metadata = {
        "account_set_id": request.account_set_id,
        "period": request.period,
        "actions": ",".join(request.actions),
    }
    _require_period_close_permission(x_actor_id, "period_close.check", "period_close.actions_previewed", target_id, metadata)
    checks = run_period_close_checks(request.account_set_id, request.period)
    _record_period_close_audit(
        x_actor_id,
        "period_close.actions_previewed",
        target_id,
        {**metadata, "failed_count": sum(1 for item in checks if item.status == "failed")},
    )
    return {"checks": checks, "actions": request.actions}


@router.post("/actions/generate")
def generate_actions(request: PeriodCloseGenerateRequest, x_actor_id: str = Header(default="system")):
    target_id = f"period-close-actions:{request.account_set_id}:{request.period}"
    metadata = {
        "account_set_id": request.account_set_id,
        "period": request.period,
        "actions": ",".join(request.actions),
    }
    _require_period_close_permission(x_actor_id, "period_close.generate", "period_close.actions_generated", target_id, metadata)
    results = generate_period_close_actions(
        account_set_id=request.account_set_id,
        period=request.period,
        actions=list(request.actions),
        generated_by=request.generated_by,
        force_regenerate=request.force_regenerate,
    )
    _record_period_close_audit(
        x_actor_id,
        "period_close.actions_generated",
        target_id,
        {**metadata, "generated_by": request.generated_by, "result_count": len(results)},
    )
    return {"results": results}


@router.post("/close")
def close_period(request: PeriodClosePeriodRequest, x_actor_id: str = Header(default="system")):
    target_id = f"period-close:{request.account_set_id}:{request.period}"
    metadata = {"account_set_id": request.account_set_id, "period": request.period, "operator": request.operator}
    _require_period_close_permission(x_actor_id, "period_close.close", "period_close.period_closed", target_id, metadata)
    result = close_accounting_period(request.period, request.operator, request.account_set_id)
    _record_period_close_audit(x_actor_id, "period_close.period_closed", target_id, metadata)
    return result


@router.post("/reopen")
def reopen_period(request: PeriodClosePeriodRequest, x_actor_id: str = Header(default="system")):
    target_id = f"period-reopen:{request.account_set_id}:{request.period}"
    metadata = {"account_set_id": request.account_set_id, "period": request.period, "operator": request.operator}
    _require_period_close_permission(x_actor_id, "period_close.reopen", "period_close.period_reopened", target_id, metadata)
    result = reopen_accounting_period(request.period, request.operator, request.account_set_id)
    _record_period_close_audit(x_actor_id, "period_close.period_reopened", target_id, metadata)
    return result


def _record_period_close_audit(
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


def _require_period_close_permission(
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
    _record_period_close_audit(
        actor_id,
        event,
        target_id,
        {**metadata, "permission_code": permission_code, "reason": decision.reason},
        result="denied",
    )
    raise HTTPException(status_code=403, detail=decision.reason)
