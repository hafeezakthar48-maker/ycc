from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
import re
from uuid import uuid4

from fastapi import HTTPException

from app.models.fixed_asset import (
    FixedAssetCreateRequest,
    FixedAssetDepreciationRunResponse,
    FixedAssetDisposeRequest,
    FixedAssetInventoryRequest,
    FixedAssetListResponse,
    FixedAssetRecord,
    FixedAssetSaleRequest,
    FixedAssetSummary,
)
from app.services.accounting_period_service import validate_account_set


PERIOD_PATTERN = re.compile(r"^\d{4}-\d{2}$")
MONEY_ZERO = Decimal("0.00")
MONEY_QUANT = Decimal("0.01")

_assets: list[FixedAssetRecord] = []
_asset_sequences: dict[str, int] = {}


def reset_fixed_asset_store() -> None:
    global _assets, _asset_sequences
    _assets = []
    _asset_sequences = {}


def create_fixed_asset(request: FixedAssetCreateRequest) -> FixedAssetRecord:
    validate_account_set(request.account_set_id)
    now = _now()
    asset = FixedAssetRecord(
        id=f"fixed-asset-{uuid4().hex[:12]}",
        account_set_id=request.account_set_id,
        asset_code=_next_asset_code(request.acquisition_date),
        name=request.name,
        category=request.category,
        acquisition_date=request.acquisition_date,
        original_cost=_money(request.original_cost),
        salvage_value=_money(request.salvage_value),
        useful_life_months=request.useful_life_months,
        depreciation_method=request.depreciation_method,
        monthly_depreciation=_monthly_depreciation(request),
        accumulated_depreciation=MONEY_ZERO,
        net_book_value=_money(request.original_cost),
        status="active",
        location=request.location,
        custodian=request.custodian,
        created_at=now,
        updated_at=now,
    )
    _assets.append(asset)
    return asset


def list_fixed_assets(account_set_id: str = "default") -> FixedAssetListResponse:
    validate_account_set(account_set_id)
    assets = [asset for asset in _assets if asset.account_set_id == account_set_id]
    assets.sort(key=lambda asset: (asset.asset_code, asset.name))
    return FixedAssetListResponse(
        account_set_id=account_set_id,
        summary=_summary(assets),
        assets=assets,
    )


def run_monthly_depreciation(period: str, account_set_id: str = "default", operator: str = "财务主管") -> FixedAssetDepreciationRunResponse:
    _validate_period(period)
    validate_account_set(account_set_id)
    depreciated_assets: list[FixedAssetRecord] = []
    total_depreciation = MONEY_ZERO

    for asset in list(_assets):
        if asset.account_set_id != account_set_id or asset.status != "active":
            continue
        if asset.last_depreciated_period == period:
            continue
        depreciation_amount = _next_depreciation_amount(asset)
        if depreciation_amount <= MONEY_ZERO:
            continue
        updated = asset.model_copy(
            update={
                "accumulated_depreciation": _money(asset.accumulated_depreciation + depreciation_amount),
                "net_book_value": _money(asset.net_book_value - depreciation_amount),
                "last_depreciated_period": period,
                "updated_at": _now(),
            }
        )
        _replace_asset(updated)
        depreciated_assets.append(updated)
        total_depreciation += depreciation_amount

    return FixedAssetDepreciationRunResponse(
        account_set_id=account_set_id,
        period=period,
        operator=operator,
        depreciated_count=len(depreciated_assets),
        total_depreciation=_money(total_depreciation),
        assets=depreciated_assets,
    )


def dispose_fixed_asset(asset_id: str, disposal_date: str, reason: str, operator: str = "财务主管") -> FixedAssetRecord:
    request = FixedAssetDisposeRequest(disposal_date=disposal_date, reason=reason, operator=operator)
    asset = _get_asset(asset_id)
    _ensure_active(asset)
    updated = asset.model_copy(
        update={
            "status": "disposed",
            "disposal_date": request.disposal_date,
            "disposal_reason": request.reason,
            "disposed_by": request.operator,
            "updated_at": _now(),
        }
    )
    _replace_asset(updated)
    return updated


def sell_fixed_asset(asset_id: str, request: FixedAssetSaleRequest) -> FixedAssetRecord:
    asset = _get_asset(asset_id)
    _ensure_active(asset)
    sale_amount = _money(request.sale_amount)
    updated = asset.model_copy(
        update={
            "status": "sold",
            "sale_date": request.sale_date,
            "sale_amount": sale_amount,
            "sale_gain_or_loss": _money(sale_amount - asset.net_book_value),
            "sale_reason": request.reason,
            "sold_by": request.operator,
            "updated_at": _now(),
        }
    )
    _replace_asset(updated)
    return updated


def inventory_fixed_asset(asset_id: str, request: FixedAssetInventoryRequest) -> FixedAssetRecord:
    asset = _get_asset(asset_id)
    updated = asset.model_copy(
        update={
            "location": request.location,
            "custodian": request.custodian,
            "condition": request.condition,
            "inventory_status": "checked",
            "last_inventory_date": request.inventory_date,
            "last_inventory_by": request.operator,
            "inventory_note": request.note,
            "updated_at": _now(),
        }
    )
    _replace_asset(updated)
    return updated


def _next_asset_code(acquisition_date: str) -> str:
    month = acquisition_date[:7].replace("-", "")
    sequence = _asset_sequences.get(month, 0) + 1
    _asset_sequences[month] = sequence
    return f"FA-{month}-{sequence:04d}"


def _monthly_depreciation(request: FixedAssetCreateRequest) -> Decimal:
    depreciable_base = request.original_cost - request.salvage_value
    return _money(depreciable_base / Decimal(request.useful_life_months))


def _next_depreciation_amount(asset: FixedAssetRecord) -> Decimal:
    remaining_depreciable = asset.original_cost - asset.salvage_value - asset.accumulated_depreciation
    if remaining_depreciable <= MONEY_ZERO:
        return MONEY_ZERO
    return min(asset.monthly_depreciation, _money(remaining_depreciable))


def _summary(assets: list[FixedAssetRecord]) -> FixedAssetSummary:
    return FixedAssetSummary(
        asset_count=len(assets),
        active_count=sum(1 for asset in assets if asset.status == "active"),
        disposed_count=sum(1 for asset in assets if asset.status == "disposed"),
        sold_count=sum(1 for asset in assets if asset.status == "sold"),
        original_cost_total=_sum_money(asset.original_cost for asset in assets),
        accumulated_depreciation_total=_sum_money(asset.accumulated_depreciation for asset in assets),
        net_book_value_total=_sum_money(asset.net_book_value for asset in assets),
        monthly_depreciation_total=_sum_money(asset.monthly_depreciation for asset in assets if asset.status == "active"),
    )


def _sum_money(values) -> Decimal:
    return _money(sum(values, MONEY_ZERO))


def _replace_asset(updated: FixedAssetRecord) -> None:
    for index, asset in enumerate(_assets):
        if asset.id == updated.id:
            _assets[index] = updated
            return
    raise HTTPException(status_code=404, detail="固定资产不存在。")


def _get_asset(asset_id: str) -> FixedAssetRecord:
    asset = next((item for item in _assets if item.id == asset_id), None)
    if asset is None:
        raise HTTPException(status_code=404, detail="固定资产不存在。")
    return asset


def _ensure_active(asset: FixedAssetRecord) -> None:
    if asset.status != "active":
        raise HTTPException(status_code=409, detail="固定资产已退出使用，不能重复处置。")


def _validate_period(period: str) -> None:
    if not PERIOD_PATTERN.fullmatch(period):
        raise HTTPException(status_code=422, detail="折旧期间格式应为 YYYY-MM。")


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
