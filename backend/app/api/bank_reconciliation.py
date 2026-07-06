from fastapi import APIRouter, Header, HTTPException, Query

from app.models.bank_reconciliation import BankReconciliationConfirmRequest, BankStatementImportRequest
from app.models.system_admin import AuditLogCreateRequest
from app.services.bank_reconciliation_service import (
    build_bank_reconciliation_statement,
    confirm_bank_reconciliation,
    import_bank_statement_lines,
    suggest_bank_matches,
)
from app.services.system_admin_service import authorize, record_audit_log


router = APIRouter(prefix="/api/v1/bank-reconciliation", tags=["bank-reconciliation"])


@router.post("/statements/import")
def import_statements(request: BankStatementImportRequest, x_actor_id: str = Header(default="system")):
    target_id = request.account_set_id
    metadata = {"account_set_id": request.account_set_id, "line_count": len(request.lines)}
    _require_bank_permission(
        x_actor_id,
        "bank_reconciliation.import",
        "bank_reconciliation.statement.import",
        target_id,
        metadata,
    )
    try:
        response = import_bank_statement_lines(request.account_set_id, request.lines)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    _record_bank_audit(
        x_actor_id,
        "bank_reconciliation.statement.import",
        target_id,
        {**metadata, "imported_count": response.imported_count, "duplicate_count": response.duplicate_count},
    )
    return response


@router.get("/matches")
def get_match_candidates(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    bank_account_id: str = Query(min_length=1, max_length=80),
    period: str = Query(pattern=r"^\d{4}-\d{2}$"),
    minimum_score: int = Query(default=80, ge=0, le=100),
    x_actor_id: str = Header(default="system"),
):
    target_id = f"{account_set_id}:{bank_account_id}:{period}"
    metadata = {
        "account_set_id": account_set_id,
        "bank_account_id": bank_account_id,
        "period": period,
        "minimum_score": minimum_score,
    }
    _require_bank_permission(
        x_actor_id,
        "bank_reconciliation.match",
        "bank_reconciliation.match.suggest",
        target_id,
        metadata,
    )
    response = suggest_bank_matches(account_set_id, bank_account_id, period, minimum_score)
    _record_bank_audit(
        x_actor_id,
        "bank_reconciliation.match.suggest",
        target_id,
        {**metadata, "candidate_count": len(response.candidates)},
    )
    return response


@router.post("/confirm")
def confirm_match(request: BankReconciliationConfirmRequest, x_actor_id: str = Header(default="system")):
    target_id = f"{request.account_set_id}:{request.bank_account_id}:{request.period}"
    metadata = {
        "account_set_id": request.account_set_id,
        "bank_account_id": request.bank_account_id,
        "period": request.period,
        "statement_line_count": len(request.statement_line_ids),
        "journal_line_count": len(request.journal_line_ids),
    }
    _require_bank_permission(
        x_actor_id,
        "bank_reconciliation.confirm",
        "bank_reconciliation.match.confirm",
        target_id,
        metadata,
    )
    match = confirm_bank_reconciliation(request)
    _record_bank_audit(
        x_actor_id,
        "bank_reconciliation.match.confirm",
        match.reconciliation_id,
        {**metadata, "settlement_count": len(match.settlement_ids)},
    )
    return match


@router.get("/statements")
def get_reconciliation_statement(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    bank_account_id: str = Query(min_length=1, max_length=80),
    period: str = Query(pattern=r"^\d{4}-\d{2}$"),
    x_actor_id: str = Header(default="system"),
):
    target_id = f"{account_set_id}:{bank_account_id}:{period}"
    metadata = {"account_set_id": account_set_id, "bank_account_id": bank_account_id, "period": period}
    _require_bank_permission(
        x_actor_id,
        "bank_reconciliation.read",
        "bank_reconciliation.statement.read",
        target_id,
        metadata,
    )
    statement = build_bank_reconciliation_statement(account_set_id, bank_account_id, period)
    _record_bank_audit(
        x_actor_id,
        "bank_reconciliation.statement.read",
        target_id,
        {
            **metadata,
            "unmatched_statement_count": statement.unmatched_statement_count,
            "unmatched_journal_count": statement.unmatched_journal_count,
        },
    )
    return statement


def _record_bank_audit(
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


def _require_bank_permission(
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
    _record_bank_audit(
        actor_id,
        event,
        target_id,
        {**metadata, "permission_code": permission_code, "reason": decision.reason},
        result="denied",
    )
    raise HTTPException(status_code=403, detail=decision.reason)
