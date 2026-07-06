from calendar import monthrange
from decimal import Decimal
import re

from fastapi import HTTPException

from app.models.accounting import AuxiliaryDimensionCreate, JournalEntryCreate, JournalLineCreate, JournalLineDimension
from app.models.fixed_asset import FixedAssetRecord, FixedAssetSaleRequest
from app.models.fixed_asset_accounting import (
    FixedAssetAccountingEntryBatch,
    FixedAssetDisposalAccountingResult,
    FormalAssetAccountingCard,
)
from app.services.accounting_period_service import is_accounting_period_closed, validate_account_set
from app.services.accounting_service import (
    get_chart_of_accounts,
    list_journal_entries,
    post_journal_entry,
    upsert_auxiliary_dimension,
)
from app.services.fixed_asset_service import (
    dispose_fixed_asset,
    get_period_depreciation_summary,
    list_fixed_assets,
    run_monthly_depreciation,
    sell_fixed_asset,
)


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


def list_formal_asset_cards(account_set_id: str = "default") -> list[FormalAssetAccountingCard]:
    validate_account_set(account_set_id)
    entries = list_journal_entries(account_set_id).entries
    cards: list[FormalAssetAccountingCard] = []
    for asset in list_fixed_assets(account_set_id).assets:
        capitalization_entry = _capitalization_entry(entries, account_set_id, asset.id)
        depreciation_entries = _entries_by_prefix(entries, "fixed_asset_depreciation", f"fixed_asset_depreciation:{account_set_id}:")
        asset_depreciation_entries = [
            entry for entry in depreciation_entries if entry.source_id.endswith(f":{asset.id}")
        ]
        impairment_entries = _entries_by_prefix(
            entries,
            "fixed_asset_impairment",
            f"fixed_asset_impairment:{account_set_id}:",
        )
        asset_impairment_entries = [
            entry for entry in impairment_entries if entry.source_id.endswith(f":{asset.id}")
        ]
        disposal_entries = _entries_by_prefix(entries, "fixed_asset_disposal", f"fixed_asset_disposal:{account_set_id}:")
        asset_disposal_entries = [
            entry for entry in disposal_entries if entry.source_id.endswith(f":{asset.id}")
        ]
        impairment_amount = _asset_impairment_amount(asset_impairment_entries)
        cards.append(
            FormalAssetAccountingCard(
                account_set_id=asset.account_set_id,
                asset_id=asset.id,
                asset_code=asset.asset_code,
                asset_name=asset.name,
                category=asset.category,
                acquisition_date=asset.acquisition_date,
                original_cost=asset.original_cost,
                salvage_value=asset.salvage_value,
                useful_life_months=asset.useful_life_months,
                monthly_depreciation=asset.monthly_depreciation,
                accumulated_depreciation=asset.accumulated_depreciation,
                impairment_amount=impairment_amount,
                net_book_value=max(MONEY_ZERO, _money(asset.net_book_value - impairment_amount)),
                asset_status=asset.status,
                formal_accounting_status=_formal_status(
                    asset,
                    capitalization_entry is not None,
                    bool(asset_depreciation_entries),
                    bool(asset_impairment_entries),
                    bool(asset_disposal_entries),
                ),
                capitalization_entry_id=capitalization_entry.id if capitalization_entry else None,
                last_depreciation_entry_id=asset_depreciation_entries[-1].id if asset_depreciation_entries else None,
                last_depreciated_period=asset.last_depreciated_period,
                impairment_entry_ids=[entry.id for entry in asset_impairment_entries],
                disposal_entry_ids=[entry.id for entry in asset_disposal_entries],
            )
        )
    return cards


def record_fixed_asset_impairment(
    account_set_id: str,
    asset_id: str,
    period: str,
    amount: Decimal,
    actor_id: str,
):
    _validate_period_open(account_set_id, period)
    asset = _get_asset(account_set_id, asset_id)
    _ensure_active(asset)
    _ensure_capitalized(account_set_id, asset.id)
    amount = _money(amount)
    if amount <= MONEY_ZERO:
        raise HTTPException(status_code=422, detail="减值金额必须大于 0。")
    source_type = "fixed_asset_impairment"
    source_id = f"{source_type}:{account_set_id}:{period}:{asset.id}"
    existing = _existing_entry(account_set_id, period, source_type, source_id)
    if existing is not None:
        return existing

    _ensure_asset_dimension(asset)
    account_names = _account_names(account_set_id)
    return post_journal_entry(
        JournalEntryCreate(
            account_set_id=account_set_id,
            entry_date=_period_end_date(period),
            source_type=source_type,
            source_id=source_id,
            description=f"{period} {asset.asset_code} 固定资产减值",
            base_currency="CNY",
            created_by=actor_id,
            posted_by=actor_id,
            lines=[
                _journal_line("6701", account_names, "debit", amount, f"{asset.asset_code} 减值损失", asset),
                _journal_line("1603", account_names, "credit", amount, f"{asset.asset_code} 减值准备", asset),
            ],
        )
    )


def dispose_fixed_asset_formally(
    account_set_id: str,
    asset_id: str,
    period: str,
    proceeds_amount: Decimal,
    actor_id: str,
    disposal_date: str | None = None,
    proceeds_account_code: str = "1002",
    reason: str = "固定资产正式处置",
) -> FixedAssetDisposalAccountingResult:
    _validate_period_open(account_set_id, period)
    asset = _get_asset(account_set_id, asset_id)
    _ensure_active(asset)
    _ensure_capitalized(account_set_id, asset.id)
    source_type = "fixed_asset_disposal"
    source_id = f"{source_type}:{account_set_id}:{period}:{asset.id}"
    existing = _existing_entry(account_set_id, period, source_type, source_id)
    if existing is not None:
        return _disposal_result(account_set_id, period, asset, _disposal_gain_or_loss([existing]), [existing])

    proceeds = _money(proceeds_amount)
    if proceeds < MONEY_ZERO:
        raise HTTPException(status_code=422, detail="处置收入不能小于 0。")
    _ensure_asset_dimension(asset)
    account_names = _account_names(account_set_id)
    impairment_amount = _asset_impairment_amount(
        [
            entry
            for entry in list_journal_entries(account_set_id).entries
            if entry.source_type == "fixed_asset_impairment" and entry.source_id.endswith(f":{asset.id}")
        ]
    )
    original_cost = _money(asset.original_cost)
    accumulated_depreciation = _money(asset.accumulated_depreciation)
    net_book_value = _money(original_cost - accumulated_depreciation - impairment_amount)
    gain_or_loss = _money(proceeds - net_book_value)
    lines = [
        _journal_line("1606", account_names, "debit", original_cost, f"{asset.asset_code} 转入清理", asset),
        _journal_line("1601", account_names, "credit", original_cost, f"{asset.asset_code} 转出原值", asset),
    ]
    if accumulated_depreciation > MONEY_ZERO:
        lines.extend(
            [
                _journal_line("1602", account_names, "debit", accumulated_depreciation, f"{asset.asset_code} 转出累计折旧", asset),
                _journal_line("1606", account_names, "credit", accumulated_depreciation, f"{asset.asset_code} 累计折旧冲减清理", asset),
            ]
        )
    if impairment_amount > MONEY_ZERO:
        lines.extend(
            [
                _journal_line("1603", account_names, "debit", impairment_amount, f"{asset.asset_code} 转出减值准备", asset),
                _journal_line("1606", account_names, "credit", impairment_amount, f"{asset.asset_code} 减值准备冲减清理", asset),
            ]
        )
    if proceeds > MONEY_ZERO:
        lines.extend(
            [
                _journal_line(proceeds_account_code, account_names, "debit", proceeds, f"{asset.asset_code} 处置收入", asset),
                _journal_line("1606", account_names, "credit", proceeds, f"{asset.asset_code} 处置收入转清理", asset),
            ]
        )
    if gain_or_loss > MONEY_ZERO:
        lines.extend(
            [
                _journal_line("1606", account_names, "debit", gain_or_loss, f"{asset.asset_code} 处置收益结转", asset),
                _journal_line("6301", account_names, "credit", gain_or_loss, f"{asset.asset_code} 处置收益", asset),
            ]
        )
    elif gain_or_loss < MONEY_ZERO:
        loss = abs(gain_or_loss)
        lines.extend(
            [
                _journal_line("6711", account_names, "debit", loss, f"{asset.asset_code} 处置损失", asset),
                _journal_line("1606", account_names, "credit", loss, f"{asset.asset_code} 处置损失结转", asset),
            ]
        )

    entry = post_journal_entry(
        JournalEntryCreate(
            account_set_id=account_set_id,
            entry_date=disposal_date or _period_end_date(period),
            source_type=source_type,
            source_id=source_id,
            description=f"{period} {asset.asset_code} 固定资产处置",
            base_currency="CNY",
            created_by=actor_id,
            posted_by=actor_id,
            lines=lines,
        )
    )
    if proceeds > MONEY_ZERO:
        updated = sell_fixed_asset(
            asset.id,
            FixedAssetSaleRequest(
                sale_date=disposal_date or _period_end_date(period),
                sale_amount=proceeds,
                reason=reason,
                operator=actor_id,
            ),
        )
    else:
        updated = dispose_fixed_asset(asset.id, disposal_date or _period_end_date(period), reason, actor_id)
    return _disposal_result(account_set_id, period, updated, gain_or_loss, [entry])


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


def _capitalization_entry(entries, account_set_id: str, asset_id: str):
    source_id = f"fixed_asset_capitalization:{account_set_id}:{asset_id}"
    return next(
        (
            entry
            for entry in entries
            if entry.status == "posted" and entry.source_type == "fixed_asset_capitalization" and entry.source_id == source_id
        ),
        None,
    )


def _entries_by_prefix(entries, source_type: str, source_prefix: str):
    return [
        entry
        for entry in entries
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


def _ensure_capitalized(account_set_id: str, asset_id: str) -> None:
    if not _is_capitalized(account_set_id, asset_id):
        raise HTTPException(status_code=409, detail="固定资产尚未正式入账，不能执行后续正式核算。")


def _ensure_active(asset: FixedAssetRecord) -> None:
    if asset.status != "active":
        raise HTTPException(status_code=409, detail="固定资产已处置，不能重复执行正式核算。")


def _asset_impairment_amount(entries) -> Decimal:
    return _money(
        sum(
            (
                line.base_amount
                for entry in entries
                for line in entry.lines
                if line.account_code == "1603" and line.direction == "credit"
            ),
            MONEY_ZERO,
        )
    )


def _formal_status(
    asset: FixedAssetRecord,
    is_capitalized: bool,
    has_depreciation: bool,
    has_impairment: bool,
    has_disposal: bool,
):
    if asset.status == "sold":
        return "sold"
    if asset.status == "disposed" or has_disposal:
        return "disposed"
    if has_impairment:
        return "impaired"
    if has_depreciation or asset.last_depreciated_period:
        return "depreciating"
    if is_capitalized:
        return "capitalized"
    return "not_capitalized"


def _journal_line(
    account_code: str,
    account_names: dict[str, str],
    direction: str,
    amount: Decimal,
    description: str,
    asset: FixedAssetRecord,
) -> JournalLineCreate:
    return JournalLineCreate(
        account_code=account_code,
        account_name=account_names.get(account_code, account_code),
        direction=direction,  # type: ignore[arg-type]
        original_amount=_money(amount),
        base_amount=_money(amount),
        description=description,
        dimensions=[JournalLineDimension(dimension_type="asset", dimension_code=asset.asset_code)],
    )


def _disposal_gain_or_loss(entries) -> Decimal:
    gain = sum(
        (
            line.base_amount
            for entry in entries
            for line in entry.lines
            if line.account_code == "6301" and line.direction == "credit"
        ),
        MONEY_ZERO,
    )
    loss = sum(
        (
            line.base_amount
            for entry in entries
            for line in entry.lines
            if line.account_code == "6711" and line.direction == "debit"
        ),
        MONEY_ZERO,
    )
    return _money(gain - loss)


def _disposal_result(
    account_set_id: str,
    period: str,
    asset: FixedAssetRecord,
    gain_or_loss: Decimal,
    entries,
) -> FixedAssetDisposalAccountingResult:
    return FixedAssetDisposalAccountingResult(
        account_set_id=account_set_id,
        period=period,
        asset_id=asset.id,
        asset_code=asset.asset_code,
        asset_status=asset.status,
        clearing_account_code="1606",
        disposal_gain_or_loss=_money(gain_or_loss),
        entries=entries,
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
