from __future__ import annotations

import hashlib
from calendar import monthrange
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from fastapi import HTTPException

from app.models.period_close import (
    PeriodCloseActionResult,
    PeriodCloseCheckItem,
    PeriodCloseRun,
    PeriodCloseRunCreate,
    PeriodCloseRunListResponse,
    TaxAccrualRule,
)
from app.services.accounting_period_service import validate_account_set


_PERIOD_CLOSE_RUNS: dict[str, PeriodCloseRun] = {}
_TAX_ACCRUAL_RULES: list[TaxAccrualRule] = []
MONEY_QUANT = Decimal("0.01")


def reset_period_close_store() -> None:
    _PERIOD_CLOSE_RUNS.clear()
    _TAX_ACCRUAL_RULES.clear()


def set_tax_accrual_rules(rules: list[TaxAccrualRule]) -> None:
    for rule in rules:
        validate_account_set(rule.account_set_id)
    _TAX_ACCRUAL_RULES.clear()
    _TAX_ACCRUAL_RULES.extend(rules)


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
            check_code="inventory_cost_ready",
            check_name="存货成本结转准备",
            status="passed",
            severity="warning",
            message="销售出库成本分录将在存货成本结转动作中汇总校验。",
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


def generate_period_close_actions(
    account_set_id: str,
    period: str,
    actions: list[str],
    generated_by: str,
    force_regenerate: bool = False,
) -> list[PeriodCloseActionResult]:
    validate_account_set(account_set_id)
    if force_regenerate:
        from app.services.accounting_period_service import is_accounting_period_closed

        if is_accounting_period_closed(period, account_set_id):
            raise HTTPException(status_code=409, detail="期间已关闭，不能重新生成期末分录。")

    results = []
    for action in actions:
        if action == "fixed_asset_depreciation":
            results.append(_generate_fixed_asset_depreciation(account_set_id, period, generated_by))
        elif action == "payroll_accrual":
            results.append(_generate_payroll_accrual(account_set_id, period, generated_by))
        elif action == "tax_accrual":
            results.append(_generate_tax_accrual(account_set_id, period, generated_by))
        elif action == "tax_surtax_accrual":
            results.append(_generate_tax_surtax_accrual(account_set_id, period, generated_by))
        elif action == "accrual_amortization_posting":
            results.append(_generate_accrual_amortization_posting(account_set_id, period, generated_by))
        elif action == "fx_revaluation":
            results.append(_generate_fx_revaluation(account_set_id, period, generated_by))
        elif action == "profit_loss_carryforward":
            results.append(_generate_profit_loss_carryforward(account_set_id, period, generated_by))
        elif action == "year_end_profit_distribution":
            results.append(_generate_year_end_profit_distribution(account_set_id, period, generated_by))
        elif action == "bad_debt_provision":
            results.append(_generate_bad_debt_provision(account_set_id, period, generated_by))
        elif action == "inventory_cost_rollforward":
            results.append(_generate_inventory_cost_rollforward(account_set_id, period, generated_by))
        else:
            raise HTTPException(status_code=422, detail=f"不支持的期末动作：{action}")
    return results


def _generate_fixed_asset_depreciation(
    account_set_id: str,
    period: str,
    generated_by: str,
) -> PeriodCloseActionResult:
    source_type = "fixed_asset_depreciation"
    from app.services.fixed_asset_accounting_service import post_fixed_asset_depreciation

    result = post_fixed_asset_depreciation(account_set_id, period, generated_by)
    return _action_result(
        source_type,
        result.status,
        result.entries,
        result.total_depreciation,
        "已按固定资产卡片生成正式折旧分录。",
    )


def _generate_payroll_accrual(account_set_id: str, period: str, generated_by: str) -> PeriodCloseActionResult:
    source_type = "payroll_accrual"
    payroll_batch_id = f"PAY-{period}"
    source_id = f"{source_type}:{account_set_id}:{period}:{payroll_batch_id}"
    existing = _existing_entries(account_set_id, period, source_type, source_id)
    if existing:
        return _action_result(source_type, "existing", existing, _entry_amount(existing), "工资计提分录已存在。")

    from app.services.payroll_accounting_service import accrue_payroll_batch
    from app.services.payroll_service import get_payroll_calculation

    if get_payroll_calculation(account_set_id, period) is None:
        return _action_result(source_type, "skipped", [], Decimal("0.00"), "本期间没有可计提的工资摘要。")

    entry = accrue_payroll_batch(account_set_id, period, payroll_batch_id, generated_by)
    amount = _entry_amount([entry])
    return _action_result(source_type, "generated", [entry], amount, "已生成工资薪酬计提分录。")


def _generate_tax_accrual(account_set_id: str, period: str, generated_by: str) -> PeriodCloseActionResult:
    source_type = "tax_accrual"
    rules = [rule for rule in _TAX_ACCRUAL_RULES if rule.account_set_id == account_set_id]
    if not rules:
        return _action_result(source_type, "skipped", [], Decimal("0.00"), "未配置税费计提规则。")

    from app.services.accounting_service import list_journal_entries

    entries = list_journal_entries(account_set_id, period).entries
    generated_entries = []
    existing_entries = []
    total_amount = Decimal("0.00")
    for rule in rules:
        source_id = f"{source_type}:{account_set_id}:{period}:{rule.tax_code}"
        existing = _existing_entries(account_set_id, period, source_type, source_id)
        if existing:
            existing_entries.extend(existing)
            total_amount += _entry_amount(existing)
            continue
        tax_base = _tax_base_amount(entries, set(rule.base_account_codes))
        amount = _money(tax_base * rule.rate)
        if amount <= Decimal("0.00"):
            continue
        entry = _post_grouped_entry(
            account_set_id=account_set_id,
            period=period,
            source_type=source_type,
            source_id=source_id,
            description=f"{period} {rule.tax_name}计提",
            generated_by=generated_by,
            debit_rows=[(rule.debit_account_code, amount, rule.tax_name)],
            credit_rows=[(rule.credit_account_code, amount, rule.tax_name)],
        )
        generated_entries.append(entry)
        total_amount += amount

    if generated_entries:
        return _action_result(source_type, "generated", generated_entries, _money(total_amount), "已生成税费计提分录。")
    if existing_entries:
        return _action_result(source_type, "existing", existing_entries, _money(total_amount), "税费计提分录已存在。")
    return _action_result(source_type, "skipped", [], Decimal("0.00"), "税费计提规则未计算出应计提金额。")


def _generate_tax_surtax_accrual(account_set_id: str, period: str, generated_by: str) -> PeriodCloseActionResult:
    source_type = "tax_surtax_accrual"
    existing = _existing_entries(account_set_id, period, source_type)
    if existing:
        return _action_result(source_type, "existing", existing, _entry_amount(existing), "附加税计提分录已存在。")

    from app.services.accounting_service import list_journal_entries
    from app.services.tax_accounting_service import calculate_surtax, post_surtax_accrual

    unpaid_vat_entries = [
        entry
        for entry in list_journal_entries(account_set_id, period).entries
        if entry.status == "posted" and entry.source_type == "tax_unpaid_vat_transfer"
    ]
    vat_payable = _money(
        sum(
            (
                line.base_amount
                for entry in unpaid_vat_entries
                for line in entry.lines
                if line.account_code == "222102" and line.direction == "credit"
            ),
            Decimal("0.00"),
        )
    )
    if vat_payable <= Decimal("0.00"):
        return _action_result(source_type, "skipped", [], Decimal("0.00"), "本期间没有可计提附加税的未交增值税。")

    result = calculate_surtax(
        vat_payable=vat_payable,
        urban_maintenance_rate=Decimal("0.07"),
        education_rate=Decimal("0.03"),
        local_education_rate=Decimal("0.02"),
    )
    entry = post_surtax_accrual(account_set_id, period, result, generated_by)
    return _action_result(source_type, "generated", [entry], result.total, "已生成附加税计提分录。")


def _generate_accrual_amortization_posting(account_set_id: str, period: str, generated_by: str) -> PeriodCloseActionResult:
    action_type = "accrual_amortization_posting"
    from app.services.accrual_amortization_service import (
        get_schedule_amount_for_period,
        list_accounting_schedules,
        post_schedule_for_period,
    )

    generated_entries = []
    existing_entries = []
    total_amount = Decimal("0.00")
    for schedule in list_accounting_schedules(account_set_id):
        if schedule.status != "active" or not (schedule.start_period <= period <= schedule.end_period):
            continue
        source_id = f"schedule_posting:{account_set_id}:{period}:{schedule.schedule_code}"
        existing = _existing_entries(account_set_id, period, schedule.schedule_type, source_id)
        amount = get_schedule_amount_for_period(schedule, period)
        if existing:
            existing_entries.extend(existing)
            total_amount += amount
            continue
        entry = post_schedule_for_period(account_set_id, schedule.schedule_code, period, generated_by)
        generated_entries.append(entry)
        total_amount += amount

    if generated_entries:
        return _action_result(action_type, "generated", generated_entries, _money(total_amount), "已按核算计划生成本期预提摊销分录。")
    if existing_entries:
        return _action_result(action_type, "existing", existing_entries, _money(total_amount), "本期预提摊销分录已存在。")
    return _action_result(action_type, "skipped", [], Decimal("0.00"), "本期间没有可生成的预提摊销计划。")


def _generate_fx_revaluation(account_set_id: str, period: str, generated_by: str) -> PeriodCloseActionResult:
    source_type = "fx_revaluation"
    from app.services.accounting_service import get_exchange_rate, get_foreign_currency_balances

    balances = get_foreign_currency_balances(account_set_id, period)
    generated_entries = []
    existing_entries = []
    total_amount = Decimal("0.00")
    period_end = _period_end_date(period)

    for balance in balances:
        rate = get_exchange_rate(account_set_id, period_end, balance["currency"], "CNY")
        expected_base_balance = _money(balance["original_balance"] * rate.rate)
        adjustment = _money(expected_base_balance - balance["book_base_balance"])
        source_id = _fx_source_id(account_set_id, period, balance)
        existing = _existing_entries(account_set_id, period, source_type, source_id)
        if existing:
            existing_entries.extend(existing)
            total_amount += _entry_amount(existing)
            continue
        if adjustment == Decimal("0.00"):
            continue
        entry = _post_fx_revaluation_entry(
            account_set_id=account_set_id,
            period=period,
            source_id=source_id,
            balance=balance,
            adjustment=adjustment,
            generated_by=generated_by,
        )
        generated_entries.append(entry)
        total_amount += abs(adjustment)

    if generated_entries:
        return _action_result(source_type, "generated", generated_entries, _money(total_amount), "已生成外币期末重估分录。")
    if existing_entries:
        return _action_result(source_type, "existing", existing_entries, _money(total_amount), "外币期末重估分录已存在。")
    return _action_result(source_type, "skipped", [], Decimal("0.00"), "本期间没有需要重估的外币余额。")


def _generate_profit_loss_carryforward(account_set_id: str, period: str, generated_by: str) -> PeriodCloseActionResult:
    source_type = "profit_loss_carryforward"
    source_id = f"{source_type}:{account_set_id}:{period}"
    existing = _existing_entries(account_set_id, period, source_type, source_id)
    if existing:
        return _action_result(source_type, "existing", existing, _entry_amount(existing), "损益结转分录已存在。")

    from app.services.accounting_service import get_profit_loss_balances

    balances = get_profit_loss_balances(account_set_id, period)
    debit_rows: list[tuple[str, Decimal, str]] = []
    credit_rows: list[tuple[str, Decimal, str]] = []
    for balance in balances:
        amount = _money(abs(balance["balance"]))
        if amount <= Decimal("0.00"):
            continue
        if balance["account_type"] == "revenue":
            if balance["balance"] > Decimal("0.00"):
                debit_rows.append((balance["account_code"], amount, "收入结转"))
                credit_rows.append(("4103", amount, "收入结转至本年利润"))
            else:
                debit_rows.append(("4103", amount, "收入反向结转"))
                credit_rows.append((balance["account_code"], amount, "收入反向结转"))
        else:
            if balance["balance"] > Decimal("0.00"):
                debit_rows.append(("4103", amount, "成本费用结转至本年利润"))
                credit_rows.append((balance["account_code"], amount, "成本费用结转"))
            else:
                debit_rows.append((balance["account_code"], amount, "成本费用反向结转"))
                credit_rows.append(("4103", amount, "成本费用反向结转"))

    amount = _money(sum((row[1] for row in debit_rows), Decimal("0.00")))
    if amount <= Decimal("0.00"):
        return _action_result(source_type, "skipped", [], amount, "本期间没有需要结转的损益余额。")
    entry = _post_grouped_entry(
        account_set_id=account_set_id,
        period=period,
        source_type=source_type,
        source_id=source_id,
        description=f"{period} 损益结转",
        generated_by=generated_by,
        debit_rows=debit_rows,
        credit_rows=credit_rows,
    )
    return _action_result(source_type, "generated", [entry], amount, "已生成损益结转分录。")


def _generate_year_end_profit_distribution(account_set_id: str, period: str, generated_by: str) -> PeriodCloseActionResult:
    source_type = "year_end_profit_distribution"
    source_id = f"{source_type}:{account_set_id}:{period}"
    existing = _existing_entries(account_set_id, period, source_type, source_id)
    if existing:
        return _action_result(source_type, "existing", existing, _entry_amount(existing), "年终利润分配分录已存在。")

    balance = _current_year_profit_balance(account_set_id, period)
    amount = _money(abs(balance))
    if amount <= Decimal("0.00"):
        return _action_result(source_type, "skipped", [], amount, "本年利润余额为零，无需年终分配。")
    if balance > Decimal("0.00"):
        debit_rows = [("4103", amount, "本年利润转出")]
        credit_rows = [("4104", amount, "转入未分配利润")]
    else:
        debit_rows = [("4104", amount, "未分配利润弥补亏损")]
        credit_rows = [("4103", amount, "本年亏损转出")]
    entry = _post_grouped_entry(
        account_set_id=account_set_id,
        period=period,
        source_type=source_type,
        source_id=source_id,
        description=f"{period} 年终利润分配",
        generated_by=generated_by,
        debit_rows=debit_rows,
        credit_rows=credit_rows,
    )
    return _action_result(source_type, "generated", [entry], amount, "已生成年终利润分配分录。")


def _generate_bad_debt_provision(account_set_id: str, period: str, generated_by: str) -> PeriodCloseActionResult:
    source_type = "bad_debt_provision"
    source_id = f"{source_type}:{account_set_id}:{period}"
    existing = _existing_entries(account_set_id, period, source_type, source_id)
    if existing:
        return _action_result(source_type, "existing", existing, _entry_amount(existing), "坏账准备分录已存在。")

    from app.models.receivable_payable import BadDebtProvisionRule
    from app.services.receivable_payable_service import calculate_bad_debt_provision

    provision = calculate_bad_debt_provision(
        account_set_id=account_set_id,
        period=period,
        as_of_date=_period_end_date(period),
        rule=BadDebtProvisionRule(
            bucket_rates={
                "91-180": Decimal("0.05"),
                "181-365": Decimal("0.10"),
                "365+": Decimal("0.50"),
            }
        ),
    )
    amount = _money(provision.required_provision_amount)
    if amount <= Decimal("0.00"):
        return _action_result(source_type, "skipped", [], amount, "本期无需计提坏账准备。")
    entry = _post_grouped_entry(
        account_set_id=account_set_id,
        period=period,
        source_type=source_type,
        source_id=source_id,
        description=f"{period} 坏账准备计提",
        generated_by=generated_by,
        debit_rows=[(provision.debit_account_code, amount, provision.debit_account_name)],
        credit_rows=[(provision.credit_account_code, amount, provision.credit_account_name)],
    )
    return _action_result(source_type, "generated", [entry], amount, "已生成坏账准备分录。")


def _generate_inventory_cost_rollforward(
    account_set_id: str,
    period: str,
    generated_by: str,
) -> PeriodCloseActionResult:
    source_type = "inventory_cost_rollforward"
    from app.services.accounting_service import list_journal_entries

    entries = [
        entry
        for entry in list_journal_entries(account_set_id, period).entries
        if entry.status == "posted" and entry.source_type == "inventory_sales_issue"
    ]
    if not entries:
        return _action_result(source_type, "skipped", [], Decimal("0.00"), "本期间没有已生成的销售出库成本分录。")
    return _action_result(
        source_type,
        "existing",
        entries,
        _entry_amount(entries),
        f"{generated_by} 已确认本期销售出库成本分录。",
    )


def _post_grouped_entry(
    *,
    account_set_id: str,
    period: str,
    source_type: str,
    source_id: str,
    description: str,
    generated_by: str,
    debit_rows: list[tuple[str, Decimal, str]],
    credit_rows: list[tuple[str, Decimal, str]],
):
    from app.models.accounting import JournalEntryCreate, JournalLineCreate
    from app.services.accounting_service import get_chart_of_accounts, post_journal_entry

    account_names = {account.account_code: account.account_name for account in get_chart_of_accounts(account_set_id).accounts}
    lines = [
        JournalLineCreate(
            account_code=account_code,
            account_name=account_names.get(account_code, account_code),
            direction=direction,
            original_amount=amount,
            exchange_rate=Decimal("1.000000"),
            base_amount=amount,
            description=line_description,
        )
        for direction, rows in (("debit", _collapse_rows(debit_rows)), ("credit", _collapse_rows(credit_rows)))
        for account_code, amount, line_description in rows
    ]
    return post_journal_entry(
        JournalEntryCreate(
            account_set_id=account_set_id,
            entry_date=_period_end_date(period),
            source_type=source_type,
            source_id=source_id,
            description=description,
            base_currency="CNY",
            created_by=generated_by,
            posted_by=generated_by,
            lines=lines,
        )
    )


def _post_fx_revaluation_entry(
    *,
    account_set_id: str,
    period: str,
    source_id: str,
    balance: dict,
    adjustment: Decimal,
    generated_by: str,
):
    from app.models.accounting import JournalEntryCreate, JournalLineCreate, JournalLineDimension
    from app.services.accounting_service import get_chart_of_accounts, post_journal_entry

    amount = _money(abs(adjustment))
    account_code = balance["account_code"]
    fx_gain_loss_code = "6603"
    if balance["account_type"] == "asset":
        account_direction = "debit" if adjustment > Decimal("0.00") else "credit"
    else:
        account_direction = "credit" if adjustment > Decimal("0.00") else "debit"
    fx_direction = "credit" if account_direction == "debit" else "debit"
    account_names = {account.account_code: account.account_name for account in get_chart_of_accounts(account_set_id).accounts}
    dimensions = [
        JournalLineDimension(
            dimension_type=dimension["dimension_type"],
            dimension_code=dimension["dimension_code"],
        )
        for dimension in balance["dimension_values"]
    ]
    return post_journal_entry(
        JournalEntryCreate(
            account_set_id=account_set_id,
            entry_date=_period_end_date(period),
            source_type="fx_revaluation",
            source_id=source_id,
            description=f"{period} {balance['currency']} 期末汇兑重估",
            base_currency="CNY",
            created_by=generated_by,
            posted_by=generated_by,
            lines=[
                JournalLineCreate(
                    account_code=account_code,
                    account_name=account_names.get(account_code, balance["account_name"]),
                    direction=account_direction,
                    currency="CNY",
                    original_amount=amount,
                    exchange_rate=Decimal("1.000000"),
                    base_amount=amount,
                    description="外币期末重估",
                    dimensions=dimensions,
                ),
                JournalLineCreate(
                    account_code=fx_gain_loss_code,
                    account_name=account_names.get(fx_gain_loss_code, "财务费用"),
                    direction=fx_direction,
                    currency="CNY",
                    original_amount=amount,
                    exchange_rate=Decimal("1.000000"),
                    base_amount=amount,
                    description="汇兑损益",
                ),
            ],
        )
    )


def _fx_source_id(account_set_id: str, period: str, balance: dict) -> str:
    dimension_hash = hashlib.sha1(str(balance["dimension_values"]).encode("utf-8")).hexdigest()[:10]
    return f"fx_revaluation:{account_set_id}:{period}:{balance['account_code']}:{balance['currency']}:{dimension_hash}"


def _collapse_rows(rows: list[tuple[str, Decimal, str]]) -> list[tuple[str, Decimal, str]]:
    grouped: dict[str, Decimal] = {}
    for account_code, amount, _description in rows:
        grouped[account_code] = grouped.get(account_code, Decimal("0.00")) + amount
    return [
        (account_code, _money(amount), "期末结账")
        for account_code, amount in sorted(grouped.items())
        if _money(amount) > Decimal("0.00")
    ]


def _existing_entries(account_set_id: str, period: str, source_type: str, source_id: str | None = None):
    from app.services.accounting_service import list_journal_entries

    return [
        entry
        for entry in list_journal_entries(account_set_id, period).entries
        if entry.status == "posted"
        and entry.source_type == source_type
        and (source_id is None or entry.source_id == source_id)
    ]


def _entry_amount(entries) -> Decimal:
    return _money(
        sum(
            (
                line.base_amount
                for entry in entries
                for line in entry.lines
                if line.direction == "debit"
            ),
            Decimal("0.00"),
        )
    )


def _tax_base_amount(entries, account_codes: set[str]) -> Decimal:
    amount = Decimal("0.00")
    for entry in entries:
        if entry.status != "posted":
            continue
        for line in entry.lines:
            if line.account_code not in account_codes:
                continue
            if line.direction == "credit":
                amount += line.base_amount
            else:
                amount -= line.base_amount
    return max(Decimal("0.00"), _money(amount))


def _current_year_profit_balance(account_set_id: str, period: str) -> Decimal:
    from app.services.accounting_service import list_journal_entries

    year = period[:4]
    balance = Decimal("0.00")
    for entry in list_journal_entries(account_set_id).entries:
        if entry.status != "posted" or not entry.period.startswith(year) or entry.period > period:
            continue
        for line in entry.lines:
            if line.account_code != "4103":
                continue
            if line.direction == "credit":
                balance += line.base_amount
            else:
                balance -= line.base_amount
    return _money(balance)


def _action_result(
    action_type: str,
    status: str,
    entries,
    amount: Decimal,
    message: str,
) -> PeriodCloseActionResult:
    return PeriodCloseActionResult(
        action_type=action_type,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        journal_entry_ids=[entry.id for entry in entries],
        amount=_money(amount),
        message=message,
    )


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


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
