from fastapi import APIRouter, Header, HTTPException

from app.models.financial_statement import FinancialStatementGenerateRequest
from app.models.system_admin import AuditLogCreateRequest
from app.services.financial_statement_service import generate_financial_statements
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
