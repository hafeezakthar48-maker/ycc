from __future__ import annotations

from calendar import monthrange
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException

from app.models.period_close import PeriodCloseCheckItem, PeriodCloseRun, PeriodCloseRunCreate, PeriodCloseRunListResponse
from app.services.accounting_period_service import validate_account_set


_PERIOD_CLOSE_RUNS: dict[str, PeriodCloseRun] = {}


def reset_period_close_store() -> None:
    _PERIOD_CLOSE_RUNS.clear()


def start_period_close_run(payload: PeriodCloseRunCreate) -> PeriodCloseRun:
    validate_account_set(payload.account_set_id)
    now = _now_iso()
    run = PeriodCloseRun(
        run_id=f"pclose_{uuid4().hex}",
        account_set_id=payload.account_set_id,
        period=payload.period,
        close_type=payload.close_type,
        status="draft",
        requested_by=payload.requested_by,
        created_at=now,
        updated_at=now,
    )
    _PERIOD_CLOSE_RUNS[run.run_id] = run
    return run


def get_period_close_run(run_id: str) -> PeriodCloseRun:
    run = _PERIOD_CLOSE_RUNS.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="期间结账运行记录不存在。")
    return run


def list_period_close_runs(
    account_set_id: str = "default",
    period: str | None = None,
) -> PeriodCloseRunListResponse:
    validate_account_set(account_set_id)
    runs = [
        run
        for run in _PERIOD_CLOSE_RUNS.values()
        if run.account_set_id == account_set_id and (period is None or run.period == period)
    ]
    runs.sort(key=lambda run: (run.created_at, run.run_id), reverse=True)
    return PeriodCloseRunListResponse(
        account_set_id=account_set_id,
        period=period,
        total=len(runs),
        runs=runs,
    )


def run_period_close_checks(account_set_id: str, period: str) -> list[PeriodCloseCheckItem]:
    validate_account_set(account_set_id)
    from app.services.accounting_period_service import is_accounting_period_closed, list_accounting_periods
    from app.services.accounting_service import get_chart_of_accounts, get_exchange_rate, list_journal_entries
    from app.services.voucher_center_service import list_vouchers

    periods = {item.period for item in list_accounting_periods(account_set_id).periods}
    entries = list_journal_entries(account_set_id, period).entries
    vouchers = [
        voucher
        for voucher in list_vouchers(account_set_id).vouchers
        if voucher.voucher_date.startswith(f"{period}-")
    ]
    active_accounts = {account.account_code for account in get_chart_of_accounts(account_set_id).accounts if account.is_active}

    items = [
        _check_item(
            "period_exists",
            "期间存在",
            period in periods,
            "指定会计期间存在，可以纳入结账流程。",
            "指定会计期间不存在，不能执行结账。",
            {"period": period},
        ),
        _check_item(
            "period_not_closed",
            "期间未关闭",
            not is_accounting_period_closed(period, account_set_id),
            "会计期间处于可结账状态。",
            "会计期间已关闭，不能重复关闭。",
            {"period": period},
        ),
        _journal_entries_balanced_check(entries),
        _voucher_posted_check(vouchers),
        _account_subjects_active_check(entries, active_accounts),
        _currency_rates_ready_check(account_set_id, period, entries, get_exchange_rate),
        PeriodCloseCheckItem(
            check_code="depreciation_ready",
            check_name="固定资产折旧准备",
            status="passed",
            severity="warning",
            message="固定资产折旧将在生成结账动作时重新计算并保持幂等。",
        ),
        PeriodCloseCheckItem(
            check_code="payroll_ready",
            check_name="工资计提准备",
            status="passed",
            severity="warning",
            message="工资计提将在生成结账动作时按可用工资摘要生成。",
        ),
        PeriodCloseCheckItem(
            check_code="tax_rule_ready",
            check_name="税费计提规则准备",
            status="warning",
            severity="warning",
            message="未配置税费计提规则时，税费计提动作会跳过。",
        ),
    ]
    return items


def has_blocking_check(items: list[PeriodCloseCheckItem]) -> bool:
    return any(item.status == "failed" and item.severity == "blocker" for item in items)


def _journal_entries_balanced_check(entries) -> PeriodCloseCheckItem:
    unbalanced_ids = []
    for entry in entries:
        debit_total = sum((line.base_amount for line in entry.lines if line.direction == "debit"), Decimal("0.00"))
        credit_total = sum((line.base_amount for line in entry.lines if line.direction == "credit"), Decimal("0.00"))
        if debit_total != credit_total:
            unbalanced_ids.append(entry.id)
    return _check_item(
        "journal_entries_balanced",
        "正式分录借贷平衡",
        not unbalanced_ids,
        "本期间正式分录均借贷平衡。",
        "本期间存在借贷不平衡的正式分录。",
        {"unbalanced_count": len(unbalanced_ids)},
    )


def _voucher_posted_check(vouchers) -> PeriodCloseCheckItem:
    unposted_count = sum(1 for voucher in vouchers if voucher.posting_status != "posted")
    return _check_item(
        "voucher_posted",
        "凭证已过账",
        unposted_count == 0,
        "本期间不存在未过账凭证。",
        "本期间存在未过账凭证，不能关闭。",
        {"unposted_count": unposted_count},
    )


def _account_subjects_active_check(entries, active_accounts: set[str]) -> PeriodCloseCheckItem:
    inactive_codes = {
        line.account_code
        for entry in entries
        for line in entry.lines
        if line.account_code not in active_accounts
    }
    return _check_item(
        "account_subjects_active",
        "科目有效",
        not inactive_codes,
        "本期间正式分录使用的科目均有效。",
        "本期间存在已停用或不存在的科目。",
        {"inactive_count": len(inactive_codes)},
    )


def _currency_rates_ready_check(account_set_id: str, period: str, entries, get_exchange_rate) -> PeriodCloseCheckItem:
    period_end = _period_end_date(period)
    missing_pairs: set[str] = set()
    for entry in entries:
        for line in entry.lines:
            if line.currency == entry.base_currency:
                continue
            try:
                get_exchange_rate(account_set_id, period_end, line.currency, entry.base_currency)
            except HTTPException as exc:
                if exc.status_code == 404:
                    missing_pairs.add(f"{line.currency}->{entry.base_currency}")
                else:
                    raise
    return _check_item(
        "currency_rates_ready",
        "期末汇率准备",
        not missing_pairs,
        "涉及外币余额的币种均已准备期末汇率。",
        "存在缺少期末汇率的外币币种。",
        {"missing_rate_count": len(missing_pairs)},
    )


def _check_item(
    check_code: str,
    check_name: str,
    passed: bool,
    passed_message: str,
    failed_message: str,
    evidence: dict[str, str | int | Decimal] | None = None,
) -> PeriodCloseCheckItem:
    return PeriodCloseCheckItem(
        check_code=check_code,
        check_name=check_name,
        status="passed" if passed else "failed",
        severity="blocker",
        message=passed_message if passed else failed_message,
        evidence=evidence or {},
    )


def _period_end_date(period: str) -> str:
    year, month = (int(part) for part in period.split("-"))
    return f"{period}-{monthrange(year, month)[1]:02d}"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
