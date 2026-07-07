from calendar import monthrange
from decimal import Decimal

from fastapi import HTTPException

from app.models.accounting import JournalEntryCreate, JournalLineCreate
from app.models.accrual_amortization import AccountingSchedule, AccountingScheduleCreate
from app.services.accounting_period_service import is_accounting_period_closed, validate_account_set
from app.services.accounting_service import get_chart_of_accounts, list_journal_entries, post_journal_entry


MONEY_QUANT = Decimal("0.01")
_ACCOUNTING_SCHEDULES: dict[str, AccountingSchedule] = {}


def reset_accrual_amortization_store() -> None:
    _ACCOUNTING_SCHEDULES.clear()


def create_accounting_schedule(payload: AccountingScheduleCreate) -> AccountingSchedule:
    validate_account_set(payload.account_set_id)
    if payload.end_period < payload.start_period:
        raise HTTPException(status_code=422, detail="计划结束期间不能早于开始期间。")
    schedule = AccountingSchedule(**payload.model_dump())
    _ACCOUNTING_SCHEDULES[_schedule_key(schedule.account_set_id, schedule.schedule_code)] = schedule
    return schedule


def get_accounting_schedule(account_set_id: str, schedule_code: str) -> AccountingSchedule:
    validate_account_set(account_set_id)
    schedule = _ACCOUNTING_SCHEDULES.get(_schedule_key(account_set_id, schedule_code))
    if schedule is None:
        raise HTTPException(status_code=404, detail="核算计划不存在。")
    return schedule


def list_accounting_schedules(account_set_id: str = "default") -> list[AccountingSchedule]:
    validate_account_set(account_set_id)
    schedules = [schedule for schedule in _ACCOUNTING_SCHEDULES.values() if schedule.account_set_id == account_set_id]
    schedules.sort(key=lambda item: item.schedule_code)
    return schedules


def calculate_even_monthly_amount(total_amount: Decimal, months: int) -> list[Decimal]:
    if months <= 0:
        raise HTTPException(status_code=422, detail="分摊月份数必须大于 0。")
    base = (total_amount / Decimal(months)).quantize(Decimal("0.01"))
    amounts = [base for _ in range(months)]
    difference = total_amount - sum(amounts)
    amounts[-1] = (amounts[-1] + difference).quantize(Decimal("0.01"))
    return amounts


def get_schedule_amount_for_period(schedule: AccountingSchedule, period: str) -> Decimal:
    periods = _periods_between(schedule.start_period, schedule.end_period)
    if period not in periods:
        raise HTTPException(status_code=422, detail="期间不在核算计划范围内。")
    amounts = calculate_even_monthly_amount(schedule.total_amount, len(periods))
    return amounts[periods.index(period)]


def post_schedule_for_period(account_set_id: str, schedule_code: str, period: str, actor_id: str):
    _validate_period_open(account_set_id, period)
    schedule = get_accounting_schedule(account_set_id, schedule_code)
    if schedule.status != "active":
        raise HTTPException(status_code=409, detail="核算计划未启用，不能生成本期分录。")

    amount = get_schedule_amount_for_period(schedule, period)
    source_id = f"schedule_posting:{account_set_id}:{period}:{schedule_code}"
    existing = _existing_entry(account_set_id, period, schedule.schedule_type, source_id)
    if existing is not None:
        return existing

    account_names = _account_names(account_set_id)
    entry = post_journal_entry(
        JournalEntryCreate(
            account_set_id=account_set_id,
            entry_date=_period_end_date(period),
            source_type=schedule.schedule_type,
            source_id=source_id,
            description=f"{period} {schedule.schedule_code} 核算计划生成",
            base_currency="CNY",
            created_by=actor_id,
            posted_by=actor_id,
            lines=[
                _journal_line(schedule.debit_account_code, account_names, "debit", amount, "核算计划借方"),
                _journal_line(schedule.credit_account_code, account_names, "credit", amount, "核算计划贷方"),
            ],
        )
    )
    _mark_schedule_posted(schedule, period)
    return entry


def _validate_period_open(account_set_id: str, period: str) -> None:
    validate_account_set(account_set_id)
    if is_accounting_period_closed(period, account_set_id):
        raise HTTPException(status_code=409, detail="会计期间已关闭，不能生成预提摊销正式分录。")


def _existing_entry(account_set_id: str, period: str, source_type: str, source_id: str):
    return next(
        (
            entry
            for entry in list_journal_entries(account_set_id, period).entries
            if entry.status == "posted" and entry.source_type == source_type and entry.source_id == source_id
        ),
        None,
    )


def _account_names(account_set_id: str) -> dict[str, str]:
    return {account.account_code: account.account_name for account in get_chart_of_accounts(account_set_id).accounts}


def _journal_line(
    account_code: str,
    account_names: dict[str, str],
    direction: str,
    amount: Decimal,
    description: str,
) -> JournalLineCreate:
    return JournalLineCreate(
        account_code=account_code,
        account_name=account_names.get(account_code, account_code),
        direction=direction,  # type: ignore[arg-type]
        original_amount=amount,
        base_amount=amount,
        description=description,
    )


def _mark_schedule_posted(schedule: AccountingSchedule, period: str) -> None:
    if period in schedule.posted_periods:
        return
    updated = schedule.model_copy(update={"posted_periods": [*schedule.posted_periods, period]})
    _ACCOUNTING_SCHEDULES[_schedule_key(schedule.account_set_id, schedule.schedule_code)] = updated


def _periods_between(start_period: str, end_period: str) -> list[str]:
    start_year, start_month = [int(part) for part in start_period.split("-")]
    end_year, end_month = [int(part) for part in end_period.split("-")]
    periods = []
    year = start_year
    month = start_month
    while (year, month) <= (end_year, end_month):
        periods.append(f"{year}-{month:02d}")
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
    return periods


def _period_end_date(period: str) -> str:
    year, month = [int(part) for part in period.split("-")]
    return f"{period}-{monthrange(year, month)[1]:02d}"


def _schedule_key(account_set_id: str, schedule_code: str) -> str:
    return f"{account_set_id}:{schedule_code}"
