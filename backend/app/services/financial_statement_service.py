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
from app.services.analysis_service import COMPANY_NAME
from app.services.accounting_service import list_journal_entries
from app.services.ledger_service import build_general_ledger


TWOPLACES = Decimal("0.01")
ZERO = Decimal("0.00")


def generate_financial_statements(
    request: FinancialStatementGenerateRequest,
) -> FinancialStatementBundle:
    ledger = build_general_ledger(request.period, request.account_set_id)
    if ledger.accounts:
        source = "formal_journal_entries" if ledger.source == "formal_journal_entries" else "reviewed_vouchers"
        return _bundle_from_ledger(request, ledger.voucher_count, ledger.accounts, source)
    return _bundle_from_sample(request)


def _bundle_from_sample(request: FinancialStatementGenerateRequest) -> FinancialStatementBundle:
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
    )


def _bundle_from_ledger(
    request: FinancialStatementGenerateRequest,
    reviewed_voucher_count: int,
    accounts: list[LedgerAccountSummary],
    source: str = "reviewed_vouchers",
) -> FinancialStatementBundle:
    cash = _sum_accounts(accounts, ("1001", "1002"), "asset")
    accounts_receivable = _sum_accounts(accounts, ("1122",), "asset")
    inventory = _sum_accounts(accounts, ("1405",), "asset")
    fixed_assets = _sum_accounts(accounts, ("1601",), "asset")
    total_assets = cash + accounts_receivable + inventory + fixed_assets
    accounts_payable = _sum_accounts(accounts, ("2202",), "credit")
    short_term_loans = _sum_accounts(accounts, ("2001",), "credit")
    tax_payable = _sum_accounts(accounts, ("2221",), "credit")
    explicit_equity = _sum_accounts(accounts, ("4001",), "credit")
    total_liabilities = accounts_payable + short_term_loans + tax_payable
    revenue = _sum_accounts(accounts, ("6001", "6051"), "credit")
    cost = _sum_accounts(accounts, ("6401",), "asset")
    expense = _sum_accounts(accounts, ("6601", "6602", "6603"), "asset")
    total_profit = revenue - cost - expense
    net_profit = total_profit
    total_equity = explicit_equity if explicit_equity > ZERO else total_assets - total_liabilities
    total_liabilities_and_equity = total_liabilities + total_equity

    balance_sheet = BalanceSheet(
        title="资产负债表",
        period=request.period,
        items=[
            StatementLineItem(code="BS-CASH", name="货币资金", amount=cash, formula="1001/1002 借方余额"),
            StatementLineItem(code="BS-AR", name="应收账款", amount=accounts_receivable, formula="1122 借方余额"),
            StatementLineItem(code="BS-INVENTORY", name="存货", amount=inventory, formula="1405 借方余额"),
            StatementLineItem(code="BS-FA", name="固定资产", amount=fixed_assets, formula="1601 借方余额"),
            StatementLineItem(code="BS-ST-LOAN", name="短期借款", amount=short_term_loans, formula="2001 贷方余额"),
            StatementLineItem(code="BS-TAX", name="应交税费", amount=tax_payable, formula="2221 贷方余额"),
            StatementLineItem(code="BS-AP", name="应付账款", amount=accounts_payable, formula="2202 贷方余额"),
            StatementLineItem(code="BS-EQUITY", name="所有者权益", amount=total_equity, formula="4001 贷方余额或资产-负债"),
        ],
        total_assets=_q(total_assets),
        total_liabilities=_q(total_liabilities),
        total_equity=_q(total_equity),
        total_liabilities_and_equity=_q(total_liabilities_and_equity),
        balanced=_q(total_assets) == _q(total_liabilities_and_equity),
    )
    income_statement = IncomeStatement(
        title="利润表",
        period=request.period,
        items=[
            StatementLineItem(code="IS-REVENUE", name="营业收入", amount=revenue, formula="6001/6051 贷方发生额"),
            StatementLineItem(code="IS-COST", name="营业成本", amount=cost, formula="6401 借方发生额"),
            StatementLineItem(code="IS-EXPENSE", name="期间费用", amount=expense, formula="6601/6602/6603 借方发生额"),
            StatementLineItem(code="IS-NET-PROFIT", name="净利润", amount=net_profit, formula="营业收入-营业成本-期间费用"),
        ],
        total_revenue=_q(revenue),
        total_cost=_q(cost),
        total_expense=_q(expense),
        total_profit=_q(total_profit),
        net_profit=_q(net_profit),
    )
    cash_flow_statement = CashFlowStatement(
        title="现金流量表",
        period=request.period,
        items=[
            StatementLineItem(code="CF-OPERATING", name="经营活动现金流量净额", amount=ZERO, formula="凭证 MVP 暂未拆分现金流项目"),
            StatementLineItem(code="CF-INVESTING", name="投资活动现金流量净额", amount=ZERO, formula="凭证 MVP 暂未拆分现金流项目"),
            StatementLineItem(code="CF-FINANCING", name="筹资活动现金流量净额", amount=ZERO, formula="凭证 MVP 暂未拆分现金流项目"),
        ],
        operating_cash_flow_net=ZERO,
        investing_cash_flow_net=ZERO,
        financing_cash_flow_net=ZERO,
        net_cash_flow=ZERO,
    )
    equity_statement = EquityStatement(
        title="所有者权益变动表",
        period=request.period,
        items=[
            StatementLineItem(code="EQ-OPENING", name="期初所有者权益", amount=ZERO, formula="凭证 MVP 无期初余额"),
            StatementLineItem(code="EQ-PROFIT", name="本期净利润", amount=_q(net_profit), formula="利润表净利润"),
            StatementLineItem(code="EQ-CLOSING", name="期末所有者权益", amount=_q(total_equity), formula="资产-负债"),
        ],
        opening_equity=ZERO,
        current_period_profit=_q(net_profit),
        closing_equity=_q(total_equity),
    )
    return _bundle(
        request=request,
        source=source,
        reviewed_voucher_count=reviewed_voucher_count,
        balance_sheet=balance_sheet,
        income_statement=income_statement,
        cash_flow_statement=cash_flow_statement,
        equity_statement=equity_statement,
    )


def _bundle(
    request: FinancialStatementGenerateRequest,
    source: str,
    reviewed_voucher_count: int,
    balance_sheet: BalanceSheet,
    income_statement: IncomeStatement,
    cash_flow_statement: CashFlowStatement,
    equity_statement: EquityStatement,
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
