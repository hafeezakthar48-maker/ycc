from calendar import monthrange
from decimal import Decimal
import re

from fastapi import HTTPException

from app.models.accounting import AuxiliaryDimensionCreate, JournalEntryCreate, JournalLineCreate, JournalLineDimension
from app.models.fixed_asset_accounting import FixedAssetAccountingEntryBatch
from app.models.fixed_asset import FixedAssetRecord
from app.services.accounting_period_service import is_accounting_period_closed, validate_account_set
from app.services.accounting_service import (
    get_chart_of_accounts,
    list_journal_entries,
    post_journal_entry,
    upsert_auxiliary_dimension,
)
from app.services.fixed_asset_service import get_period_depreciation_summary, list_fixed_assets, run_monthly_depreciation


PERIOD_PATTERN = re.compile(r"^\d{4}-\d{2}$")
MONEY_ZERO = Decimal("0.00")


def reset_fixed_asset_accounting_store() -> None:
    # 当前正式核算事实写入正式分录库，本服务暂不维护额外持久状态。
    return None


def capitalize_fixed_asset(
    account_set_id: str,
    asset_id: str,
    period: str,
    credit_account_code: str,
    actor_id: str,
):
    _validate_period_open(account_set_id, period)
    asset = _get_asset(account_set_id, asset_id)
    source_type = "fixed_asset_capitalization"
    source_id = f"{source_type}:{account_set_id}:{asset.id}"
    existing = _existing_entry(account_set_id, period, source_type, source_id)
    if existing is not None:
        return existing

    _ensure_asset_dimension(asset)
    account_names = _account_names(account_set_id)
    amount = _money(asset.original_cost)
    return post_journal_entry(
        JournalEntryCreate(
            account_set_id=account_set_id,
            entry_date=_entry_date_for_period(asset.acquisition_date, period),
            source_type=source_type,
            source_id=source_id,
            description=f"{asset.asset_code} 固定资产资本化",
            base_currency="CNY",
            created_by=actor_id,
            posted_by=actor_id,
            lines=[
                JournalLineCreate(
                    account_code="1601",
                    account_name=account_names.get("1601", "固定资产"),
                    direction="debit",
                    original_amount=amount,
                    base_amount=amount,
                    description=f"{asset.asset_code} 原值入账",
                    dimensions=[JournalLineDimension(dimension_type="asset", dimension_code=asset.asset_code)],
                ),
                JournalLineCreate(
                    account_code=credit_account_code,
                    account_name=account_names.get(credit_account_code, credit_account_code),
                    direction="credit",
                    original_amount=amount,
                    base_amount=amount,
                    description=f"{asset.asset_code} 资本化来源",
                    dimensions=[JournalLineDimension(dimension_type="asset", dimension_code=asset.asset_code)],
                ),
            ],
        )
    )


def calculate_monthly_depreciation(original_cost: Decimal, salvage_value: Decimal, useful_life_months: int) -> Decimal:
    if useful_life_months <= 0:
        raise HTTPException(status_code=422, detail="折旧月数必须大于 0。")
    depreciable_amount = Decimal(original_cost) - Decimal(salvage_value)
    if depreciable_amount < MONEY_ZERO:
        raise HTTPException(status_code=422, detail="残值不能大于资产原值。")
    return _money(depreciable_amount / Decimal(useful_life_months))


def post_fixed_asset_depreciation(account_set_id: str, period: str, actor_id: str) -> FixedAssetAccountingEntryBatch:
    _validate_period_open(account_set_id, period)
    source_type = "fixed_asset_depreciation"
    source_prefix = f"{source_type}:{account_set_id}:{period}:"
    existing_entries = _existing_entries_by_prefix(account_set_id, period, source_type, source_prefix)
    existing_asset_ids = {entry.source_id.removeprefix(source_prefix) for entry in existing_entries}
    assets = {asset.id: asset for asset in list_fixed_assets(account_set_id).assets}
    rows = [
        row
        for row in get_period_depreciation_summary(account_set_id, period)
        if row["asset_id"] not in existing_asset_ids and _is_capitalized(account_set_id, row["asset_id"])
    ]
    if not rows:
        if existing_entries:
            return FixedAssetAccountingEntryBatch(
                account_set_id=account_set_id,
                period=period,
                status="existing",
                depreciated_count=len(existing_entries),
                total_depreciation=_entry_amount(existing_entries),
                entries=existing_entries,
            )
        return FixedAssetAccountingEntryBatch(
            account_set_id=account_set_id,
            period=period,
            status="skipped",
            depreciated_count=0,
            total_depreciation=MONEY_ZERO,
            entries=[],
        )

    account_names = _account_names(account_set_id)
    generated_entries = []
    for row in rows:
        asset = assets[row["asset_id"]]
        _ensure_asset_dimension(asset)
        amount = _money(row["amount"])
        source_id = f"{source_prefix}{asset.id}"
        generated_entries.append(
            post_journal_entry(
                JournalEntryCreate(
                    account_set_id=account_set_id,
                    entry_date=_period_end_date(period),
                    source_type=source_type,
                    source_id=source_id,
                    description=f"{period} {asset.asset_code} 固定资产折旧",
                    base_currency="CNY",
                    created_by=actor_id,
                    posted_by=actor_id,
                    lines=[
                        JournalLineCreate(
                            account_code=row["debit_account_code"],
                            account_name=account_names.get(row["debit_account_code"], row["debit_account_code"]),
                            direction="debit",
                            original_amount=amount,
                            base_amount=amount,
                            description=f"{asset.asset_code} 折旧费用",
                            dimensions=[JournalLineDimension(dimension_type="asset", dimension_code=asset.asset_code)],
                        ),
                        JournalLineCreate(
                            account_code=row["credit_account_code"],
                            account_name=account_names.get(row["credit_account_code"], row["credit_account_code"]),
                            direction="credit",
                            original_amount=amount,
                            base_amount=amount,
                            description=f"{asset.asset_code} 累计折旧",
                            dimensions=[JournalLineDimension(dimension_type="asset", dimension_code=asset.asset_code)],
                        ),
                    ],
                )
            )
        )

    run_monthly_depreciation(period, account_set_id, operator=actor_id)
    return FixedAssetAccountingEntryBatch(
        account_set_id=account_set_id,
        period=period,
        status="generated",
        depreciated_count=len(generated_entries),
        total_depreciation=_entry_amount(generated_entries),
        entries=generated_entries,
    )


def _validate_period_open(account_set_id: str, period: str) -> None:
    if not PERIOD_PATTERN.fullmatch(period):
        raise HTTPException(status_code=422, detail="会计期间格式应为 YYYY-MM。")
    validate_account_set(account_set_id)
    if is_accounting_period_closed(period, account_set_id):
        raise HTTPException(status_code=409, detail="会计期间已关闭，不能生成固定资产正式分录。")


def _get_asset(account_set_id: str, asset_id: str) -> FixedAssetRecord:
    payload = list_fixed_assets(account_set_id)
    asset = next((item for item in payload.assets if item.id == asset_id), None)
    if asset is None:
        raise HTTPException(status_code=404, detail="固定资产不存在。")
    return asset


def _ensure_asset_dimension(asset: FixedAssetRecord) -> None:
    upsert_auxiliary_dimension(
        AuxiliaryDimensionCreate(
            account_set_id=asset.account_set_id,
            dimension_type="asset",
            dimension_code=asset.asset_code,
            dimension_name=asset.name,
        )
    )


def _account_names(account_set_id: str) -> dict[str, str]:
    return {account.account_code: account.account_name for account in get_chart_of_accounts(account_set_id).accounts}


def _existing_entry(account_set_id: str, period: str, source_type: str, source_id: str):
    return next(
        (
            entry
            for entry in list_journal_entries(account_set_id, period).entries
            if entry.status == "posted" and entry.source_type == source_type and entry.source_id == source_id
        ),
        None,
    )


def _existing_entries_by_prefix(account_set_id: str, period: str, source_type: str, source_prefix: str):
    return [
        entry
        for entry in list_journal_entries(account_set_id, period).entries
        if entry.status == "posted" and entry.source_type == source_type and entry.source_id.startswith(source_prefix)
    ]


def _is_capitalized(account_set_id: str, asset_id: str) -> bool:
    source_id = f"fixed_asset_capitalization:{account_set_id}:{asset_id}"
    return any(
        entry.status == "posted"
        and entry.source_type == "fixed_asset_capitalization"
        and entry.source_id == source_id
        for entry in list_journal_entries(account_set_id).entries
    )


def _entry_amount(entries) -> Decimal:
    return _money(
        sum(
            (
                line.base_amount
                for entry in entries
                for line in entry.lines
                if line.direction == "debit"
            ),
            MONEY_ZERO,
        )
    )


def _entry_date_for_period(preferred_date: str, period: str) -> str:
    if preferred_date.startswith(f"{period}-"):
        return preferred_date
    return _period_end_date(period)


def _period_end_date(period: str) -> str:
    year, month = (int(part) for part in period.split("-"))
    return f"{period}-{monthrange(year, month)[1]:02d}"


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))
