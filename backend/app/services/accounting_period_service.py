from dataclasses import dataclass
from datetime import UTC, datetime
import re

from fastapi import HTTPException

from app.data.sample_finance_data import SAMPLE_FINANCE_DATA
from app.models.accounting_period import (
    AccountingPeriodItem,
    AccountingPeriodListResponse,
    AccountSetItem,
    AccountSetListResponse,
)


DEFAULT_ACCOUNT_SET_ID = "default"
PERIOD_PATTERN = re.compile(r"^\d{4}-\d{2}$")

DEFAULT_ACCOUNT_SET = AccountSetItem(
    id=DEFAULT_ACCOUNT_SET_ID,
    name="默认账套",
    base_currency="CNY",
    accounting_standard="企业会计准则",
    is_default=True,
)
CROSS_BORDER_ACCOUNT_SET = AccountSetItem(
    id="cross_border",
    name="跨境电商账套",
    base_currency="CNY",
    accounting_standard="企业会计准则",
    is_default=False,
)
ACCOUNT_SETS: tuple[AccountSetItem, ...] = (DEFAULT_ACCOUNT_SET, CROSS_BORDER_ACCOUNT_SET)
ACCOUNT_SET_IDS = {account_set.id for account_set in ACCOUNT_SETS}


@dataclass
class _PeriodState:
    status: str = "open"
    closed_by: str | None = None
    closed_at: str | None = None


_period_states: dict[tuple[str, str], _PeriodState] = {}


def reset_accounting_period_store() -> None:
    _period_states.clear()


def list_account_sets() -> AccountSetListResponse:
    return AccountSetListResponse(account_sets=list(ACCOUNT_SETS))


def list_accounting_periods(account_set_id: str = DEFAULT_ACCOUNT_SET_ID) -> AccountingPeriodListResponse:
    validate_account_set(account_set_id)
    stats = _voucher_period_stats()
    known_periods = {record.period for record in SAMPLE_FINANCE_DATA}
    known_periods.update(period for period_account_set, period in stats if period_account_set == account_set_id)
    known_periods.update(period for period_account_set, period in _period_states if period_account_set == account_set_id)

    periods = [
        _period_item(account_set_id=account_set_id, period=period, stats=stats)
        for period in sorted(known_periods, reverse=True)
    ]
    return AccountingPeriodListResponse(account_set_id=account_set_id, periods=periods)


def close_accounting_period(period: str, operator: str, account_set_id: str = DEFAULT_ACCOUNT_SET_ID) -> AccountingPeriodItem:
    _validate_period(period)
    validate_account_set(account_set_id)
    _validate_period_can_close(account_set_id, period)
    _period_states[(account_set_id, period)] = _PeriodState(
        status="closed",
        closed_by=operator,
        closed_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )
    return _period_item(account_set_id=account_set_id, period=period, stats=_voucher_period_stats())


def reopen_accounting_period(period: str, operator: str, account_set_id: str = DEFAULT_ACCOUNT_SET_ID) -> AccountingPeriodItem:
    _validate_period(period)
    validate_account_set(account_set_id)
    _period_states[(account_set_id, period)] = _PeriodState(status="open")
    return _period_item(account_set_id=account_set_id, period=period, stats=_voucher_period_stats())


def is_accounting_period_closed(period: str, account_set_id: str = DEFAULT_ACCOUNT_SET_ID) -> bool:
    _validate_period(period)
    validate_account_set(account_set_id)
    state = _period_states.get((account_set_id, period), _PeriodState())
    return state.status == "closed"


def _period_item(
    account_set_id: str,
    period: str,
    stats: dict[tuple[str, str], tuple[int, int]],
) -> AccountingPeriodItem:
    state = _period_states.get((account_set_id, period), _PeriodState())
    voucher_count, posted_voucher_count = stats.get((account_set_id, period), (0, 0))
    return AccountingPeriodItem(
        account_set_id=account_set_id,
        period=period,
        status=state.status,  # type: ignore[arg-type]
        closed_by=state.closed_by,
        closed_at=state.closed_at,
        voucher_count=voucher_count,
        posted_voucher_count=posted_voucher_count,
    )


def _voucher_period_stats() -> dict[tuple[str, str], tuple[int, int]]:
    from app.services.voucher_center_service import list_vouchers

    stats: dict[tuple[str, str], tuple[int, int]] = {}
    for voucher in list_vouchers().vouchers:
        period = voucher.voucher_date[:7]
        key = (voucher.account_set_id, period)
        voucher_count, posted_voucher_count = stats.get(key, (0, 0))
        stats[key] = (
            voucher_count + 1,
            posted_voucher_count + (1 if voucher.posting_status == "posted" else 0),
        )
    return stats


def validate_account_set(account_set_id: str) -> None:
    if account_set_id not in ACCOUNT_SET_IDS:
        raise HTTPException(status_code=404, detail="账套不存在。")


def _validate_period_can_close(account_set_id: str, period: str) -> None:
    from app.services.voucher_center_service import list_vouchers

    unposted_vouchers = [
        voucher
        for voucher in list_vouchers(account_set_id).vouchers
        if voucher.voucher_date.startswith(f"{period}-") and voucher.posting_status != "posted"
    ]
    if unposted_vouchers:
        raise HTTPException(status_code=409, detail="期间存在未过账凭证，不能结账。")


def _validate_period(period: str) -> None:
    if not PERIOD_PATTERN.fullmatch(period):
        raise HTTPException(status_code=422, detail="会计期间格式应为 YYYY-MM。")
