from fastapi import APIRouter, Header, HTTPException, Query

from app.models.fixed_asset import (
    FixedAssetCreateRequest,
    FixedAssetDepreciationRunRequest,
    FixedAssetDisposeRequest,
    FixedAssetInventoryRequest,
    FixedAssetSaleRequest,
)
from app.models.system_admin import AuditLogCreateRequest
from app.services.fixed_asset_service import (
    create_fixed_asset,
    dispose_fixed_asset,
    inventory_fixed_asset,
    list_fixed_assets,
    run_monthly_depreciation,
    sell_fixed_asset,
)
from app.services.system_admin_service import authorize, record_audit_log


router = APIRouter(prefix="/api/v1/fixed-assets", tags=["fixed-assets"])


@router.get("")
def get_fixed_assets(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    x_actor_id: str = Header(default="system"),
):
    event = "fixed_asset.list"
    target_id = f"fixed-assets:{account_set_id}"
    _require_fixed_asset_permission(
        actor_id=x_actor_id,
        permission_code="fixed_asset.read",
        event=event,
        target_id=target_id,
        metadata={"account_set_id": account_set_id},
    )
    payload = list_fixed_assets(account_set_id)
    _record_fixed_asset_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={"account_set_id": account_set_id, "asset_count": payload.summary.asset_count},
    )
    return payload


@router.post("")
def create_fixed_asset_record(
    request: FixedAssetCreateRequest,
    x_actor_id: str = Header(default="system"),
):
    event = "fixed_asset.create"
    _require_fixed_asset_permission(
        actor_id=x_actor_id,
        permission_code="fixed_asset.write",
        event=event,
        target_id="new-fixed-asset",
        metadata={"account_set_id": request.account_set_id, "name": request.name},
    )
    asset = create_fixed_asset(request)
    _record_fixed_asset_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=asset.id,
        metadata={
            "account_set_id": asset.account_set_id,
            "asset_code": asset.asset_code,
            "name": asset.name,
            "original_cost": str(asset.original_cost),
        },
    )
    return asset


@router.post("/depreciation/run")
def run_fixed_asset_depreciation(
    request: FixedAssetDepreciationRunRequest,
    x_actor_id: str = Header(default="system"),
):
    event = "fixed_asset.depreciation.run"
    target_id = f"fixed-asset-depreciation:{request.account_set_id}:{request.period}"
    _require_fixed_asset_permission(
        actor_id=x_actor_id,
        permission_code="fixed_asset.depreciate",
        event=event,
        target_id=target_id,
        metadata={"account_set_id": request.account_set_id, "period": request.period},
    )
    result = run_monthly_depreciation(request.period, request.account_set_id, request.operator)
    _record_fixed_asset_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={
            "account_set_id": result.account_set_id,
            "period": result.period,
            "operator": result.operator,
            "depreciated_count": result.depreciated_count,
            "total_depreciation": str(result.total_depreciation),
        },
    )
    return result


@router.post("/{asset_id}/dispose")
def dispose_fixed_asset_record(
    asset_id: str,
    request: FixedAssetDisposeRequest,
    x_actor_id: str = Header(default="system"),
):
    event = "fixed_asset.dispose"
    target_id = f"fixed-asset:{asset_id}"
    _require_fixed_asset_permission(
        actor_id=x_actor_id,
        permission_code="fixed_asset.dispose",
        event=event,
        target_id=target_id,
        metadata={"asset_id": asset_id, "operator": request.operator},
    )
    asset = dispose_fixed_asset(asset_id, request.disposal_date, request.reason, request.operator)
    _record_fixed_asset_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=asset.id,
        metadata={
            "account_set_id": asset.account_set_id,
            "asset_code": asset.asset_code,
            "status": asset.status,
            "operator": request.operator,
        },
    )
    return asset


@router.post("/{asset_id}/sell")
def sell_fixed_asset_record(
    asset_id: str,
    request: FixedAssetSaleRequest,
    x_actor_id: str = Header(default="system"),
):
    event = "fixed_asset.sell"
    target_id = f"fixed-asset:{asset_id}"
    _require_fixed_asset_permission(
        actor_id=x_actor_id,
        permission_code="fixed_asset.dispose",
        event=event,
        target_id=target_id,
        metadata={"asset_id": asset_id, "operator": request.operator},
    )
    asset = sell_fixed_asset(asset_id, request)
    _record_fixed_asset_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=asset.id,
        metadata={
            "account_set_id": asset.account_set_id,
            "asset_code": asset.asset_code,
            "status": asset.status,
            "sale_gain_or_loss": str(asset.sale_gain_or_loss),
            "operator": request.operator,
        },
    )
    return asset


@router.post("/{asset_id}/inventory")
def inventory_fixed_asset_record(
    asset_id: str,
    request: FixedAssetInventoryRequest,
    x_actor_id: str = Header(default="system"),
):
    event = "fixed_asset.inventory"
    target_id = f"fixed-asset:{asset_id}"
    _require_fixed_asset_permission(
        actor_id=x_actor_id,
        permission_code="fixed_asset.inventory",
        event=event,
        target_id=target_id,
        metadata={"asset_id": asset_id, "operator": request.operator},
    )
    asset = inventory_fixed_asset(asset_id, request)
    _record_fixed_asset_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=asset.id,
        metadata={
            "account_set_id": asset.account_set_id,
            "asset_code": asset.asset_code,
            "inventory_status": asset.inventory_status,
            "operator": request.operator,
        },
    )
    return asset


def _record_fixed_asset_audit(
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


def _require_fixed_asset_permission(
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

    _record_fixed_asset_audit(
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
