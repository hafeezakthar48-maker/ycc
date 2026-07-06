from fastapi import APIRouter, Header, HTTPException, Query

from app.models.fixed_asset_accounting import (
    FixedAssetCapitalizationRequest,
    FixedAssetDepreciationPostRequest,
    FixedAssetDisposalPostRequest,
    FixedAssetImpairmentPostRequest,
    FormalAssetAccountingCardListResponse,
)
from app.models.system_admin import AuditLogCreateRequest
from app.services.fixed_asset_accounting_service import (
    capitalize_fixed_asset,
    dispose_fixed_asset_formally,
    list_formal_asset_cards,
    post_fixed_asset_depreciation,
    record_fixed_asset_impairment,
)
from app.services.system_admin_service import authorize, record_audit_log


router = APIRouter(prefix="/api/v1/fixed-asset-accounting", tags=["fixed-asset-accounting"])


@router.get("/cards")
def get_formal_fixed_asset_cards(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    x_actor_id: str = Header(default="system"),
):
    event = "fixed_asset_accounting.card.read"
    target_id = f"fixed-asset-accounting:{account_set_id}"
    _require_permission(
        actor_id=x_actor_id,
        permission_code="fixed_asset_accounting.read",
        event=event,
        target_id=target_id,
        metadata={"account_set_id": account_set_id},
    )
    cards = list_formal_asset_cards(account_set_id)
    _record_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={"account_set_id": account_set_id, "card_count": len(cards)},
    )
    return FormalAssetAccountingCardListResponse(account_set_id=account_set_id, cards=cards)


@router.post("/capitalize")
def capitalize_formal_fixed_asset(
    request: FixedAssetCapitalizationRequest,
    x_actor_id: str = Header(default="system"),
):
    event = "fixed_asset_accounting.capitalize"
    target_id = f"fixed-asset:{request.asset_id}"
    _require_permission(
        actor_id=x_actor_id,
        permission_code="fixed_asset_accounting.post",
        event=event,
        target_id=target_id,
        metadata={"account_set_id": request.account_set_id, "asset_id": request.asset_id, "period": request.period},
    )
    entry = capitalize_fixed_asset(
        request.account_set_id,
        request.asset_id,
        request.period,
        request.credit_account_code,
        x_actor_id,
    )
    _record_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={
            "account_set_id": request.account_set_id,
            "asset_id": request.asset_id,
            "period": request.period,
            "journal_entry_id": entry.id,
        },
    )
    return entry


@router.post("/depreciation")
def post_formal_fixed_asset_depreciation(
    request: FixedAssetDepreciationPostRequest,
    x_actor_id: str = Header(default="system"),
):
    event = "fixed_asset_accounting.depreciation.post"
    target_id = f"fixed-asset-depreciation:{request.account_set_id}:{request.period}"
    _require_permission(
        actor_id=x_actor_id,
        permission_code="fixed_asset_accounting.post",
        event=event,
        target_id=target_id,
        metadata={"account_set_id": request.account_set_id, "period": request.period},
    )
    result = post_fixed_asset_depreciation(request.account_set_id, request.period, x_actor_id)
    _record_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={
            "account_set_id": request.account_set_id,
            "period": request.period,
            "status": result.status,
            "depreciated_count": result.depreciated_count,
            "total_depreciation": str(result.total_depreciation),
        },
    )
    return result


@router.post("/impairment")
def post_formal_fixed_asset_impairment(
    request: FixedAssetImpairmentPostRequest,
    x_actor_id: str = Header(default="system"),
):
    event = "fixed_asset_accounting.impairment.post"
    target_id = f"fixed-asset:{request.asset_id}"
    _require_permission(
        actor_id=x_actor_id,
        permission_code="fixed_asset_accounting.impair",
        event=event,
        target_id=target_id,
        metadata={"account_set_id": request.account_set_id, "asset_id": request.asset_id, "period": request.period},
    )
    entry = record_fixed_asset_impairment(
        request.account_set_id,
        request.asset_id,
        request.period,
        request.amount,
        x_actor_id,
    )
    _record_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={
            "account_set_id": request.account_set_id,
            "asset_id": request.asset_id,
            "period": request.period,
            "amount": str(request.amount),
            "journal_entry_id": entry.id,
        },
    )
    return entry


@router.post("/disposal")
def post_formal_fixed_asset_disposal(
    request: FixedAssetDisposalPostRequest,
    x_actor_id: str = Header(default="system"),
):
    event = "fixed_asset_accounting.disposal.post"
    target_id = f"fixed-asset:{request.asset_id}"
    _require_permission(
        actor_id=x_actor_id,
        permission_code="fixed_asset_accounting.dispose",
        event=event,
        target_id=target_id,
        metadata={"account_set_id": request.account_set_id, "asset_id": request.asset_id, "period": request.period},
    )
    result = dispose_fixed_asset_formally(
        account_set_id=request.account_set_id,
        asset_id=request.asset_id,
        period=request.period,
        proceeds_amount=request.proceeds_amount,
        actor_id=x_actor_id,
        disposal_date=request.disposal_date,
        proceeds_account_code=request.proceeds_account_code,
        reason=request.reason,
    )
    _record_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={
            "account_set_id": request.account_set_id,
            "asset_id": request.asset_id,
            "period": request.period,
            "proceeds_amount": str(request.proceeds_amount),
            "disposal_gain_or_loss": str(result.disposal_gain_or_loss),
        },
    )
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
