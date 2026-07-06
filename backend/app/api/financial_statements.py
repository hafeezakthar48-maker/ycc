from fastapi import APIRouter, Header, HTTPException

from app.models.financial_statement import FinancialStatementGenerateRequest
from app.models.system_admin import AuditLogCreateRequest
from app.services.financial_statement_service import generate_financial_statements
from app.services.system_admin_service import authorize, record_audit_log


router = APIRouter(prefix="/api/v1/financial-statements", tags=["financial-statements"])


@router.post("/generate")
def generate_financial_statement_bundle(
    request: FinancialStatementGenerateRequest,
    x_actor_id: str = Header(default="system"),
):
    event = "statement.generate"
    target_id = f"financial-statements:{request.account_set_id}:{request.period}"
    _require_statement_permission(
        actor_id=x_actor_id,
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


def _require_statement_permission(
    actor_id: str,
    event: str,
    target_id: str,
    metadata: dict[str, str | int | float | bool | None],
) -> None:
    if actor_id == "system":
        return

    permission_code = "statement.generate"
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
