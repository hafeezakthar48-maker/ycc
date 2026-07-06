# 正式核算引擎十五期 合并报表与内部往来抵销 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立多账套合并报表、内部往来匹配、内部交易抵销和合并工作底稿能力。  
**Architecture:** 新增 `consolidation` 模型和服务，单体账套继续由正式核算引擎生成报表，合并层读取各账套正式报表和科目余额，按合并范围、持股比例和抵销规则生成合并工作底稿。抵销分录只存在于合并层，不回写单体账套正式分录。  
**Tech Stack:** FastAPI、Pydantic、SQLite、Decimal、pytest、React、TypeScript、Vite、Node test runner。

---

## 前置条件

- 一期正式分录和账套隔离可稳定提供单体账务事实。
- 五期正式报表映射可生成资产负债表、利润表和现金流量表。
- 八期应收应付可按客户、供应商和关联方维度出具往来余额。
- 十二期存货成本可识别内部采购销售的库存影响。
- 十三期税务核算能保持单体税务口径独立。

本期不做复杂股权购买法追溯、不做商誉减值完整评估模型、不做境外准则转换、不替代审计合并底稿。

## 核算决策

- 合并层不修改单体账套正式分录。
- 合并工作底稿由单体报表、抵销分录和合并调整组成。
- 内部往来抵销以关联方辅助维度匹配应收、应付、其他应收和其他应付。
- 内部销售抵销包括收入、成本和未实现内部利润；存货未实现利润按期末内部采购库存余额计算。
- 投资与权益抵销本期支持全资子公司和按持股比例合并的简单场景。
- 少数股东权益和少数股东损益按配置持股比例计算。
- 合并期间关闭后不能新增抵销分录，可以查询历史合并底稿。

## 文件结构

- Create: `backend/app/models/consolidation.py`
- Create: `backend/app/services/consolidation_service.py`
- Create: `backend/app/api/consolidation.py`
- Modify: `backend/app/services/financial_statement_service.py`
- Modify: `backend/app/services/receivable_payable_service.py`
- Modify: `backend/app/services/inventory_accounting_service.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Modify: `backend/app/api/router_registry.py`
- Create: `backend/tests/test_consolidation_service.py`
- Create: `backend/tests/test_consolidation_api.py`
- Create: `frontend/src/types/consolidation.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/ConsolidationPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Create: `frontend/tests/consolidationApi.test.mjs`
- Create: `frontend/tests/consolidationPanel.test.mjs`
- Modify: `README.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

## Task 1: 合并范围与持股模型

**Files:**
- Create: `backend/app/models/consolidation.py`
- Test: `backend/tests/test_consolidation_service.py`

- [ ] **Step 1: Write failing model test**

```python
from decimal import Decimal

from app.models.consolidation import ConsolidationEntity


def test_consolidation_entity_records_ownership_percentage():
    entity = ConsolidationEntity(
        consolidation_group_id="group-001",
        account_set_id="subsidiary-a",
        entity_name="子公司A",
        ownership_percentage=Decimal("0.80"),
        consolidation_method="proportionate",
    )

    assert entity.ownership_percentage == Decimal("0.80")
```

- [ ] **Step 2: Run failing test**

```powershell
python -m pytest backend/tests/test_consolidation_service.py::test_consolidation_entity_records_ownership_percentage -v
```

Expected result: fails because consolidation models do not exist.

- [ ] **Step 3: Create models**

```python
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


ConsolidationMethod = Literal["full", "proportionate", "equity_method"]
EliminationType = Literal["intercompany_balance", "intercompany_revenue_cost", "investment_equity", "unrealized_profit"]


class ConsolidationEntity(BaseModel):
    consolidation_group_id: str
    account_set_id: str
    entity_name: str
    ownership_percentage: Decimal = Field(gt=Decimal("0"), le=Decimal("1"))
    consolidation_method: ConsolidationMethod = "full"


class ConsolidationEliminationEntry(BaseModel):
    elimination_id: str
    group_id: str
    period: str
    elimination_type: EliminationType
    debit_account_code: str
    credit_account_code: str
    amount: Decimal
    explanation: str
```

- [ ] **Step 4: Run model test**

```powershell
python -m pytest backend/tests/test_consolidation_service.py::test_consolidation_entity_records_ownership_percentage -v
```

Expected result: test passes.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/models/consolidation.py backend/tests/test_consolidation_service.py
git commit -m "feat: add consolidation group models"
```

## Task 2: 单体报表包读取

**Files:**
- Create: `backend/app/services/consolidation_service.py`
- Modify: `backend/app/services/financial_statement_service.py`
- Test: `backend/tests/test_consolidation_service.py`

- [ ] **Step 1: Add failing package test**

```python
from app.services.consolidation_service import build_reporting_package


def test_build_reporting_package_reads_balance_and_income_statement():
    package = build_reporting_package("default", "2026-06")

    assert package.account_set_id == "default"
    assert package.period == "2026-06"
    assert package.balance_sheet is not None
    assert package.income_statement is not None
```

- [ ] **Step 2: Implement reporting package**

```python
def build_reporting_package(account_set_id: str, period: str):
    balance_sheet = generate_financial_statement(account_set_id, period, "balance_sheet")
    income_statement = generate_financial_statement(account_set_id, period, "income_statement")
    cash_flow_statement = generate_financial_statement(account_set_id, period, "cash_flow_statement")
    return type(
        "ReportingPackage",
        (),
        {
            "account_set_id": account_set_id,
            "period": period,
            "balance_sheet": balance_sheet,
            "income_statement": income_statement,
            "cash_flow_statement": cash_flow_statement,
        },
    )()
```

- [ ] **Step 3: Run package test**

```powershell
python -m pytest backend/tests/test_consolidation_service.py::test_build_reporting_package_reads_balance_and_income_statement -v
```

Expected result: reporting package includes three core statements.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/services/consolidation_service.py backend/app/services/financial_statement_service.py backend/tests/test_consolidation_service.py
git commit -m "feat: build consolidation reporting packages"
```

## Task 3: 内部往来匹配与抵销

**Files:**
- Modify: `backend/app/services/consolidation_service.py`
- Modify: `backend/app/services/receivable_payable_service.py`
- Test: `backend/tests/test_consolidation_service.py`

- [ ] **Step 1: Add failing balance elimination test**

```python
from decimal import Decimal

from app.services.consolidation_service import build_intercompany_balance_elimination


def test_build_intercompany_balance_elimination_offsets_ar_and_ap():
    entry = build_intercompany_balance_elimination(
        group_id="group-001",
        period="2026-06",
        receivable_account_code="1122",
        payable_account_code="2202",
        amount=Decimal("50000.00"),
    )

    assert entry.elimination_type == "intercompany_balance"
    assert entry.amount == Decimal("50000.00")
```

- [ ] **Step 2: Implement elimination entry**

```python
def build_intercompany_balance_elimination(group_id: str, period: str, receivable_account_code: str, payable_account_code: str, amount: Decimal):
    return ConsolidationEliminationEntry(
        elimination_id=f"elim-{group_id}-{period}-balance",
        group_id=group_id,
        period=period,
        elimination_type="intercompany_balance",
        debit_account_code=payable_account_code,
        credit_account_code=receivable_account_code,
        amount=amount,
        explanation="抵销内部应收应付",
    )
```

- [ ] **Step 3: Run balance elimination tests**

```powershell
python -m pytest backend/tests/test_consolidation_service.py -v
```

Expected result: internal AR/AP elimination entry is generated.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/services/consolidation_service.py backend/app/services/receivable_payable_service.py backend/tests/test_consolidation_service.py
git commit -m "feat: eliminate intercompany balances"
```

## Task 4: 内部交易和未实现利润抵销

**Files:**
- Modify: `backend/app/services/consolidation_service.py`
- Modify: `backend/app/services/inventory_accounting_service.py`
- Test: `backend/tests/test_consolidation_service.py`

- [ ] **Step 1: Add failing unrealized profit test**

```python
from decimal import Decimal

from app.services.consolidation_service import calculate_unrealized_inventory_profit


def test_calculate_unrealized_inventory_profit_uses_margin_rate():
    result = calculate_unrealized_inventory_profit(
        ending_internal_inventory_amount=Decimal("100000.00"),
        internal_gross_margin_rate=Decimal("0.20"),
    )

    assert result == Decimal("20000.00")
```

- [ ] **Step 2: Implement unrealized profit calculation**

```python
def calculate_unrealized_inventory_profit(ending_internal_inventory_amount: Decimal, internal_gross_margin_rate: Decimal) -> Decimal:
    return (ending_internal_inventory_amount * internal_gross_margin_rate).quantize(Decimal("0.01"))
```

- [ ] **Step 3: Implement revenue cost elimination**

```python
def build_intercompany_revenue_cost_elimination(group_id: str, period: str, revenue_amount: Decimal, cost_amount: Decimal):
    return [
        ConsolidationEliminationEntry(
            elimination_id=f"elim-{group_id}-{period}-revenue",
            group_id=group_id,
            period=period,
            elimination_type="intercompany_revenue_cost",
            debit_account_code="6001",
            credit_account_code="6401",
            amount=min(revenue_amount, cost_amount),
            explanation="抵销内部销售收入与成本",
        )
    ]
```

- [ ] **Step 4: Run transaction elimination tests**

```powershell
python -m pytest backend/tests/test_consolidation_service.py -v
```

Expected result: internal transaction and unrealized profit tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/consolidation_service.py backend/app/services/inventory_accounting_service.py backend/tests/test_consolidation_service.py
git commit -m "feat: eliminate intercompany transactions"
```

## Task 5: 投资权益抵销和少数股东权益

**Files:**
- Modify: `backend/app/services/consolidation_service.py`
- Test: `backend/tests/test_consolidation_service.py`

- [ ] **Step 1: Add failing minority interest test**

```python
from decimal import Decimal

from app.services.consolidation_service import calculate_minority_interest


def test_calculate_minority_interest_from_ownership():
    result = calculate_minority_interest(
        subsidiary_net_assets=Decimal("1000000.00"),
        ownership_percentage=Decimal("0.80"),
    )

    assert result == Decimal("200000.00")
```

- [ ] **Step 2: Implement minority interest calculation**

```python
def calculate_minority_interest(subsidiary_net_assets: Decimal, ownership_percentage: Decimal) -> Decimal:
    minority_percentage = Decimal("1") - ownership_percentage
    return (subsidiary_net_assets * minority_percentage).quantize(Decimal("0.01"))
```

- [ ] **Step 3: Implement investment equity elimination**

抵销规则：
- 借记子公司实收资本、资本公积、盈余公积、未分配利润。
- 贷记母公司长期股权投资。
- 差额按配置进入商誉或合并价差项目。
- 少数股东权益单独列示。

- [ ] **Step 4: Run equity tests**

```powershell
python -m pytest backend/tests/test_consolidation_service.py -v
```

Expected result: investment equity and minority interest calculations pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/consolidation_service.py backend/tests/test_consolidation_service.py
git commit -m "feat: eliminate investment against equity"
```

## Task 6: API、前端和文档

**Files:**
- Create: `backend/app/api/consolidation.py`
- Modify: `backend/app/api/router_registry.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Create: `backend/tests/test_consolidation_api.py`
- Create: `frontend/src/types/consolidation.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/ConsolidationPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Create: `frontend/tests/consolidationApi.test.mjs`
- Create: `frontend/tests/consolidationPanel.test.mjs`
- Modify: `README.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

- [ ] **Step 1: Implement endpoints**

Endpoints:
- `GET /api/v1/consolidation/groups`
- `POST /api/v1/consolidation/groups`
- `GET /api/v1/consolidation/reporting-package`
- `GET /api/v1/consolidation/eliminations`
- `POST /api/v1/consolidation/eliminations/rebuild`
- `GET /api/v1/consolidation/statements`

Permissions:
- `consolidation.read`
- `consolidation.write`
- `consolidation.rebuild`

Audit events:
- `consolidation.group.read`
- `consolidation.group.write`
- `consolidation.package.read`
- `consolidation.elimination.rebuild`
- `consolidation.statement.read`

- [ ] **Step 2: Build consolidation panel**

Panel must show:
- 合并范围。
- 单体报表包状态。
- 内部往来匹配差异。
- 抵销分录列表。
- 合并资产负债表、利润表和现金流量表。
- 少数股东权益和少数股东损益。

- [ ] **Step 3: Run regression**

```powershell
python -m pytest backend/tests/test_consolidation_service.py backend/tests/test_consolidation_api.py backend/tests/test_financial_statement_service.py backend/tests/test_receivable_payable_service.py
npm --prefix frontend test
npm --prefix frontend run build
```

Expected result: selected backend tests, frontend tests and build pass.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/api/consolidation.py backend/app/api/router_registry.py backend/app/services/system_admin_service.py backend/app/services/module_registry_service.py backend/tests/test_consolidation_api.py frontend/src/types/consolidation.ts frontend/src/services/dashboardApi.ts frontend/src/components/ConsolidationPanel.tsx frontend/src/components/DashboardLayout.tsx frontend/tests/consolidationApi.test.mjs frontend/tests/consolidationPanel.test.mjs README.md docs/02-api-design.md docs/03-frd-v1.0.md
git commit -m "feat: expose consolidation workflow"
```

## 验收标准

- 可维护合并集团、账套范围和持股比例。
- 可读取各账套单体报表包。
- 可生成内部应收应付抵销。
- 可生成内部销售成本和未实现利润抵销。
- 可计算投资权益抵销和少数股东权益。
- 合并层抵销不回写单体账套。
- 前端可展示合并范围、抵销底稿和合并报表。

## 风险控制

- 合并抵销只存在于合并工作底稿。
- 合并报表必须保留单体来源、抵销来源和计算公式。
- 持股比例、合并方法和抵销规则必须记录审计日志。
- 复杂商誉、购买日公允价值和境外准则转换明确不在本期范围。
- 金额计算统一使用 `Decimal`。
