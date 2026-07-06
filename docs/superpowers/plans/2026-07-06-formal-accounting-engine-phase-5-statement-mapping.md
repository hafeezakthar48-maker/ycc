# Formal Accounting Engine Phase 5 Statement Mapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把现有财务报表 MVP 升级为正式报表映射与取数引擎，支持资产负债表、利润表、现金流量表和所有者权益变动表的配置化映射、生成追溯、公式校验和现金流项目映射。  
**Architecture:** 新增报表映射模型与服务，报表项目不再硬编码在 `financial_statement_service.py` 中，而是通过默认中国企业会计准则映射集计算。正式报表生成读取正式账簿、期末处理结果和现金流项目映射，返回每个报表项目的取数规则、来源科目、金额和校验结果；前端在报表面板中增加映射配置与追溯视图。  
**Tech Stack:** FastAPI、Pydantic、SQLite、Decimal、pytest、React、TypeScript、Vite、Node test runner。
---

## Prerequisite

必须先完成并验证：
- `docs/superpowers/plans/2026-07-06-formal-accounting-engine-phase-1.md`
- `docs/superpowers/plans/2026-07-06-formal-accounting-engine-phase-2-multi-currency.md`
- `docs/superpowers/plans/2026-07-06-formal-accounting-engine-phase-3-auxiliary-dimensions.md`
- `docs/superpowers/plans/2026-07-06-formal-accounting-engine-phase-4-period-close.md`
- 后端已有正式分录、正式账簿、期末损益结转和期间关闭守卫
- 现有 `backend/app/services/financial_statement_service.py` 能生成财务报表 MVP
- 现有 `frontend/src/components/FinancialStatementPanel.tsx` 能展示财务报表结果

本期不做合并报表、分部报告、XBRL、报表附注披露、正式税局申报表、复杂金融工具列报、递延所得税列报和长期股权投资权益法调整。本期只做单账套、单期间、正式账簿来源的标准报表映射底座。

## Accounting Decisions

- 报表项目映射使用账套级映射集，默认映射集内置为“中国企业会计准则通用科目表”。
- 资产负债表取期末余额；利润表取期间发生额；现金流量表取现金流项目金额；所有者权益变动表取期初权益、净利润、利润分配和期末权益。
- 报表项目金额统一使用本位币金额。外币原币余额只进入追溯信息，不直接影响报表列示金额。
- 现金流量表优先使用分录行或凭证行的 `cash_flow_item_code`；缺失时允许通过现金科目对方科目规则推断，并在校验结果中标记为 `warning`。
- 报表生成结果必须带有 `trace_items`，每个项目能看到映射规则、来源科目、来源方向、计算公式和金额。
- 报表公式校验必须返回结构化结果，不把错误藏在管理摘要文本里。
- 生成报表不会修改正式账簿；映射配置变更需要权限和审计日志。
- 已关闭期间仍允许重新生成报表，但不能修改该期间的正式分录或现金流项目标记。

## File Structure

- Create: `backend/app/models/statement_mapping.py`
  - 定义报表类型、映射集、映射规则、现金流项目、生成追溯和校验项模型。
- Create: `backend/app/services/statement_mapping_service.py`
  - 管理默认映射集、账套映射集、现金流项目映射和报表项目计算。
- Modify: `backend/app/models/financial_statement.py`
  - 增加 `mapping_set_id`、`trace_items`、`validation_items` 和现金流项目字段。
- Modify: `backend/app/services/financial_statement_service.py`
  - 从硬编码前缀汇总改为调用 `statement_mapping_service`。
- Modify: `backend/app/models/accounting.py`
  - 为正式分录行增加可选 `cash_flow_item_code`。
- Modify: `backend/app/services/accounting_service.py`
  - 保存、校验和查询分录行现金流项目。
- Modify: `backend/app/api/financial_statements.py`
  - 增加映射集查询、保存、校验和现金流项目 API。
- Modify: `backend/app/services/system_admin_service.py`
  - 增加报表映射查看、维护、校验权限。
- Modify: `backend/app/services/module_registry_service.py`
  - 注册报表映射 API、权限与审计事件。
- Create: `backend/tests/test_statement_mapping_service.py`
- Modify: `backend/tests/test_financial_statement_service.py`
- Modify: `backend/tests/test_financial_statement_api.py`
- Modify: `backend/tests/test_accounting_service.py`
- Create: `frontend/src/types/statementMapping.ts`
- Modify: `frontend/src/types/financialStatement.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/StatementMappingPanel.tsx`
- Modify: `frontend/src/components/FinancialStatementPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Create: `frontend/tests/statementMappingApi.test.mjs`
- Create: `frontend/tests/statementMappingPanel.test.mjs`
- Modify: `frontend/tests/financialStatementPanel.test.mjs`
- Modify: `frontend/package.json`
- Modify: `README.md`
- Modify: `docs/01-mvp-design.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

## Task 1: 报表映射模型与默认映射集

**Files:**
- Create: `backend/app/models/statement_mapping.py`
- Create: `backend/app/services/statement_mapping_service.py`
- Create: `backend/tests/test_statement_mapping_service.py`

- [ ] **Step 1: Write failing default mapping tests**

Create `backend/tests/test_statement_mapping_service.py`:

```python
from app.services.statement_mapping_service import (
    get_default_statement_mapping_set,
    list_statement_mapping_rules,
    reset_statement_mapping_store,
)


def setup_function():
    reset_statement_mapping_store()


def test_default_mapping_set_contains_four_statements():
    mapping_set = get_default_statement_mapping_set(account_set_id="default")
    rules = list_statement_mapping_rules(mapping_set.mapping_set_id)

    statement_types = {rule.statement_type for rule in rules}

    assert mapping_set.account_set_id == "default"
    assert mapping_set.mapping_set_name == "中国企业会计准则通用报表映射"
    assert statement_types == {
        "balance_sheet",
        "income_statement",
        "cash_flow_statement",
        "equity_statement",
    }
    assert any(rule.line_code == "BS-CASH" for rule in rules)
    assert any(rule.line_code == "IS-NET-PROFIT" for rule in rules)
    assert any(rule.line_code == "CF-OPERATING-NET" for rule in rules)
    assert any(rule.line_code == "EQ-CLOSING" for rule in rules)
```

- [ ] **Step 2: Implement statement mapping models**

Create `backend/app/models/statement_mapping.py`:

```python
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


StatementType = Literal[
    "balance_sheet",
    "income_statement",
    "cash_flow_statement",
    "equity_statement",
]
StatementRuleSource = Literal[
    "account_balance",
    "account_activity",
    "formula",
    "cash_flow_item",
    "period_close_result",
]
StatementNormalSide = Literal["debit", "credit", "none"]


class StatementMappingSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mapping_set_id: str
    account_set_id: str = "default"
    mapping_set_name: str
    base_currency: str = "CNY"
    is_default: bool = True
    enabled: bool = True
    updated_by: str = "system"
    updated_at: str


class StatementMappingRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    mapping_set_id: str
    statement_type: StatementType
    line_code: str
    line_name: str
    display_order: int
    source_type: StatementRuleSource
    normal_side: StatementNormalSide = "none"
    account_prefixes: list[str] = Field(default_factory=list)
    cash_flow_item_codes: list[str] = Field(default_factory=list)
    formula: str = ""
    sign: int = Field(default=1, ge=-1, le=1)
    enabled: bool = True


class CashFlowItemMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_code: str
    item_name: str
    activity_type: Literal["operating", "investing", "financing"]
    cash_account_prefixes: list[str]
    counterpart_account_prefixes: list[str]
    direction: Literal["inflow", "outflow"]


class StatementLineTrace(BaseModel):
    line_code: str
    rule_id: str
    source_type: StatementRuleSource
    source_account_codes: list[str] = Field(default_factory=list)
    cash_flow_item_codes: list[str] = Field(default_factory=list)
    formula: str
    amount: Decimal
    warnings: list[str] = Field(default_factory=list)


class StatementValidationItem(BaseModel):
    validation_code: str
    validation_name: str
    status: Literal["passed", "failed", "warning"]
    message: str
    expected_amount: Decimal | None = None
    actual_amount: Decimal | None = None
```

- [ ] **Step 3: Implement default mapping set**

Create `backend/app/services/statement_mapping_service.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.models.statement_mapping import (
    CashFlowItemMapping,
    StatementLineTrace,
    StatementMappingRule,
    StatementMappingSet,
    StatementValidationItem,
)

_MAPPING_SETS: dict[str, StatementMappingSet] = {}
_MAPPING_RULES: dict[str, list[StatementMappingRule]] = {}
_CASH_FLOW_ITEMS: dict[str, CashFlowItemMapping] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def reset_statement_mapping_store() -> None:
    _MAPPING_SETS.clear()
    _MAPPING_RULES.clear()
    _CASH_FLOW_ITEMS.clear()


def get_default_statement_mapping_set(account_set_id: str = "default") -> StatementMappingSet:
    mapping_set_id = f"stmtmap_{account_set_id}_default"
    if mapping_set_id not in _MAPPING_SETS:
        _MAPPING_SETS[mapping_set_id] = StatementMappingSet(
            mapping_set_id=mapping_set_id,
            account_set_id=account_set_id,
            mapping_set_name="中国企业会计准则通用报表映射",
            updated_at=_now_iso(),
        )
        _MAPPING_RULES[mapping_set_id] = _default_rules(mapping_set_id)
        for item in _default_cash_flow_items():
            _CASH_FLOW_ITEMS[item.item_code] = item
    return _MAPPING_SETS[mapping_set_id]


def list_statement_mapping_rules(mapping_set_id: str) -> list[StatementMappingRule]:
    return list(_MAPPING_RULES.get(mapping_set_id, []))


def _rule(
    mapping_set_id: str,
    statement_type: str,
    line_code: str,
    line_name: str,
    display_order: int,
    source_type: str,
    normal_side: str = "none",
    account_prefixes: list[str] | None = None,
    cash_flow_item_codes: list[str] | None = None,
    formula: str = "",
    sign: int = 1,
) -> StatementMappingRule:
    return StatementMappingRule(
        rule_id=f"{mapping_set_id}:{line_code}",
        mapping_set_id=mapping_set_id,
        statement_type=statement_type,
        line_code=line_code,
        line_name=line_name,
        display_order=display_order,
        source_type=source_type,
        normal_side=normal_side,
        account_prefixes=account_prefixes or [],
        cash_flow_item_codes=cash_flow_item_codes or [],
        formula=formula,
        sign=sign,
    )
```

Add `_default_rules(mapping_set_id)` with these required lines:

```python
def _default_rules(mapping_set_id: str) -> list[StatementMappingRule]:
    return [
        _rule(mapping_set_id, "balance_sheet", "BS-CASH", "货币资金", 10, "account_balance", "debit", ["1001", "1002"]),
        _rule(mapping_set_id, "balance_sheet", "BS-AR", "应收账款", 20, "account_balance", "debit", ["1122"]),
        _rule(mapping_set_id, "balance_sheet", "BS-INVENTORY", "存货", 30, "account_balance", "debit", ["1401", "1403", "1405"]),
        _rule(mapping_set_id, "balance_sheet", "BS-FA-NET", "固定资产净额", 40, "formula", formula="BS-FA-COST - BS-ACC-DEPR"),
        _rule(mapping_set_id, "balance_sheet", "BS-FA-COST", "固定资产原值", 41, "account_balance", "debit", ["1601"]),
        _rule(mapping_set_id, "balance_sheet", "BS-ACC-DEPR", "累计折旧", 42, "account_balance", "credit", ["1602"]),
        _rule(mapping_set_id, "balance_sheet", "BS-AP", "应付账款", 110, "account_balance", "credit", ["2202"]),
        _rule(mapping_set_id, "balance_sheet", "BS-TAX", "应交税费", 120, "account_balance", "credit", ["2221"]),
        _rule(mapping_set_id, "balance_sheet", "BS-EQUITY", "所有者权益", 210, "account_balance", "credit", ["4001", "4103", "4104"]),
        _rule(mapping_set_id, "balance_sheet", "BS-TOTAL-ASSETS", "资产合计", 900, "formula", formula="BS-CASH + BS-AR + BS-INVENTORY + BS-FA-NET"),
        _rule(mapping_set_id, "balance_sheet", "BS-TOTAL-LIAB-EQUITY", "负债和所有者权益合计", 910, "formula", formula="BS-AP + BS-TAX + BS-EQUITY"),
        _rule(mapping_set_id, "income_statement", "IS-REVENUE", "营业收入", 10, "account_activity", "credit", ["6001", "6051"]),
        _rule(mapping_set_id, "income_statement", "IS-COST", "营业成本", 20, "account_activity", "debit", ["6401"]),
        _rule(mapping_set_id, "income_statement", "IS-TAX-SURCHARGE", "税金及附加", 30, "account_activity", "debit", ["6403"]),
        _rule(mapping_set_id, "income_statement", "IS-EXPENSE", "期间费用", 40, "account_activity", "debit", ["6601", "6602", "6603"]),
        _rule(mapping_set_id, "income_statement", "IS-NET-PROFIT", "净利润", 900, "formula", formula="IS-REVENUE - IS-COST - IS-TAX-SURCHARGE - IS-EXPENSE"),
        _rule(mapping_set_id, "cash_flow_statement", "CF-OPERATING-NET", "经营活动现金流量净额", 10, "cash_flow_item", cash_flow_item_codes=["CFO-SALES-CASH", "CFO-PURCHASE-CASH", "CFO-PAYROLL-CASH", "CFO-TAX-CASH"]),
        _rule(mapping_set_id, "cash_flow_statement", "CF-INVESTING-NET", "投资活动现金流量净额", 20, "cash_flow_item", cash_flow_item_codes=["CFI-ASSET-PURCHASE", "CFI-ASSET-DISPOSAL"]),
        _rule(mapping_set_id, "cash_flow_statement", "CF-FINANCING-NET", "筹资活动现金流量净额", 30, "cash_flow_item", cash_flow_item_codes=["CFF-LOAN-IN", "CFF-LOAN-REPAY"]),
        _rule(mapping_set_id, "cash_flow_statement", "CF-NET-INCREASE", "现金及现金等价物净增加额", 900, "formula", formula="CF-OPERATING-NET + CF-INVESTING-NET + CF-FINANCING-NET"),
        _rule(mapping_set_id, "equity_statement", "EQ-OPENING", "期初所有者权益", 10, "account_balance", "credit", ["4001", "4103", "4104"]),
        _rule(mapping_set_id, "equity_statement", "EQ-PROFIT", "本期净利润", 20, "formula", formula="IS-NET-PROFIT"),
        _rule(mapping_set_id, "equity_statement", "EQ-DISTRIBUTION", "利润分配", 30, "period_close_result", "debit", ["4104"]),
        _rule(mapping_set_id, "equity_statement", "EQ-CLOSING", "期末所有者权益", 900, "formula", formula="EQ-OPENING + EQ-PROFIT - EQ-DISTRIBUTION"),
    ]
```

Add `_default_cash_flow_items()`:

```python
def _default_cash_flow_items() -> list[CashFlowItemMapping]:
    return [
        CashFlowItemMapping(item_code="CFO-SALES-CASH", item_name="销售商品、提供劳务收到的现金", activity_type="operating", cash_account_prefixes=["1001", "1002"], counterpart_account_prefixes=["1122", "6001", "6051"], direction="inflow"),
        CashFlowItemMapping(item_code="CFO-PURCHASE-CASH", item_name="购买商品、接受劳务支付的现金", activity_type="operating", cash_account_prefixes=["1001", "1002"], counterpart_account_prefixes=["1401", "1403", "1405", "2202"], direction="outflow"),
        CashFlowItemMapping(item_code="CFO-PAYROLL-CASH", item_name="支付给职工以及为职工支付的现金", activity_type="operating", cash_account_prefixes=["1001", "1002"], counterpart_account_prefixes=["2211"], direction="outflow"),
        CashFlowItemMapping(item_code="CFO-TAX-CASH", item_name="支付的各项税费", activity_type="operating", cash_account_prefixes=["1001", "1002"], counterpart_account_prefixes=["2221"], direction="outflow"),
        CashFlowItemMapping(item_code="CFI-ASSET-PURCHASE", item_name="购建固定资产支付的现金", activity_type="investing", cash_account_prefixes=["1001", "1002"], counterpart_account_prefixes=["1601"], direction="outflow"),
        CashFlowItemMapping(item_code="CFI-ASSET-DISPOSAL", item_name="处置固定资产收到的现金", activity_type="investing", cash_account_prefixes=["1001", "1002"], counterpart_account_prefixes=["1606"], direction="inflow"),
        CashFlowItemMapping(item_code="CFF-LOAN-IN", item_name="取得借款收到的现金", activity_type="financing", cash_account_prefixes=["1001", "1002"], counterpart_account_prefixes=["2001", "2501"], direction="inflow"),
        CashFlowItemMapping(item_code="CFF-LOAN-REPAY", item_name="偿还债务支付的现金", activity_type="financing", cash_account_prefixes=["1001", "1002"], counterpart_account_prefixes=["2001", "2501"], direction="outflow"),
    ]
```

- [ ] **Step 4: Run backend tests and commit**

```powershell
python -m pytest backend/tests/test_statement_mapping_service.py
git add backend/app/models/statement_mapping.py backend/app/services/statement_mapping_service.py backend/tests/test_statement_mapping_service.py
git commit -m "feat: add statement mapping defaults"
```

## Task 2: 报表项目计算与公式引擎

**Files:**
- Modify: `backend/app/services/statement_mapping_service.py`
- Modify: `backend/tests/test_statement_mapping_service.py`

- [ ] **Step 1: Write failing calculation tests**

Append to `backend/tests/test_statement_mapping_service.py`:

```python
from decimal import Decimal

from app.services.statement_mapping_service import calculate_statement_lines


def test_calculate_balance_sheet_lines_from_account_balances():
    mapping_set = get_default_statement_mapping_set("default")
    balances = [
        {"account_code": "1002", "account_name": "银行存款", "debit_total": Decimal("1500.00"), "credit_total": Decimal("200.00")},
        {"account_code": "1122", "account_name": "应收账款", "debit_total": Decimal("800.00"), "credit_total": Decimal("100.00")},
        {"account_code": "2202", "account_name": "应付账款", "debit_total": Decimal("50.00"), "credit_total": Decimal("450.00")},
        {"account_code": "4001", "account_name": "实收资本", "debit_total": Decimal("0.00"), "credit_total": Decimal("1600.00")},
    ]

    result = calculate_statement_lines(
        mapping_set_id=mapping_set.mapping_set_id,
        statement_type="balance_sheet",
        account_balances=balances,
        account_activities=[],
        cash_flow_amounts={},
        period_close_amounts={},
    )

    amount_by_code = {line.code: line.amount for line in result.lines}

    assert amount_by_code["BS-CASH"] == Decimal("1300.00")
    assert amount_by_code["BS-AR"] == Decimal("700.00")
    assert amount_by_code["BS-AP"] == Decimal("400.00")
    assert amount_by_code["BS-TOTAL-ASSETS"] == Decimal("2000.00")
    assert result.trace_items[0].line_code == "BS-CASH"
```

- [ ] **Step 2: Add calculation result models inside service**

In `backend/app/services/statement_mapping_service.py`:

```python
from pydantic import BaseModel

from app.models.financial_statement import StatementLineItem


class StatementCalculationResult(BaseModel):
    lines: list[StatementLineItem]
    trace_items: list[StatementLineTrace]
    validation_items: list[StatementValidationItem]
```

- [ ] **Step 3: Implement account and formula calculation**

Add pure calculation helpers:

```python
ZERO = Decimal("0.00")
TWOPLACES = Decimal("0.01")


def calculate_statement_lines(
    mapping_set_id: str,
    statement_type: str,
    account_balances: list[dict],
    account_activities: list[dict],
    cash_flow_amounts: dict[str, Decimal],
    period_close_amounts: dict[str, Decimal],
) -> StatementCalculationResult:
    rules = [
        rule for rule in list_statement_mapping_rules(mapping_set_id)
        if rule.statement_type == statement_type and rule.enabled
    ]
    values: dict[str, Decimal] = {}
    lines: list[StatementLineItem] = []
    traces: list[StatementLineTrace] = []

    for rule in sorted(rules, key=lambda item: item.display_order):
        if rule.source_type == "account_balance":
            amount, accounts = _sum_account_rows(account_balances, rule.account_prefixes, rule.normal_side)
            formula = f"{'/'.join(rule.account_prefixes)} {rule.normal_side} balance"
        elif rule.source_type == "account_activity":
            amount, accounts = _sum_account_rows(account_activities, rule.account_prefixes, rule.normal_side)
            formula = f"{'/'.join(rule.account_prefixes)} {rule.normal_side} activity"
        elif rule.source_type == "cash_flow_item":
            amount = sum(cash_flow_amounts.get(code, ZERO) for code in rule.cash_flow_item_codes)
            accounts = []
            formula = " + ".join(rule.cash_flow_item_codes)
        elif rule.source_type == "period_close_result":
            amount = sum(period_close_amounts.get(prefix, ZERO) for prefix in rule.account_prefixes)
            accounts = list(rule.account_prefixes)
            formula = "period close result"
        else:
            amount = _evaluate_formula(rule.formula, values)
            accounts = []
            formula = rule.formula

        amount = _q(amount * Decimal(rule.sign))
        values[rule.line_code] = amount
        lines.append(StatementLineItem(code=rule.line_code, name=rule.line_name, amount=amount, formula=formula))
        traces.append(
            StatementLineTrace(
                line_code=rule.line_code,
                rule_id=rule.rule_id,
                source_type=rule.source_type,
                source_account_codes=accounts,
                cash_flow_item_codes=list(rule.cash_flow_item_codes),
                formula=formula,
                amount=amount,
            )
        )

    return StatementCalculationResult(lines=lines, trace_items=traces, validation_items=_validate_statement(statement_type, values))
```

Add helpers:

```python
def _sum_account_rows(rows: list[dict], prefixes: list[str], normal_side: str) -> tuple[Decimal, list[str]]:
    total = ZERO
    matched_accounts: list[str] = []
    for row in rows:
        account_code = str(row["account_code"])
        if not any(account_code.startswith(prefix) for prefix in prefixes):
            continue
        debit_total = Decimal(str(row.get("debit_total", "0")))
        credit_total = Decimal(str(row.get("credit_total", "0")))
        matched_accounts.append(account_code)
        if normal_side == "credit":
            total += credit_total - debit_total
        else:
            total += debit_total - credit_total
    return _q(total), matched_accounts


def _evaluate_formula(formula: str, values: dict[str, Decimal]) -> Decimal:
    tokens = formula.replace("+", " + ").replace("-", " - ").split()
    total = ZERO
    sign = Decimal("1")
    for token in tokens:
        if token == "+":
            sign = Decimal("1")
        elif token == "-":
            sign = Decimal("-1")
        else:
            total += values.get(token, ZERO) * sign
    return _q(total)


def _validate_statement(statement_type: str, values: dict[str, Decimal]) -> list[StatementValidationItem]:
    if statement_type == "balance_sheet":
        expected = values.get("BS-TOTAL-ASSETS", ZERO)
        actual = values.get("BS-TOTAL-LIAB-EQUITY", ZERO)
        return [
            StatementValidationItem(
                validation_code="balance_sheet_identity",
                validation_name="资产等于负债和所有者权益",
                status="passed" if expected == actual else "failed",
                message="资产负债表平衡" if expected == actual else "资产负债表不平衡",
                expected_amount=expected,
                actual_amount=actual,
            )
        ]
    return []


def _q(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES)
```

- [ ] **Step 4: Verify and commit**

```powershell
python -m pytest backend/tests/test_statement_mapping_service.py
git add backend/app/services/statement_mapping_service.py backend/tests/test_statement_mapping_service.py
git commit -m "feat: calculate mapped statement lines"
```

## Task 3: 现金流项目标记与现金流映射

**Files:**
- Modify: `backend/app/models/accounting.py`
- Modify: `backend/app/services/accounting_service.py`
- Modify: `backend/app/services/statement_mapping_service.py`
- Modify: `backend/tests/test_accounting_service.py`
- Modify: `backend/tests/test_statement_mapping_service.py`

- [ ] **Step 1: Write failing cash-flow mapping tests**

Append to `backend/tests/test_statement_mapping_service.py`:

```python
from app.services.statement_mapping_service import infer_cash_flow_amounts


def test_infer_cash_flow_amounts_from_cash_and_counterpart_accounts():
    journal_lines = [
        {"entry_id": "je_1", "account_code": "1002", "direction": "debit", "amount": Decimal("500.00"), "cash_flow_item_code": "CFO-SALES-CASH"},
        {"entry_id": "je_1", "account_code": "6001", "direction": "credit", "amount": Decimal("500.00"), "cash_flow_item_code": ""},
        {"entry_id": "je_2", "account_code": "1002", "direction": "credit", "amount": Decimal("120.00"), "cash_flow_item_code": ""},
        {"entry_id": "je_2", "account_code": "2211", "direction": "debit", "amount": Decimal("120.00"), "cash_flow_item_code": ""},
    ]

    amounts, warnings = infer_cash_flow_amounts(journal_lines)

    assert amounts["CFO-SALES-CASH"] == Decimal("500.00")
    assert amounts["CFO-PAYROLL-CASH"] == Decimal("-120.00")
    assert warnings == ["je_2 使用对方科目推断现金流项目 CFO-PAYROLL-CASH"]
```

- [ ] **Step 2: Add optional cash flow item field to accounting models**

In `backend/app/models/accounting.py`, add this field to formal journal line create and response models:

```python
cash_flow_item_code: str | None = Field(default=None, max_length=64)
```

Validation rule:

```python
def normalize_cash_flow_item_code(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().upper()
```

- [ ] **Step 3: Persist and expose cash flow item code**

In `backend/app/services/accounting_service.py`:

```python
def _serialize_journal_line(line: JournalLineCreate) -> dict:
    payload = line.model_dump()
    payload["cash_flow_item_code"] = normalize_cash_flow_item_code(line.cash_flow_item_code)
    return payload
```

When reading lines back from the store, include `cash_flow_item_code` in response payloads. Keep empty string for lines without mapping so frontend can render a blank state consistently.

Add a reporting query for statement generation:

```python
def list_period_journal_lines_for_reporting(account_set_id: str, period: str) -> list[dict]:
    rows: list[dict] = []
    for entry in _JOURNAL_ENTRIES.values():
        if entry.account_set_id != account_set_id:
            continue
        if not entry.entry_date.startswith(period):
            continue
        for line in entry.lines:
            rows.append(
                {
                    "entry_id": entry.entry_id,
                    "account_code": line.account_code,
                    "account_name": line.account_name,
                    "direction": line.direction,
                    "amount": line.base_amount,
                    "cash_flow_item_code": normalize_cash_flow_item_code(line.cash_flow_item_code),
                }
            )
    return rows
```

- [ ] **Step 4: Implement cash flow inference**

In `backend/app/services/statement_mapping_service.py`:

```python
def infer_cash_flow_amounts(journal_lines: list[dict]) -> tuple[dict[str, Decimal], list[str]]:
    get_default_statement_mapping_set("default")
    amounts: dict[str, Decimal] = {}
    warnings: list[str] = []
    lines_by_entry: dict[str, list[dict]] = {}
    for line in journal_lines:
        lines_by_entry.setdefault(str(line["entry_id"]), []).append(line)

    for entry_id, lines in lines_by_entry.items():
        explicit_items = [line for line in lines if str(line.get("cash_flow_item_code", "")).strip()]
        if explicit_items:
            for line in explicit_items:
                code = str(line["cash_flow_item_code"]).strip().upper()
                amount = _cash_signed_amount(line, code)
                amounts[code] = _q(amounts.get(code, ZERO) + amount)
            continue

        inferred_code = _infer_cash_flow_code(lines)
        if inferred_code:
            amount = sum(_cash_signed_amount(line, inferred_code) for line in lines if _is_cash_line(line))
            amounts[inferred_code] = _q(amounts.get(inferred_code, ZERO) + amount)
            warnings.append(f"{entry_id} 使用对方科目推断现金流项目 {inferred_code}")

    return amounts, warnings
```

Add helpers:

```python
def _is_cash_line(line: dict) -> bool:
    account_code = str(line["account_code"])
    return account_code.startswith("1001") or account_code.startswith("1002")


def _cash_signed_amount(line: dict, item_code: str) -> Decimal:
    amount = Decimal(str(line["amount"]))
    direction = str(line["direction"]).lower()
    item = _CASH_FLOW_ITEMS.get(item_code)
    if item and item.direction == "outflow":
        return -amount
    return amount if direction == "debit" else -amount


def _infer_cash_flow_code(lines: list[dict]) -> str:
    cash_lines = [line for line in lines if _is_cash_line(line)]
    counterpart_lines = [line for line in lines if not _is_cash_line(line)]
    if not cash_lines or not counterpart_lines:
        return ""
    for item in _CASH_FLOW_ITEMS.values():
        if any(_matches_prefix(line, item.cash_account_prefixes) for line in cash_lines) and any(
            _matches_prefix(line, item.counterpart_account_prefixes) for line in counterpart_lines
        ):
            return item.item_code
    return ""


def _matches_prefix(line: dict, prefixes: list[str]) -> bool:
    account_code = str(line["account_code"])
    return any(account_code.startswith(prefix) for prefix in prefixes)
```

- [ ] **Step 5: Verify and commit**

```powershell
python -m pytest backend/tests/test_statement_mapping_service.py backend/tests/test_accounting_service.py
git add backend/app/models/accounting.py backend/app/services/accounting_service.py backend/app/services/statement_mapping_service.py backend/tests/test_accounting_service.py backend/tests/test_statement_mapping_service.py
git commit -m "feat: map cash flow items"
```

## Task 4: 财务报表生成服务改造

**Files:**
- Modify: `backend/app/models/financial_statement.py`
- Modify: `backend/app/services/financial_statement_service.py`
- Modify: `backend/tests/test_financial_statement_service.py`

- [ ] **Step 1: Write failing mapped statement generation tests**

Append to `backend/tests/test_financial_statement_service.py`:

```python
def test_financial_statements_include_mapping_trace_and_validations():
    result = generate_financial_statements(FinancialStatementGenerateRequest(period="2026-06"))

    assert result.mapping_set_id.startswith("stmtmap_default")
    assert result.trace_items
    assert result.validation_items
    assert any(item.validation_code == "balance_sheet_identity" for item in result.validation_items)
    assert all(trace.line_code for trace in result.trace_items)
```

- [ ] **Step 2: Extend financial statement models**

In `backend/app/models/financial_statement.py`, import models:

```python
from app.models.statement_mapping import StatementLineTrace, StatementValidationItem
```

Update `FinancialStatementGenerateRequest`:

```python
mapping_set_id: str | None = Field(default=None, max_length=128)
include_trace: bool = True
```

Update `FinancialStatementBundle`:

```python
mapping_set_id: str
trace_items: list[StatementLineTrace]
validation_items: list[StatementValidationItem]
```

- [ ] **Step 3: Replace hard-coded mappings with mapping service**

In `backend/app/services/financial_statement_service.py`, keep sample fallback for demo data and add mapped formal path:

```python
from app.services.accounting_service import list_period_journal_lines_for_reporting
from app.services.statement_mapping_service import (
    calculate_statement_lines,
    get_default_statement_mapping_set,
    infer_cash_flow_amounts,
)
```

Add helper:

```python
def _mapping_set_id(request: FinancialStatementGenerateRequest) -> str:
    if request.mapping_set_id:
        return request.mapping_set_id
    return get_default_statement_mapping_set(request.account_set_id).mapping_set_id
```

In `generate_financial_statements`, use the mapping set when ledger accounts exist:

```python
def generate_financial_statements(
    request: FinancialStatementGenerateRequest,
) -> FinancialStatementBundle:
    mapping_set_id = _mapping_set_id(request)
    ledger = build_general_ledger(request.period, request.account_set_id)
    if ledger.accounts:
        return _bundle_from_mapped_ledger(request, mapping_set_id, ledger.voucher_count, ledger.accounts)
    return _bundle_from_sample(request)
```

Add mapped path:

```python
def _bundle_from_mapped_ledger(
    request: FinancialStatementGenerateRequest,
    mapping_set_id: str,
    reviewed_voucher_count: int,
    accounts: list[LedgerAccountSummary],
) -> FinancialStatementBundle:
    account_rows = [_ledger_account_to_row(account) for account in accounts]
    journal_lines = list_period_journal_lines_for_reporting(request.account_set_id, request.period)
    cash_flow_amounts, cash_warnings = infer_cash_flow_amounts(journal_lines)
    balance = calculate_statement_lines(mapping_set_id, "balance_sheet", account_rows, account_rows, cash_flow_amounts, {})
    income = calculate_statement_lines(mapping_set_id, "income_statement", account_rows, account_rows, cash_flow_amounts, {})
    cash_flow = calculate_statement_lines(mapping_set_id, "cash_flow_statement", account_rows, account_rows, cash_flow_amounts, {})
    equity = calculate_statement_lines(mapping_set_id, "equity_statement", account_rows, account_rows, cash_flow_amounts, {})

    balance_sheet = _balance_sheet_from_lines(request.period, balance.lines)
    income_statement = _income_statement_from_lines(request.period, income.lines)
    cash_flow_statement = _cash_flow_statement_from_lines(request.period, cash_flow.lines)
    equity_statement = _equity_statement_from_lines(request.period, equity.lines)
    validation_items = balance.validation_items + income.validation_items + cash_flow.validation_items + equity.validation_items
    for warning in cash_warnings:
        validation_items.append(_warning_validation("cash_flow_inferred", "现金流项目推断", warning))

    return _bundle(
        request=request,
        source="formal_ledger",
        reviewed_voucher_count=reviewed_voucher_count,
        balance_sheet=balance_sheet,
        income_statement=income_statement,
        cash_flow_statement=cash_flow_statement,
        equity_statement=equity_statement,
        mapping_set_id=mapping_set_id,
        trace_items=balance.trace_items + income.trace_items + cash_flow.trace_items + equity.trace_items,
        validation_items=validation_items,
    )
```

Add converter:

```python
def _ledger_account_to_row(account: LedgerAccountSummary) -> dict:
    return {
        "account_code": account.account_code,
        "account_name": account.account_name,
        "debit_total": account.debit_total,
        "credit_total": account.credit_total,
    }
```

- [ ] **Step 4: Keep sample fallback trace explicit**

When `_bundle_from_sample` returns demo data, set:

```python
mapping_set_id="sample_finance_data"
trace_items=[
    StatementLineTrace(
        line_code="SAMPLE",
        rule_id="sample_finance_data",
        source_type="formula",
        formula="SAMPLE_FINANCE_DATA",
        amount=Decimal("0.00"),
        warnings=["当前账套无正式账簿数据，使用样例经营数据生成演示报表"],
    )
]
validation_items=[
    StatementValidationItem(
        validation_code="sample_data_fallback",
        validation_name="样例数据回退",
        status="warning",
        message="当前账套无正式账簿数据，报表来自样例经营数据",
    )
]
```

- [ ] **Step 5: Verify and commit**

```powershell
python -m pytest backend/tests/test_statement_mapping_service.py backend/tests/test_financial_statement_service.py
git add backend/app/models/financial_statement.py backend/app/services/financial_statement_service.py backend/tests/test_financial_statement_service.py
git commit -m "feat: generate statements from mappings"
```

## Task 5: 报表映射 API、权限与审计

**Files:**
- Modify: `backend/app/api/financial_statements.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Modify: `backend/tests/test_financial_statement_api.py`

- [ ] **Step 1: Write failing API tests**

Append to `backend/tests/test_financial_statement_api.py`:

```python
def test_statement_mapping_api_returns_default_rules():
    response = client.get(
        "/api/v1/financial-statements/mapping-sets/default",
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mapping_set"]["mapping_set_name"] == "中国企业会计准则通用报表映射"
    assert any(rule["line_code"] == "BS-CASH" for rule in payload["rules"])


def test_statement_generate_returns_trace_and_validation_items():
    response = client.post(
        "/api/v1/financial-statements/generate",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={"period": "2026-06", "account_set_id": "default", "include_trace": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "mapping_set_id" in payload
    assert "trace_items" in payload
    assert "validation_items" in payload
```

- [ ] **Step 2: Add mapping API routes**

In `backend/app/api/financial_statements.py`:

```python
from app.services.statement_mapping_service import (
    get_default_statement_mapping_set,
    list_statement_mapping_rules,
)
```

Add route:

```python
@router.get("/mapping-sets/default")
def get_default_mapping_set(account_set_id: str = "default", x_actor_id: str = Header(default="system")):
    _require_permission(
        actor_id=x_actor_id,
        permission_code="statement.mapping.view",
        event="statement.mapping.view",
        target_id=f"statement-mapping:{account_set_id}:default",
        metadata={"account_set_id": account_set_id},
    )
    mapping_set = get_default_statement_mapping_set(account_set_id)
    return {
        "mapping_set": mapping_set,
        "rules": list_statement_mapping_rules(mapping_set.mapping_set_id),
    }
```

Refactor the existing permission helper into generic `_require_permission`:

```python
def _require_permission(
    actor_id: str,
    permission_code: str,
    event: str,
    target_id: str,
    metadata: dict[str, str | int | float | bool | None],
) -> None:
    if actor_id == "system":
        return
    decision = authorize(actor_id, permission_code)
    if decision.allowed:
        return
    _record_statement_audit(
        actor_id=actor_id,
        event=event,
        target_id=target_id,
        result="denied",
        metadata={**metadata, "permission_code": permission_code, "reason": decision.reason},
    )
    raise HTTPException(status_code=403, detail=decision.reason)
```

- [ ] **Step 3: Register permissions and audit events**

Permissions:
- `statement.generate`
- `statement.validate`
- `statement.mapping.view`
- `statement.mapping.manage`

Audit events:
- `statement.generate`
- `statement.validate`
- `statement.mapping.view`
- `statement.mapping.update`

Finance manager role gets all four permissions. API integrator role keeps read-only access only when current system policy already allows finance reads; otherwise no new permission is granted.

- [ ] **Step 4: Verify and commit**

```powershell
python -m pytest backend/tests/test_financial_statement_api.py backend/tests/test_system_admin_api.py
git add backend/app/api/financial_statements.py backend/app/services/system_admin_service.py backend/app/services/module_registry_service.py backend/tests/test_financial_statement_api.py
git commit -m "feat: expose statement mapping api"
```

## Task 6: 前端映射配置与追溯视图

**Files:**
- Create: `frontend/src/types/statementMapping.ts`
- Modify: `frontend/src/types/financialStatement.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/StatementMappingPanel.tsx`
- Modify: `frontend/src/components/FinancialStatementPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Create: `frontend/tests/statementMappingApi.test.mjs`
- Create: `frontend/tests/statementMappingPanel.test.mjs`
- Modify: `frontend/tests/financialStatementPanel.test.mjs`
- Modify: `frontend/package.json`

- [ ] **Step 1: Write frontend API and panel tests**

Create `frontend/tests/statementMappingApi.test.mjs`:

```javascript
import assert from "node:assert/strict";
import test from "node:test";

import { fetchDefaultStatementMappingSet } from "../src/services/dashboardApi.ts";

function createFetcher(payload) {
  const calls = [];
  const fetcher = async (url, init = {}) => {
    calls.push({ url, init });
    return {
      ok: true,
      status: 200,
      json: async () => payload
    };
  };
  fetcher.calls = calls;
  return fetcher;
}

test("报表映射 API helper 获取默认映射集", async () => {
  const fetcher = createFetcher({
    mapping_set: { mapping_set_id: "stmtmap_default_default", mapping_set_name: "中国企业会计准则通用报表映射" },
    rules: [{ line_code: "BS-CASH", line_name: "货币资金" }]
  });

  const result = await fetchDefaultStatementMappingSet("default", "http://api.local", fetcher);

  assert.equal(result.mapping_set.mapping_set_id, "stmtmap_default_default");
  assert.equal(fetcher.calls[0].url, "http://api.local/api/v1/financial-statements/mapping-sets/default?account_set_id=default");
  assert.equal(fetcher.calls[0].init.headers["X-Actor-Id"], "u-finance-manager");
});
```

Create `frontend/tests/statementMappingPanel.test.mjs`:

```javascript
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("报表映射面板展示映射规则和校验追溯", async () => {
  const panel = await readFile(resolve("src/components/StatementMappingPanel.tsx"), "utf8");
  const financialPanel = await readFile(resolve("src/components/FinancialStatementPanel.tsx"), "utf8");

  assert.match(panel, /statement-mapping-panel/);
  assert.match(panel, /fetchDefaultStatementMappingSet/);
  assert.match(panel, /资产负债表/);
  assert.match(panel, /利润表/);
  assert.match(panel, /现金流量表/);
  assert.match(panel, /所有者权益变动表/);
  assert.match(financialPanel, /trace_items/);
  assert.match(financialPanel, /validation_items/);
});
```

- [ ] **Step 2: Add frontend types**

Create `frontend/src/types/statementMapping.ts`:

```typescript
export type StatementType =
  | "balance_sheet"
  | "income_statement"
  | "cash_flow_statement"
  | "equity_statement";

export type StatementRuleSource =
  | "account_balance"
  | "account_activity"
  | "formula"
  | "cash_flow_item"
  | "period_close_result";

export interface StatementMappingSet {
  mapping_set_id: string;
  account_set_id: string;
  mapping_set_name: string;
  base_currency: string;
  is_default: boolean;
  enabled: boolean;
  updated_by: string;
  updated_at: string;
}

export interface StatementMappingRule {
  rule_id: string;
  mapping_set_id: string;
  statement_type: StatementType;
  line_code: string;
  line_name: string;
  display_order: number;
  source_type: StatementRuleSource;
  normal_side: "debit" | "credit" | "none";
  account_prefixes: string[];
  cash_flow_item_codes: string[];
  formula: string;
  sign: number;
  enabled: boolean;
}

export interface StatementMappingSetResponse {
  mapping_set: StatementMappingSet;
  rules: StatementMappingRule[];
}
```

Modify `frontend/src/types/financialStatement.ts`:

```typescript
export interface StatementLineTrace {
  line_code: string;
  rule_id: string;
  source_type: string;
  source_account_codes: string[];
  cash_flow_item_codes: string[];
  formula: string;
  amount: MoneyValue;
  warnings: string[];
}

export interface StatementValidationItem {
  validation_code: string;
  validation_name: string;
  status: "passed" | "failed" | "warning";
  message: string;
  expected_amount?: MoneyValue | null;
  actual_amount?: MoneyValue | null;
}
```

Add to `FinancialStatementBundle`:

```typescript
mapping_set_id: string;
trace_items: StatementLineTrace[];
validation_items: StatementValidationItem[];
```

- [ ] **Step 3: Add dashboard API helpers**

In `frontend/src/services/dashboardApi.ts`:

```typescript
import type { StatementMappingSetResponse } from "../types/statementMapping";
```

Add:

```typescript
export function fetchDefaultStatementMappingSet(
  accountSetId = "default",
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<StatementMappingSetResponse> {
  return fetcher(
    `${apiBase}/api/v1/financial-statements/mapping-sets/default?account_set_id=${encodeURIComponent(accountSetId)}`,
    { headers: { "X-Actor-Id": actorId } }
  ).then(async (response) => {
    if (!response.ok) {
      throw new Error(`报表映射 API 请求失败：${response.status}`);
    }
    return response.json() as Promise<StatementMappingSetResponse>;
  });
}
```

- [ ] **Step 4: Build StatementMappingPanel**

Create `frontend/src/components/StatementMappingPanel.tsx`:

```tsx
import { useEffect, useMemo, useState } from "react";
import { fetchDefaultStatementMappingSet } from "../services/dashboardApi";
import type { StatementMappingRule, StatementMappingSetResponse, StatementType } from "../types/statementMapping";

const statementLabels: Record<StatementType, string> = {
  balance_sheet: "资产负债表",
  income_statement: "利润表",
  cash_flow_statement: "现金流量表",
  equity_statement: "所有者权益变动表"
};

export default function StatementMappingPanel() {
  const [payload, setPayload] = useState<StatementMappingSetResponse | null>(null);
  const [activeStatement, setActiveStatement] = useState<StatementType>("balance_sheet");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchDefaultStatementMappingSet()
      .then((result) => {
        if (!cancelled) {
          setPayload(result);
        }
      })
      .catch((mappingError) => {
        if (!cancelled) {
          setError(mappingError instanceof Error ? mappingError.message : "报表映射读取失败");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const rules = useMemo(
    () => (payload?.rules ?? []).filter((rule) => rule.statement_type === activeStatement),
    [payload, activeStatement]
  );

  return (
    <section id="statement-mapping-panel" className="statement-mapping-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">报表映射</span>
          <h2>{payload?.mapping_set.mapping_set_name ?? "中国企业会计准则通用报表映射"}</h2>
        </div>
      </div>
      {error ? <p className="inline-error">{error}</p> : null}
      <div className="statement-tab-list">
        {(Object.keys(statementLabels) as StatementType[]).map((type) => (
          <button
            key={type}
            type="button"
            className={activeStatement === type ? "button-primary" : "button-secondary"}
            onClick={() => setActiveStatement(type)}
          >
            {statementLabels[type]}
          </button>
        ))}
      </div>
      <div className="voucher-table-wrap">
        <table className="voucher-table statement-mapping-table">
          <thead>
            <tr>
              <th>项目编码</th>
              <th>项目名称</th>
              <th>来源</th>
              <th>科目前缀</th>
              <th>公式</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((rule: StatementMappingRule) => (
              <tr key={rule.rule_id}>
                <td>{rule.line_code}</td>
                <td>{rule.line_name}</td>
                <td>{rule.source_type}</td>
                <td>{rule.account_prefixes.join(" / ") || rule.cash_flow_item_codes.join(" / ")}</td>
                <td>{rule.formula || rule.normal_side}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
```

- [ ] **Step 5: Show trace and validation in FinancialStatementPanel**

In `frontend/src/components/FinancialStatementPanel.tsx`, add:

```tsx
<section className="panel statement-validation-panel">
  <div className="panel-header">
    <div>
      <span className="eyebrow">校验追溯</span>
      <h3>报表生成校验</h3>
    </div>
  </div>
  <div className="statement-validation-list">
    {(bundle?.validation_items ?? []).map((item) => (
      <p key={item.validation_code} className={`statement-validation statement-validation--${item.status}`}>
        {item.validation_name}：{item.message}
      </p>
    ))}
  </div>
  <div className="statement-trace-list">
    {(bundle?.trace_items ?? []).slice(0, 12).map((trace) => (
      <p key={`${trace.rule_id}-${trace.line_code}`}>
        {trace.line_code}：{trace.formula}，来源科目 {trace.source_account_codes.join(" / ") || "公式或现金流项目"}
      </p>
    ))}
  </div>
</section>
```

Place it after the management summary panel so the operational view remains compact.

- [ ] **Step 6: Wire layout and package tests**

In `frontend/src/components/DashboardLayout.tsx`, render `StatementMappingPanel` near `FinancialStatementPanel`.

In `frontend/package.json`, append:

```json
"node tests/statementMappingApi.test.mjs && node tests/statementMappingPanel.test.mjs"
```

to the existing `test:nav` command.

- [ ] **Step 7: Verify and commit**

```powershell
npm --prefix frontend test
npm --prefix frontend run build
git add frontend/src/types/statementMapping.ts frontend/src/types/financialStatement.ts frontend/src/services/dashboardApi.ts frontend/src/components/StatementMappingPanel.tsx frontend/src/components/FinancialStatementPanel.tsx frontend/src/components/DashboardLayout.tsx frontend/tests/statementMappingApi.test.mjs frontend/tests/statementMappingPanel.test.mjs frontend/tests/financialStatementPanel.test.mjs frontend/package.json
git commit -m "feat: add statement mapping frontend"
```

## Task 7: 文档、回归验证与集成检查

**Files:**
- Modify: `README.md`
- Modify: `docs/01-mvp-design.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

- [ ] **Step 1: Document statement mapping workflow**

Update docs with:
- 默认报表映射集和适用范围
- 资产负债表期末余额取数规则
- 利润表期间发生额取数规则
- 现金流量表现金流项目取数和推断规则
- 所有者权益变动表期初、净利润、利润分配和期末权益取数规则
- 生成追溯字段
- 报表公式校验项
- 权限和审计事件

- [ ] **Step 2: Document API changes**

In `docs/02-api-design.md`, add:

```markdown
GET /api/v1/financial-statements/mapping-sets/default?account_set_id=default
POST /api/v1/financial-statements/generate

`generate` 响应新增：
- `mapping_set_id`
- `trace_items`
- `validation_items`
```

Permissions:
- `statement.generate`
- `statement.validate`
- `statement.mapping.view`
- `statement.mapping.manage`

- [ ] **Step 3: Run backend regression**

```powershell
python -m pytest backend/tests/test_statement_mapping_service.py backend/tests/test_financial_statement_service.py backend/tests/test_financial_statement_api.py backend/tests/test_accounting_service.py backend/tests/test_system_admin_api.py
```

Expected result: all selected backend tests pass.

- [ ] **Step 4: Run frontend regression and build**

```powershell
npm --prefix frontend test
npm --prefix frontend run build
```

Expected result: frontend tests and production build pass. Existing Vite chunk-size warnings are acceptable only when the build exits with code 0.

- [ ] **Step 5: Manual verification scenario**

Manual scenario:
1. Generate default statement mapping set for account set `default`.
2. Post formal revenue, cost, payroll payment and tax payment entries.
3. Mark at least one cash line with `cash_flow_item_code`.
4. Generate statements for `2026-06`.
5. Confirm balance sheet and income statement lines use mapping rules rather than hard-coded service prefixes.
6. Confirm cash flow statement includes explicit cash flow item and inferred warning for unmarked cash movement.
7. Confirm `trace_items` list source accounts and formulas.
8. Confirm `validation_items` includes balance sheet identity result.
9. Open the frontend statement panel and verify trace/validation text does not overlap table content.

- [ ] **Step 6: Final docs commit**

```powershell
git add README.md docs/01-mvp-design.md docs/02-api-design.md docs/03-frd-v1.0.md
git commit -m "docs: document statement mapping workflow"
```

## Acceptance Criteria

- Default mapping set covers balance sheet, income statement, cash flow statement and equity statement.
- Financial statement generation returns `mapping_set_id`, `trace_items` and `validation_items`.
- Balance sheet and income statement amounts are computed from mapping rules, not hard-coded prefixes in `financial_statement_service.py`.
- Cash flow statement supports explicit `cash_flow_item_code` and deterministic account-pair inference.
- Balance sheet identity validation returns `passed` or `failed` as structured data.
- Sample data fallback remains available for demo-only workspaces and is marked with a warning validation item.
- Mapping view API is protected by `statement.mapping.view`.
- Mapping update permission exists as `statement.mapping.manage`.
- Frontend exposes mapping rules and report trace without hiding core report tables.
- Documentation states mapping rules, permissions, audit events and verification commands.

## Risk Controls

- Use `Decimal` for every mapped amount and formula result.
- Keep formula evaluation limited to report line codes plus `+` and `-`; do not use `eval`.
- Keep default mapping deterministic and versionable through `mapping_set_id`.
- Treat inferred cash flow items as warnings so accountants can review untagged cash movements.
- Do not mutate formal journal entries during report generation.
- Preserve existing `POST /api/v1/financial-statements/generate` compatibility while adding trace fields.
- Run backend and frontend regression commands before merging implementation work.
