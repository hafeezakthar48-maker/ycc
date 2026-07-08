# 正式核算引擎十四期 预提摊销与融资利息核算 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立预付摊销、待摊费用、预提费用、递延收入和借款利息的正式月结核算能力。
**Architecture:** 新增 `accrual_amortization` 领域模型和服务，以核算计划表驱动每月自动分录。每个计划生成的分录使用账套、期间和计划编号作为幂等 source key，月结服务统一调度，人工可暂停、终止或调整计划。
**Tech Stack:** FastAPI、Pydantic、SQLite、Decimal、pytest、React、TypeScript、Vite、Node test runner。

---

## 前置条件

- 一期正式分录服务支持幂等 source key。
- 三期辅助核算支持部门、项目、合同和供应商维度。
- 四期期末处理可注册月结动作。
- 九期银行资金模块可记录借款到账、还本付息和手续费付款。

本期不做复杂金融工具公允价值计量，不做实际利率摊余成本完整模型，不做租赁准则全流程，不做合同收入五步法自动判断。

## 核算决策

- 预付费用初始入账借记 `1801 长期待摊费用` 或 `1123 预付账款`，月度摊销借记费用，贷记待摊科目。
- 预提费用月末借记费用，贷记 `2241 其他应付款` 或配置负债科目；实际支付时借记负债，贷记银行存款。
- 递延收入收款时贷记 `2203 预收账款` 或 `2401 递延收益`，确认收入时借记递延科目，贷记收入科目。
- 借款到账借记银行存款，贷记 `2001 短期借款` 或 `2501 长期借款`。
- 借款利息计提借记 `6603 财务费用` 或在建工程等配置科目，贷记 `2231 应付利息`。
- 还本付息借记借款本金和应付利息，贷记银行存款。
- 已关闭期间不能生成、调整或冲销本期计划分录。

## 文件结构

- Create: `backend/app/models/accrual_amortization.py`
- Create: `backend/app/services/accrual_amortization_service.py`
- Create: `backend/app/api/accrual_amortization.py`
- Modify: `backend/app/services/period_close_service.py`
- Modify: `backend/app/services/accounting_service.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Modify: `backend/app/api/router_registry.py`
- Create: `backend/tests/test_accrual_amortization_service.py`
- Create: `backend/tests/test_accrual_amortization_api.py`
- Modify: `backend/tests/test_period_close_service.py`
- Create: `frontend/src/types/accrualAmortization.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/AccrualAmortizationPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Create: `frontend/tests/accrualAmortizationApi.test.mjs`
- Create: `frontend/tests/accrualAmortizationPanel.test.mjs`
- Modify: `README.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

## Task 1: 核算计划模型

**Files:**
- Create: `backend/app/models/accrual_amortization.py`
- Test: `backend/tests/test_accrual_amortization_service.py`

- [ ] **Step 1: Write failing schedule model test**

```python
from decimal import Decimal

from app.models.accrual_amortization import AccountingScheduleCreate


def test_accounting_schedule_has_total_amount_and_months():
    schedule = AccountingScheduleCreate(
        account_set_id="default",
        schedule_code="AMORT-2026-001",
        schedule_type="prepaid_amortization",
        start_period="2026-01",
        end_period="2026-12",
        total_amount=Decimal("12000.00"),
        debit_account_code="6602",
        credit_account_code="1801",
        department_id="dept-admin",
    )

    assert schedule.total_amount == Decimal("12000.00")
```

- [ ] **Step 2: Run failing test**

```powershell
python -m pytest backend/tests/test_accrual_amortization_service.py::test_accounting_schedule_has_total_amount_and_months -v
```

Expected result: fails because accrual amortization models do not exist.

- [ ] **Step 3: Create models**

```python
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


ScheduleType = Literal["prepaid_amortization", "accrued_expense", "deferred_revenue", "loan_interest"]
ScheduleStatus = Literal["active", "paused", "completed", "terminated"]


class AccountingScheduleCreate(BaseModel):
    account_set_id: str
    schedule_code: str
    schedule_type: ScheduleType
    start_period: str
    end_period: str
    total_amount: Decimal = Field(gt=Decimal("0"))
    debit_account_code: str
    credit_account_code: str
    department_id: str | None = None
    project_id: str | None = None


class AccountingSchedule(AccountingScheduleCreate):
    status: ScheduleStatus = "active"
    posted_periods: list[str] = []
```

- [ ] **Step 4: Run model test**

```powershell
python -m pytest backend/tests/test_accrual_amortization_service.py::test_accounting_schedule_has_total_amount_and_months -v
```

Expected result: test passes.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/models/accrual_amortization.py backend/tests/test_accrual_amortization_service.py
git commit -m "feat: add accrual amortization schedules"
```

## Task 2: 月度摊销金额计算

**Files:**
- Create: `backend/app/services/accrual_amortization_service.py`
- Test: `backend/tests/test_accrual_amortization_service.py`

- [ ] **Step 1: Add failing monthly amount test**

```python
from decimal import Decimal

from app.services.accrual_amortization_service import calculate_even_monthly_amount


def test_calculate_even_monthly_amount_rounds_to_cents():
    result = calculate_even_monthly_amount(Decimal("10000.00"), 3)

    assert result == [Decimal("3333.33"), Decimal("3333.33"), Decimal("3333.34")]
```

- [ ] **Step 2: Implement rounding distribution**

```python
from decimal import Decimal


def calculate_even_monthly_amount(total_amount: Decimal, months: int) -> list[Decimal]:
    base = (total_amount / Decimal(months)).quantize(Decimal("0.01"))
    amounts = [base for _ in range(months)]
    difference = total_amount - sum(amounts)
    amounts[-1] = (amounts[-1] + difference).quantize(Decimal("0.01"))
    return amounts
```

- [ ] **Step 3: Run monthly amount test**

```powershell
python -m pytest backend/tests/test_accrual_amortization_service.py::test_calculate_even_monthly_amount_rounds_to_cents -v
```

Expected result: last month absorbs rounding difference.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/services/accrual_amortization_service.py backend/tests/test_accrual_amortization_service.py
git commit -m "feat: calculate monthly amortization amounts"
```

## Task 3: 预付摊销与预提费用分录

**Files:**
- Modify: `backend/app/services/accrual_amortization_service.py`
- Modify: `backend/app/services/period_close_service.py`
- Test: `backend/tests/test_accrual_amortization_service.py`

- [ ] **Step 1: Add failing schedule posting test**

```python
from app.services.accrual_amortization_service import post_schedule_for_period


def test_post_prepaid_amortization_for_period_uses_schedule_source_key():
    entry = post_schedule_for_period("default", "AMORT-2026-001", "2026-06", "close-user")

    assert entry.source_id == "schedule_posting:default:2026-06:AMORT-2026-001"
```

- [ ] **Step 2: Implement posting**

```python
def post_schedule_for_period(account_set_id: str, schedule_code: str, period: str, actor_id: str):
    schedule = get_accounting_schedule(account_set_id, schedule_code)
    amount = get_schedule_amount_for_period(schedule, period)
    source_id = f"schedule_posting:{account_set_id}:{period}:{schedule_code}"
    return create_journal_entry(
        account_set_id=account_set_id,
        period=period,
        entry_date=f"{period}-28",
        source_type=schedule.schedule_type,
        source_id=source_id,
        lines=[
            {"account_code": schedule.debit_account_code, "debit": amount, "credit": Decimal("0.00")},
            {"account_code": schedule.credit_account_code, "debit": Decimal("0.00"), "credit": amount},
        ],
        created_by=actor_id,
    )
```

- [ ] **Step 3: Run schedule posting tests**

```powershell
python -m pytest backend/tests/test_accrual_amortization_service.py backend/tests/test_period_close_service.py -v
```

Expected result: schedule posting is idempotent and balanced.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/services/accrual_amortization_service.py backend/app/services/period_close_service.py backend/tests/test_accrual_amortization_service.py backend/tests/test_period_close_service.py
git commit -m "feat: post accrual and amortization schedules"
```

## Task 4: 借款和利息核算

**Files:**
- Modify: `backend/app/models/accrual_amortization.py`
- Modify: `backend/app/services/accrual_amortization_service.py`
- Test: `backend/tests/test_accrual_amortization_service.py`

- [ ] **Step 1: Add failing loan interest test**

```python
from decimal import Decimal

from app.services.accrual_amortization_service import calculate_monthly_interest


def test_calculate_monthly_interest_uses_annual_rate():
    amount = calculate_monthly_interest(Decimal("1000000.00"), Decimal("0.036"))

    assert amount == Decimal("3000.00")
```

- [ ] **Step 2: Implement interest calculation**

```python
def calculate_monthly_interest(principal: Decimal, annual_rate: Decimal) -> Decimal:
    return (principal * annual_rate / Decimal("12")).quantize(Decimal("0.01"))
```

- [ ] **Step 3: Implement loan interest accrual entry**

```python
def post_loan_interest_accrual(account_set_id: str, loan_code: str, period: str, actor_id: str):
    loan = get_loan_schedule(account_set_id, loan_code)
    interest = calculate_monthly_interest(loan.principal, loan.annual_rate)
    source_id = f"loan_interest_accrual:{account_set_id}:{period}:{loan_code}"
    return create_journal_entry(
        account_set_id=account_set_id,
        period=period,
        entry_date=f"{period}-28",
        source_type="loan_interest_accrual",
        source_id=source_id,
        lines=[
            {"account_code": "6603", "debit": interest, "credit": Decimal("0.00")},
            {"account_code": "2231", "debit": Decimal("0.00"), "credit": interest},
        ],
        created_by=actor_id,
    )
```

- [ ] **Step 4: Run loan tests**

```powershell
python -m pytest backend/tests/test_accrual_amortization_service.py -v
```

Expected result: loan interest accrual tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/models/accrual_amortization.py backend/app/services/accrual_amortization_service.py backend/tests/test_accrual_amortization_service.py
git commit -m "feat: accrue loan interest"
```

## Task 5: API、权限与审计

**Files:**
- Create: `backend/app/api/accrual_amortization.py`
- Modify: `backend/app/api/router_registry.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Create: `backend/tests/test_accrual_amortization_api.py`

- [ ] **Step 1: Implement endpoints**

Endpoints:
- `GET /api/v1/accrual-amortization/schedules`
- `POST /api/v1/accrual-amortization/schedules`
- `POST /api/v1/accrual-amortization/schedules/{schedule_code}/post`
- `POST /api/v1/accrual-amortization/loan-interest`

Permissions:
- `accrual_amortization.read`
- `accrual_amortization.write`
- `accrual_amortization.post`

Audit events:
- `accrual_amortization.schedule.read`
- `accrual_amortization.schedule.create`
- `accrual_amortization.schedule.post`
- `accrual_amortization.loan_interest.post`

- [ ] **Step 2: Run API tests**

```powershell
python -m pytest backend/tests/test_accrual_amortization_api.py backend/tests/test_system_admin_api.py backend/tests/test_module_registry_api.py -v
```

Expected result: selected backend tests pass.

- [ ] **Step 3: Commit**

```powershell
git add backend/app/api/accrual_amortization.py backend/app/api/router_registry.py backend/app/services/system_admin_service.py backend/app/services/module_registry_service.py backend/tests/test_accrual_amortization_api.py
git commit -m "feat: expose accrual amortization api"
```

## Task 6: 前端面板和文档

**Files:**
- Create: `frontend/src/types/accrualAmortization.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/AccrualAmortizationPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Create: `frontend/tests/accrualAmortizationApi.test.mjs`
- Create: `frontend/tests/accrualAmortizationPanel.test.mjs`
- Modify: `README.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

- [ ] **Step 1: Build panel**

Panel must show:
- 计划编号、类型、起止期间和总金额。
- 本期应摊销或应计提金额。
- 已生成分录期间。
- 暂停、终止和本期生成状态。
- 借款本金、年利率、本期利息和还款状态。

- [ ] **Step 2: Run regression**

```powershell
python -m pytest backend/tests/test_accrual_amortization_service.py backend/tests/test_accrual_amortization_api.py backend/tests/test_period_close_service.py
npm --prefix frontend test
npm --prefix frontend run build
```

Expected result: selected backend tests, frontend tests and build pass.

- [ ] **Step 3: Commit**

```powershell
git add frontend/src/types/accrualAmortization.ts frontend/src/services/dashboardApi.ts frontend/src/components/AccrualAmortizationPanel.tsx frontend/src/components/DashboardLayout.tsx frontend/tests/accrualAmortizationApi.test.mjs frontend/tests/accrualAmortizationPanel.test.mjs README.md docs/02-api-design.md docs/03-frd-v1.0.md
git commit -m "feat: add accrual amortization panel"
```

## 验收标准

- 预付摊销、预提费用、递延收入和借款利息计划可创建。
- 月度金额能正确分摊并处理尾差。
- 月结可按计划生成幂等正式分录。
- 借款利息可按本金和年利率计提。
- 前端可查看计划、生成状态和分录号。
- 已关闭期间拒绝新增或调整本期计划分录。

## 风险控制

- 计划调整不改历史分录，改用新计划或调整分录。
- 每个计划每期只允许一个 source key。
- 尾差集中在最后一期并保留计算记录。
- 借款利息只做直线月利息，本期不承诺复杂金融工具计量。
- 所有金额使用 `Decimal`。
