from fastapi import APIRouter, Header, HTTPException, Query

from app.models.inventory_accounting import (
    InventoryAccountingSummaryResponse,
    InventoryCountVarianceRequest,
    InventoryImpairmentRequest,
    InventoryPurchaseReceiptRequest,
    InventorySalesIssueRequest,
)
from app.models.system_admin import AuditLogCreateRequest
from app.services.inventory_accounting_service import (
    list_inventory_balances,
    list_inventory_movements,
    post_purchase_receipt,
    post_sales_issue,
    record_inventory_count_variance,
    record_inventory_impairment,
)
from app.services.system_admin_service import authorize, record_audit_log


router = APIRouter(prefix="/api/v1/inventory-accounting", tags=["inventory-accounting"])


@router.get("/balances")
def get_inventory_accounting_balances(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    x_actor_id: str = Header(default="system"),
):
    event = "inventory_accounting.balance.read"
    target_id = f"inventory-accounting:{account_set_id}"
    _require_permission(
        actor_id=x_actor_id,
        permission_code="inventory_accounting.read",
        event=event,
        target_id=target_id,
        metadata={"account_set_id": account_set_id},
    )
    balances = list_inventory_balances(account_set_id)
    movements = list_inventory_movements(account_set_id)
    _record_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={
            "account_set_id": account_set_id,
            "balance_count": len(balances),
            "movement_count": len(movements),
        },
    )
    return InventoryAccountingSummaryResponse(
        account_set_id=account_set_id,
        total_balances=len(balances),
        total_movements=len(movements),
        balances=balances,
        movements=movements,
    )


@router.post("/purchase-receipts")
def post_inventory_purchase_receipt(
    request: InventoryPurchaseReceiptRequest,
    x_actor_id: str = Header(default="system"),
):
    event = "inventory_accounting.receipt.post"
    target_id = f"inventory-receipt:{request.account_set_id}:{request.period}:{request.sku_id}"
    _require_permission(
        actor_id=x_actor_id,
        permission_code="inventory_accounting.receipt",
        event=event,
        target_id=target_id,
        metadata=_request_metadata(request),
    )
    movement = post_purchase_receipt(
        account_set_id=request.account_set_id,
        sku_id=request.sku_id,
        warehouse_id=request.warehouse_id,
        period=request.period,
        quantity=request.quantity,
        amount=request.amount,
        supplier_id=request.supplier_id,
        actor_id=x_actor_id,
    )
    _record_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={**_request_metadata(request), "movement_id": movement.movement_id, "journal_entry_id": movement.journal_entry_id},
    )
    return movement


@router.post("/sales-issues")
def post_inventory_sales_issue(
    request: InventorySalesIssueRequest,
    x_actor_id: str = Header(default="system"),
):
    event = "inventory_accounting.sales_issue.post"
    target_id = f"inventory-sales-issue:{request.account_set_id}:{request.period}:{request.sku_id}"
    _require_permission(
        actor_id=x_actor_id,
        permission_code="inventory_accounting.issue",
        event=event,
        target_id=target_id,
        metadata=_request_metadata(request),
    )
    result = post_sales_issue(
        account_set_id=request.account_set_id,
        sku_id=request.sku_id,
        warehouse_id=request.warehouse_id,
        period=request.period,
        quantity=request.quantity,
        actor_id=x_actor_id,
    )
    _record_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={**_request_metadata(request), "journal_entry_id": result.journal_entry_id, "cost_amount": str(result.cost_amount)},
    )
    return result


@router.post("/impairments")
def post_inventory_impairment(
    request: InventoryImpairmentRequest,
    x_actor_id: str = Header(default="system"),
):
    event = "inventory_accounting.impairment.post"
    target_id = f"inventory-impairment:{request.account_set_id}:{request.period}:{request.sku_id}"
    _require_permission(
        actor_id=x_actor_id,
        permission_code="inventory_accounting.impair",
        event=event,
        target_id=target_id,
        metadata=_request_metadata(request),
    )
    entry = record_inventory_impairment(
        account_set_id=request.account_set_id,
        sku_id=request.sku_id,
        period=request.period,
        amount=request.amount,
        actor_id=x_actor_id,
    )
    _record_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={**_request_metadata(request), "journal_entry_id": entry.id},
    )
    return entry


@router.post("/count-variances")
def post_inventory_count_variance(
    request: InventoryCountVarianceRequest,
    x_actor_id: str = Header(default="system"),
):
    event = "inventory_accounting.count_variance.post"
    target_id = f"inventory-count-variance:{request.account_set_id}:{request.period}:{request.sku_id}:{request.warehouse_id}"
    _require_permission(
        actor_id=x_actor_id,
        permission_code="inventory_accounting.count",
        event=event,
        target_id=target_id,
        metadata=_request_metadata(request),
    )
    result = record_inventory_count_variance(
        account_set_id=request.account_set_id,
        sku_id=request.sku_id,
        warehouse_id=request.warehouse_id,
        period=request.period,
        actual_quantity=request.actual_quantity,
        actor_id=x_actor_id,
        approved_by=request.approved_by,
        approved_at=request.approved_at,
    )
    _record_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={**_request_metadata(request), "journal_entry_id": result.journal_entry_id, "variance_type": result.variance_type},
    )
    return result


def _request_metadata(request) -> dict[str, str | int | float | bool | None]:
    return {
        "account_set_id": request.account_set_id,
        "period": request.period,
        "sku_id": request.sku_id,
        "warehouse_id": getattr(request, "warehouse_id", None),
    }


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
