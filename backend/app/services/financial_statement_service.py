from decimal import Decimal, ROUND_HALF_UP

from app.data.sample_finance_data import SAMPLE_FINANCE_DATA
from app.models.finance import MonthlyFinanceRecord
from app.models.financial_statement import (
    BalanceSheet,
    CashFlowStatement,
    EquityStatement,
    FinancialStatementBundle,
    FinancialStatementGenerateRequest,
    FinancialStatementGenerationSummary,
    IncomeStatement,
    ManagementStatementSummary,
    StatementLineItem,
)
from app.models.ledger import LedgerAccountSummary
from app.models.statement_mapping import StatementLineTrace, StatementValidationItem
from app.services.analysis_service import COMPANY_NAME
from app.services.accounting_service import list_journal_entries, list_period_journal_lines_for_reporting
from app.services.ledger_service import build_general_ledger
from app.services.statement_mapping_service import (
    calculate_statement_lines,
    get_default_statement_mapping_set,
    infer_cash_flow_amounts,
)


TWOPLACES = Decimal("0.01")
ZERO = Decimal("0.00")


def generate_financial_statements(
    request: FinancialStatementGenerateRequest,
) -> FinancialStatementBundle:
    mapping_set_id = _mapping_set_id(request)
    ledger = build_general_ledger(request.period, request.account_set_id)
    if ledger.accounts:
        source = "formal_journal_entries" if ledger.source == "formal_journal_entries" else "reviewed_vouchers"
        return _bundle_from_mapped_ledger(request, mapping_set_id, ledger.voucher_count, ledger.accounts, source)
    return _bundle_from_sample(request, mapping_set_id)


def _mapping_set_id(request: FinancialStatementGenerateRequest) -> str:
    if request.mapping_set_id:
        return request.mapping_set_id
    return get_default_statement_mapping_set(request.account_set_id).mapping_set_id


def _bundle_from_sample(request: FinancialStatementGenerateRequest, mapping_set_id: str) -> FinancialStatementBundle:
    current = _find_record(request.period)
    previous = _previous_record(request.period)

    cash = _money(current.cash)
    accounts_receivable = _money(current.accounts_receivable)
    inventory = _money(current.inventory)
    fixed_assets = _money(current.fixed_assets)
    total_assets = _money(current.total_assets)
    short_term_loans = _money(current.short_term_loans)
    accounts_payable = _money(current.accounts_payable)
    total_liabilities = _money(current.total_liabilities)
    total_equity = _money(current.owner_equity)
    total_liabilities_and_equity = total_liabilities + total_equity
    net_profit = _money(current.net_profit)
    opening_equity = _money(previous.owner_equity if previous else current.owner_equity - current.net_profit)
    equity_adjustment = total_equity - opening_equity - net_profit

    income_statement = IncomeStatement(
        title="利润表",
        period=request.period,
        items=[
            _line("IS-REVENUE", "营业收入", current.revenue, "样例经营数据：revenue"),
            _line("IS-COST", "营业成本", current.cost, "样例经营数据：cost"),
            _line("IS-SALES-EXPENSE", "销售费用", current.sales_expense, "样例经营数据：sales_expense"),
            _line("IS-ADMIN-EXPENSE", "管理费用", current.admin_expense, "样例经营数据：admin_expense"),
            _line("IS-RD-EXPENSE", "研发费用", current.rd_expense, "样例经营数据：rd_expense"),
            _line("IS-FINANCE-EXPENSE", "财务费用", current.finance_expense, "样例经营数据：finance_expense"),
            _line("IS-TOTAL-PROFIT", "利润总额", current.total_profit, "样例经营数据：total_profit"),
            _line("IS-NET-PROFIT", "净利润", current.net_profit, "样例经营数据：net_profit"),
        ],
        total_revenue=_money(current.revenue),
        total_cost=_money(current.cost),
        total_expense=_money(current.sales_expense + current.admin_expense + current.rd_expense + current.finance_expense),
        total_profit=_money(current.total_profit),
        net_profit=net_profit,
    )
    balance_sheet = BalanceSheet(
        title="资产负债表",
        period=request.period,
        items=[
            _line("BS-CASH", "货币资金", cash, "样例经营数据：cash"),
            _line("BS-AR", "应收账款", accounts_receivable, "样例经营数据：accounts_receivable"),
            _line("BS-INVENTORY", "存货", inventory, "样例经营数据：inventory"),
            _line("BS-FA", "固定资产", fixed_assets, "样例经营数据：fixed_assets"),
            _line("BS-ST-LOAN", "短期借款", short_term_loans, "样例经营数据：short_term_loans"),
            _line("BS-AP", "应付账款", accounts_payable, "样例经营数据：accounts_payable"),
            _line("BS-EQUITY", "所有者权益", total_equity, "样例经营数据：owner_equity"),
        ],
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=total_equity,
        total_liabilities_and_equity=total_liabilities_and_equity,
        balanced=total_assets == total_liabilities_and_equity,
    )
    cash_flow_statement = CashFlowStatement(
        title="现金流量表",
        period=request.period,
        items=[
            _line("CF-OPERATING", "经营活动现金流量净额", current.operating_cash_flow_net, "样例经营数据：operating_cash_flow_net"),
            _line("CF-INVESTING", "投资活动现金流量净额", current.investing_cash_flow_net, "样例经营数据：investing_cash_flow_net"),
            _line("CF-FINANCING", "筹资活动现金流量净额", current.financing_cash_flow_net, "样例经营数据：financing_cash_flow_net"),
        ],
        operating_cash_flow_net=_money(current.operating_cash_flow_net),
        investing_cash_flow_net=_money(current.investing_cash_flow_net),
        financing_cash_flow_net=_money(current.financing_cash_flow_net),
        net_cash_flow=_money(
            current.operating_cash_flow_net
            + current.investing_cash_flow_net
            + current.financing_cash_flow_net
        ),
    )
    equity_statement = EquityStatement(
        title="所有者权益变动表",
        period=request.period,
        items=[
            StatementLineItem(code="EQ-OPENING", name="期初所有者权益", amount=opening_equity, formula="上期所有者权益"),
            StatementLineItem(code="EQ-PROFIT", name="本期净利润", amount=net_profit, formula="利润表净利润"),
            StatementLineItem(code="EQ-ADJUSTMENT", name="权益调整", amount=equity_adjustment, formula="期末权益 - 期初权益 - 本期净利润"),
            StatementLineItem(code="EQ-CLOSING", name="期末所有者权益", amount=total_equity, formula="资产负债表所有者权益"),
        ],
        opening_equity=opening_equity,
        current_period_profit=net_profit,
        closing_equity=total_equity,
    )
    return _bundle(
        request=request,
        source="sample_finance_data",
        reviewed_voucher_count=0,
        balance_sheet=balance_sheet,
        income_statement=income_statement,
        cash_flow_statement=cash_flow_statement,
        equity_statement=equity_statement,
        mapping_set_id=mapping_set_id,
        trace_items=[
            StatementLineTrace(
                line_code="SAMPLE",
                rule_id="sample_finance_data",
                source_type="formula",
                formula="SAMPLE_FINANCE_DATA",
                amount=Decimal("0.00"),
                warnings=["当前账套无正式账簿数据，使用样例经营数据生成演示报表"],
            )
        ],
        validation_items=[
            StatementValidationItem(
                validation_code="balance_sheet_identity",
                validation_name="资产等于负债和所有者权益",
                status="passed" if balance_sheet.balanced else "failed",
                message="资产负债表平衡" if balance_sheet.balanced else "资产负债表不平衡",
                expected_amount=balance_sheet.total_assets,
                actual_amount=balance_sheet.total_liabilities_and_equity,
            ),
            StatementValidationItem(
                validation_code="sample_data_fallback",
                validation_name="样例数据回退",
                status="warning",
                message="当前账套无正式账簿数据，报表来自样例经营数据",
            ),
        ],
    )


def _bundle_from_mapped_ledger(
    request: FinancialStatementGenerateRequest,
    mapping_set_id: str,
    reviewed_voucher_count: int,
    accounts: list[LedgerAccountSummary],
    source: str = "reviewed_vouchers",
) -> FinancialStatementBundle:
    account_rows = [_ledger_account_to_row(account) for account in accounts]
    journal_lines = list_period_journal_lines_for_reporting(request.account_set_id, request.period)
    cash_flow_amounts, cash_warnings = infer_cash_flow_amounts(journal_lines)
    balance = calculate_statement_lines(mapping_set_id, "balance_sheet", account_rows, account_rows, cash_flow_amounts, {})
    income = calculate_statement_lines(mapping_set_id, "income_statement", account_rows, account_rows, cash_flow_amounts, {})
    cash_flow = calculate_statement_lines(mapping_set_id, "cash_flow_statement", account_rows, account_rows, cash_flow_amounts, {})
    net_profit = _line_amount(income.lines, "IS-NET-PROFIT")
    equity = calculate_statement_lines(
        mapping_set_id,
        "equity_statement",
        account_rows,
        account_rows,
        cash_flow_amounts,
        {},
        seed_values={"IS-NET-PROFIT": net_profit},
    )

    balance_sheet = _balance_sheet_from_lines(request.period, balance.lines)
    income_statement = _income_statement_from_lines(request.period, income.lines)
    cash_flow_statement = _cash_flow_statement_from_lines(request.period, cash_flow.lines)
    equity_statement = _equity_statement_from_lines(request.period, equity.lines)
    validation_items = balance.validation_items + income.validation_items + cash_flow.validation_items + equity.validation_items
    for warning in cash_warnings:
        validation_items.append(_warning_validation("cash_flow_inferred", "现金流项目推断", warning))

    return _bundle(
        request=request,
        source=source,
        reviewed_voucher_count=reviewed_voucher_count,
        balance_sheet=balance_sheet,
        income_statement=income_statement,
        cash_flow_statement=cash_flow_statement,
        equity_statement=equity_statement,
        mapping_set_id=mapping_set_id,
        trace_items=balance.trace_items + income.trace_items + cash_flow.trace_items + equity.trace_items,
        validation_items=validation_items,
    )


def _bundle(
    request: FinancialStatementGenerateRequest,
    source: str,
    reviewed_voucher_count: int,
    balance_sheet: BalanceSheet,
    income_statement: IncomeStatement,
    cash_flow_statement: CashFlowStatement,
    equity_statement: EquityStatement,
    mapping_set_id: str,
    trace_items: list[StatementLineTrace],
    validation_items: list[StatementValidationItem],
) -> FinancialStatementBundle:
    base_currency = "CNY"
    foreign_currency_line_count = _foreign_currency_line_count(request.account_set_id, request.period, base_currency)
    management_summary = _management_summary(balance_sheet, income_statement, cash_flow_statement, source)
    if foreign_currency_line_count:
        management_summary.highlights.append(
            f"本期包含外币分录 {foreign_currency_line_count} 行，报表金额按账套本位币 {base_currency} 展示。"
        )
    return FinancialStatementBundle(
        account_set_id=request.account_set_id,
        period=request.period,
        company_name=COMPANY_NAME,
        source=source,
        mapping_set_id=mapping_set_id,
        trace_items=trace_items if request.include_trace else [],
        validation_items=validation_items,
        summary=FinancialStatementGenerationSummary(
            account_set_id=request.account_set_id,
            period=request.period,
            source=source,
            reviewed_voucher_count=reviewed_voucher_count,
            asset_liability_balanced=balance_sheet.balanced,
            generated_statement_count=5,
            base_currency=base_currency,
            foreign_currency_line_count=foreign_currency_line_count,
        ),
        balance_sheet=balance_sheet,
        income_statement=income_statement,
        cash_flow_statement=cash_flow_statement,
        equity_statement=equity_statement,
        management_summary=management_summary,
    )


def _balance_sheet_from_lines(period: str, lines: list[StatementLineItem]) -> BalanceSheet:
    total_assets = _line_amount(lines, "BS-TOTAL-ASSETS")
    total_liabilities = _line_amount(lines, "BS-AP") + _line_amount(lines, "BS-TAX")
    total_equity = _line_amount(lines, "BS-EQUITY")
    total_liabilities_and_equity = _line_amount(lines, "BS-TOTAL-LIAB-EQUITY")
    return BalanceSheet(
        title="资产负债表",
        period=period,
        items=lines,
        total_assets=total_assets,
        total_liabilities=_q(total_liabilities),
        total_equity=total_equity,
        total_liabilities_and_equity=total_liabilities_and_equity,
        balanced=total_assets == total_liabilities_and_equity,
    )


def _income_statement_from_lines(period: str, lines: list[StatementLineItem]) -> IncomeStatement:
    total_revenue = _line_amount(lines, "IS-REVENUE")
    total_cost = _line_amount(lines, "IS-COST")
    total_tax_surcharge = _line_amount(lines, "IS-TAX-SURCHARGE")
    total_expense = _line_amount(lines, "IS-EXPENSE") + total_tax_surcharge
    net_profit = _line_amount(lines, "IS-NET-PROFIT")
    return IncomeStatement(
        title="利润表",
        period=period,
        items=lines,
        total_revenue=total_revenue,
        total_cost=total_cost,
        total_expense=_q(total_expense),
        total_profit=net_profit,
        net_profit=net_profit,
    )


def _cash_flow_statement_from_lines(period: str, lines: list[StatementLineItem]) -> CashFlowStatement:
    operating = _line_amount(lines, "CF-OPERATING-NET")
    investing = _line_amount(lines, "CF-INVESTING-NET")
    financing = _line_amount(lines, "CF-FINANCING-NET")
    return CashFlowStatement(
        title="现金流量表",
        period=period,
        items=lines,
        operating_cash_flow_net=operating,
        investing_cash_flow_net=investing,
        financing_cash_flow_net=financing,
        net_cash_flow=_line_amount(lines, "CF-NET-INCREASE"),
    )


def _equity_statement_from_lines(period: str, lines: list[StatementLineItem]) -> EquityStatement:
    return EquityStatement(
        title="所有者权益变动表",
        period=period,
        items=lines,
        opening_equity=_line_amount(lines, "EQ-OPENING"),
        current_period_profit=_line_amount(lines, "EQ-PROFIT"),
        closing_equity=_line_amount(lines, "EQ-CLOSING"),
    )


def _line_amount(lines: list[StatementLineItem], code: str) -> Decimal:
    for line in lines:
        if line.code == code:
            return _q(line.amount)
    return ZERO


def _ledger_account_to_row(account: LedgerAccountSummary) -> dict:
    return {
        "account_code": account.account_code,
        "account_name": account.account_name,
        "debit_total": account.debit_total,
        "credit_total": account.credit_total,
    }


def _warning_validation(code: str, name: str, message: str) -> StatementValidationItem:
    return StatementValidationItem(
        validation_code=code,
        validation_name=name,
        status="warning",
        message=message,
    )


def _management_summary(
    balance_sheet: BalanceSheet,
    income_statement: IncomeStatement,
    cash_flow_statement: CashFlowStatement,
    source: str,
) -> ManagementStatementSummary:
    net_margin = _percent(income_statement.net_profit, income_statement.total_revenue)
    liability_ratio = _percent(balance_sheet.total_liabilities, balance_sheet.total_assets)
    cash_profit_ratio = _percent(cash_flow_statement.operating_cash_flow_net, income_statement.net_profit)
    risks = []
    if not balance_sheet.balanced:
        risks.append("资产负债表不平衡，需复核科目映射或期初余额。")
    if cash_flow_statement.operating_cash_flow_net < income_statement.net_profit:
        risks.append("经营现金流低于净利润，需关注回款质量。")
    if not risks:
        risks.append("本期标准报表未发现自动校验差异。")
    return ManagementStatementSummary(
        title="管理报表摘要",
        key_metrics={
            "净利率": net_margin,
            "资产负债率": liability_ratio,
            "现金流利润比": cash_profit_ratio,
        },
        highlights=[
            f"报表来源：{source}。",
            f"本期净利润 {income_statement.net_profit:.2f}，期末资产 {balance_sheet.total_assets:.2f}。",
        ],
        risks=risks,
    )


def _foreign_currency_line_count(account_set_id: str, period: str, base_currency: str = "CNY") -> int:
    entries = list_journal_entries(account_set_id, period).entries
    return sum(1 for entry in entries for line in entry.lines if line.currency != base_currency)


def _find_record(period: str) -> MonthlyFinanceRecord:
    for record in SAMPLE_FINANCE_DATA:
        if record.period == period:
            return record
    available = ", ".join(record.period for record in SAMPLE_FINANCE_DATA)
    raise ValueError(f"未找到期间 {period}，可用期间：{available}")


def _previous_record(period: str) -> MonthlyFinanceRecord | None:
    for index, record in enumerate(SAMPLE_FINANCE_DATA):
        if record.period == period and index > 0:
            return SAMPLE_FINANCE_DATA[index - 1]
    return None


def _sum_accounts(
    accounts: list[LedgerAccountSummary],
    prefixes: tuple[str, ...],
    normal_side: str,
) -> Decimal:
    total = ZERO
    for account in accounts:
        if not account.account_code.startswith(prefixes):
            continue
        if normal_side == "credit":
            total += account.credit_total - account.debit_total
        else:
            total += account.debit_total - account.credit_total
    return _q(total)


def _line(code: str, name: str, amount: float | Decimal, formula: str) -> StatementLineItem:
    return StatementLineItem(code=code, name=name, amount=_money(amount), formula=formula)


def _money(value: float | Decimal) -> Decimal:
    return _q(Decimal(str(value)))


def _q(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _percent(numerator: Decimal, denominator: Decimal) -> str:
    if denominator == ZERO:
        return "0.00%"
    return f"{(numerator / denominator * Decimal('100')).quantize(TWOPLACES, rounding=ROUND_HALF_UP)}%"
