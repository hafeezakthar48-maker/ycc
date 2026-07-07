from decimal import Decimal

from fastapi import HTTPException

from app.models.consolidation import (
    ConsolidatedStatementResponse,
    ConsolidationEliminationEntry,
    ConsolidationEliminationListResponse,
    ConsolidationEliminationRebuildRequest,
    ConsolidationGroup,
    ConsolidationGroupCreate,
    ConsolidationGroupListResponse,
    ConsolidationReportingPackage,
)
from app.models.financial_statement import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatementGenerateRequest,
    IncomeStatement,
    StatementLineItem,
)
from app.services.financial_statement_service import generate_financial_statements


MONEY_QUANT = Decimal("0.01")
ZERO = Decimal("0.00")
_GROUPS: dict[str, ConsolidationGroup] = {}
_ELIMINATIONS: dict[tuple[str, str], list[ConsolidationEliminationEntry]] = {}
_MINORITY_METRICS: dict[tuple[str, str], tuple[Decimal, Decimal]] = {}


def reset_consolidation_store() -> None:
    _GROUPS.clear()
    _ELIMINATIONS.clear()
    _MINORITY_METRICS.clear()


def create_consolidation_group(payload: ConsolidationGroupCreate) -> ConsolidationGroup:
    for entity in payload.entities:
        if entity.consolidation_group_id != payload.group_id:
            raise HTTPException(status_code=422, detail="合并实体所属集团必须与合并集团一致。")
    group = ConsolidationGroup(**payload.model_dump())
    _GROUPS[group.group_id] = group
    return group


def get_consolidation_group(group_id: str) -> ConsolidationGroup:
    group = _GROUPS.get(group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="合并集团不存在。")
    return group


def list_consolidation_groups() -> ConsolidationGroupListResponse:
    groups = sorted(_GROUPS.values(), key=lambda item: item.group_id)
    return ConsolidationGroupListResponse(total_groups=len(groups), groups=groups)


def build_reporting_package(account_set_id: str, period: str) -> ConsolidationReportingPackage:
    bundle = generate_financial_statements(
        FinancialStatementGenerateRequest(account_set_id=account_set_id, period=period, include_trace=True)
    )
    return ConsolidationReportingPackage(
        account_set_id=account_set_id,
        period=period,
        balance_sheet=bundle.balance_sheet,
        income_statement=bundle.income_statement,
        cash_flow_statement=bundle.cash_flow_statement,
    )


def list_consolidation_eliminations(group_id: str, period: str) -> ConsolidationEliminationListResponse:
    get_consolidation_group(group_id)
    eliminations = _ELIMINATIONS.get((group_id, period), [])
    return ConsolidationEliminationListResponse(
        group_id=group_id,
        period=period,
        total_eliminations=len(eliminations),
        eliminations=eliminations,
    )


def rebuild_consolidation_eliminations(
    request: ConsolidationEliminationRebuildRequest,
) -> ConsolidationEliminationListResponse:
    get_consolidation_group(request.group_id)
    eliminations: list[ConsolidationEliminationEntry] = []
    if request.intercompany_balance_amount > ZERO:
        eliminations.append(
            build_intercompany_balance_elimination(
                group_id=request.group_id,
                period=request.period,
                receivable_account_code="1122",
                payable_account_code="2202",
                amount=request.intercompany_balance_amount,
            )
        )
    if request.intercompany_revenue_amount > ZERO and request.intercompany_cost_amount > ZERO:
        eliminations.extend(
            build_intercompany_revenue_cost_elimination(
                group_id=request.group_id,
                period=request.period,
                revenue_amount=request.intercompany_revenue_amount,
                cost_amount=request.intercompany_cost_amount,
            )
        )
    unrealized_profit = calculate_unrealized_inventory_profit(
        request.ending_internal_inventory_amount,
        request.internal_gross_margin_rate,
    )
    if unrealized_profit > ZERO:
        eliminations.append(
            ConsolidationEliminationEntry(
                elimination_id=f"elim-{request.group_id}-{request.period}-unrealized-profit",
                group_id=request.group_id,
                period=request.period,
                elimination_type="unrealized_profit",
                debit_account_code="6401",
                credit_account_code="1405",
                amount=unrealized_profit,
                explanation="抵销期末存货未实现内部利润",
            )
        )
    if request.investment_amount > ZERO and request.subsidiary_equity_amount > ZERO:
        eliminations.extend(
            build_investment_equity_elimination(
                group_id=request.group_id,
                period=request.period,
                investment_account_code="1511",
                subsidiary_equity_account_code="4001",
                investment_amount=request.investment_amount,
                subsidiary_equity_amount=request.subsidiary_equity_amount,
                ownership_percentage=request.ownership_percentage,
            )
        )
    minority_interest = (
        calculate_minority_interest(request.subsidiary_equity_amount, request.ownership_percentage)
        if request.subsidiary_equity_amount > ZERO
        else ZERO
    )
    _ELIMINATIONS[(request.group_id, request.period)] = eliminations
    _MINORITY_METRICS[(request.group_id, request.period)] = (
        minority_interest,
        calculate_minority_interest(request.intercompany_revenue_amount - request.intercompany_cost_amount, request.ownership_percentage)
        if request.intercompany_revenue_amount > request.intercompany_cost_amount
        else ZERO,
    )
    return list_consolidation_eliminations(request.group_id, request.period)


def build_intercompany_balance_elimination(
    group_id: str,
    period: str,
    receivable_account_code: str,
    payable_account_code: str,
    amount: Decimal,
) -> ConsolidationEliminationEntry:
    return ConsolidationEliminationEntry(
        elimination_id=f"elim-{group_id}-{period}-balance",
        group_id=group_id,
        period=period,
        elimination_type="intercompany_balance",
        debit_account_code=payable_account_code,
        credit_account_code=receivable_account_code,
        amount=amount.quantize(Decimal("0.01")),
        explanation="抵销内部应收应付",
    )


def calculate_unrealized_inventory_profit(
    ending_internal_inventory_amount: Decimal,
    internal_gross_margin_rate: Decimal,
) -> Decimal:
    return (ending_internal_inventory_amount * internal_gross_margin_rate).quantize(Decimal("0.01"))


def build_intercompany_revenue_cost_elimination(
    group_id: str,
    period: str,
    revenue_amount: Decimal,
    cost_amount: Decimal,
) -> list[ConsolidationEliminationEntry]:
    elimination_amount = min(revenue_amount, cost_amount).quantize(Decimal("0.01"))
    return [
        ConsolidationEliminationEntry(
            elimination_id=f"elim-{group_id}-{period}-revenue-cost",
            group_id=group_id,
            period=period,
            elimination_type="intercompany_revenue_cost",
            debit_account_code="6001",
            credit_account_code="6401",
            amount=elimination_amount,
            explanation="抵销内部销售收入与成本",
        )
    ]


def calculate_minority_interest(
    subsidiary_net_assets: Decimal,
    ownership_percentage: Decimal,
) -> Decimal:
    minority_percentage = Decimal("1") - ownership_percentage
    return (subsidiary_net_assets * minority_percentage).quantize(Decimal("0.01"))


def build_investment_equity_elimination(
    group_id: str,
    period: str,
    investment_account_code: str,
    subsidiary_equity_account_code: str,
    investment_amount: Decimal,
    subsidiary_equity_amount: Decimal,
    ownership_percentage: Decimal,
) -> list[ConsolidationEliminationEntry]:
    attributable_equity = (subsidiary_equity_amount * ownership_percentage).quantize(Decimal("0.01"))
    elimination_amount = min(investment_amount, attributable_equity).quantize(Decimal("0.01"))
    return [
        ConsolidationEliminationEntry(
            elimination_id=f"elim-{group_id}-{period}-investment-equity",
            group_id=group_id,
            period=period,
            elimination_type="investment_equity",
            debit_account_code=subsidiary_equity_account_code,
            credit_account_code=investment_account_code,
            amount=elimination_amount,
            explanation="抵销母公司长期股权投资与子公司权益",
        )
    ]


def build_consolidated_statements(group_id: str, period: str) -> ConsolidatedStatementResponse:
    group = get_consolidation_group(group_id)
    weighted_packages = [
        (build_reporting_package(entity.account_set_id, period), _entity_weight(entity.consolidation_method, entity.ownership_percentage))
        for entity in group.entities
    ]
    if not weighted_packages:
        raise HTTPException(status_code=422, detail="合并集团至少需要一个纳入范围的账套。")

    balance_sheet = _combine_balance_sheets(period, [(package.balance_sheet, weight) for package, weight in weighted_packages])
    income_statement = _combine_income_statements(period, [(package.income_statement, weight) for package, weight in weighted_packages])
    cash_flow_statement = _combine_cash_flow_statements(period, [(package.cash_flow_statement, weight) for package, weight in weighted_packages])
    minority_interest, minority_profit = _MINORITY_METRICS.get((group_id, period), (ZERO, ZERO))
    return ConsolidatedStatementResponse(
        group_id=group_id,
        period=period,
        balance_sheet=balance_sheet,
        income_statement=income_statement,
        cash_flow_statement=cash_flow_statement,
        minority_interest=minority_interest,
        minority_profit=minority_profit,
        elimination_count=len(_ELIMINATIONS.get((group_id, period), [])),
    )


def _entity_weight(consolidation_method: str, ownership_percentage: Decimal) -> Decimal:
    if consolidation_method == "proportionate":
        return ownership_percentage
    if consolidation_method == "equity_method":
        return ownership_percentage
    return Decimal("1")


def _combine_balance_sheets(period: str, statements: list[tuple[BalanceSheet, Decimal]]) -> BalanceSheet:
    total_assets = _weighted_sum([(statement.total_assets, weight) for statement, weight in statements])
    total_liabilities = _weighted_sum([(statement.total_liabilities, weight) for statement, weight in statements])
    total_equity = _weighted_sum([(statement.total_equity, weight) for statement, weight in statements])
    total_liabilities_and_equity = total_liabilities + total_equity
    return BalanceSheet(
        title="合并资产负债表",
        period=period,
        items=_combine_items([(statement.items, weight) for statement, weight in statements]),
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=total_equity,
        total_liabilities_and_equity=total_liabilities_and_equity,
        balanced=total_assets == total_liabilities_and_equity,
    )


def _combine_income_statements(period: str, statements: list[tuple[IncomeStatement, Decimal]]) -> IncomeStatement:
    total_revenue = _weighted_sum([(statement.total_revenue, weight) for statement, weight in statements])
    total_cost = _weighted_sum([(statement.total_cost, weight) for statement, weight in statements])
    total_expense = _weighted_sum([(statement.total_expense, weight) for statement, weight in statements])
    total_profit = _weighted_sum([(statement.total_profit, weight) for statement, weight in statements])
    net_profit = _weighted_sum([(statement.net_profit, weight) for statement, weight in statements])
    return IncomeStatement(
        title="合并利润表",
        period=period,
        items=_combine_items([(statement.items, weight) for statement, weight in statements]),
        total_revenue=total_revenue,
        total_cost=total_cost,
        total_expense=total_expense,
        total_profit=total_profit,
        net_profit=net_profit,
    )


def _combine_cash_flow_statements(period: str, statements: list[tuple[CashFlowStatement, Decimal]]) -> CashFlowStatement:
    operating = _weighted_sum([(statement.operating_cash_flow_net, weight) for statement, weight in statements])
    investing = _weighted_sum([(statement.investing_cash_flow_net, weight) for statement, weight in statements])
    financing = _weighted_sum([(statement.financing_cash_flow_net, weight) for statement, weight in statements])
    return CashFlowStatement(
        title="合并现金流量表",
        period=period,
        items=_combine_items([(statement.items, weight) for statement, weight in statements]),
        operating_cash_flow_net=operating,
        investing_cash_flow_net=investing,
        financing_cash_flow_net=financing,
        net_cash_flow=operating + investing + financing,
    )


def _combine_items(statement_items: list[tuple[list[StatementLineItem], Decimal]]) -> list[StatementLineItem]:
    totals: dict[tuple[str, str, str], Decimal] = {}
    for items, weight in statement_items:
        for item in items:
            key = (item.code, item.name, item.formula)
            totals[key] = totals.get(key, ZERO) + (item.amount * weight)
    return [
        StatementLineItem(code=code, name=name, amount=amount.quantize(MONEY_QUANT), formula=f"合并汇总：{formula}")
        for (code, name, formula), amount in sorted(totals.items(), key=lambda pair: pair[0][0])
    ]


def _weighted_sum(amounts: list[tuple[Decimal, Decimal]]) -> Decimal:
    return sum((amount * weight for amount, weight in amounts), ZERO).quantize(MONEY_QUANT)
