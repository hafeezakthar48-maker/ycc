# Formal Accounting Engine Phase 4 Period Close Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在正式核算一至三期基础上，建立月末期末处理与结账引擎，支持结账检查、固定资产折旧、工资计提、税费计提、外币期末重估、损益结转、期间关闭与重开审计。
**Architecture:** 新增 `period_close` 领域模型与服务层，所有期末结果都以正式分录写入，不直接改写历史分录。`close_accounting_period` 从单纯改期间状态升级为“检查清单通过 + 期末分录生成 + 关闭审计记录”的编排流程；每类期末动作使用稳定的 `source_type` / `source_id` 实现幂等。
**Tech Stack:** FastAPI、Pydantic、SQLite、Decimal、pytest、React、TypeScript、Vite、Node test runner。
---

## Prerequisite

必须先完成并验证：
- `docs/superpowers/plans/2026-07-06-formal-accounting-engine-phase-1.md`
- `docs/superpowers/plans/2026-07-06-formal-accounting-engine-phase-2-multi-currency.md`
- `docs/superpowers/plans/2026-07-06-formal-accounting-engine-phase-3-auxiliary-dimensions.md`
- 后端已有正式分录写入、查询、不可变控制与账簿读取能力
- 后端已有期间状态模型与 `/periods/{period}/close`、`/periods/{period}/reopen` 接口
- 后端已有固定资产折旧与工资计算的 MVP 服务
- 多币种分录已有 `currency`、`original_amount`、`exchange_rate`、`base_amount` 字段

本期不实现正式纳税申报、银行代发、完整应收应付账龄、电子档案归档、复杂成本结转、跨账套合并报表。本期目标是把月结所需的正式核算底座做实，并让后续专业模块能挂接到同一套结账流程。

## Accounting Decisions

- 期间关闭前必须执行检查清单。检查清单失败时不能关闭期间。
- 期末分录必须写入正式分录表，不能写入临时账簿缓存。
- 期末分录必须带有 `source_type`、`source_id`、`period`、`account_set_id` 与 `generated_by`，便于审计和幂等。
- 同一账套、同一期间、同一 `source_type` 的期末动作重复执行时，默认返回已有运行结果；显式 `force_regenerate` 只允许在期间未关闭时执行。
- 期间关闭后禁止新增、修改或删除该期间正式分录。期间重开只改变期间状态并记录审计事件，不删除已经生成的期末分录。
- 月末损益结转只结转收入、成本、费用、税金及附加、营业外收支、所得税费用到 `4103 本年利润`。年结把 `4103 本年利润` 转入 `4104 利润分配-未分配利润`。
- 外币期末重估只对期末仍有外币余额的科目生成本位币调整分录，原币余额不变，汇兑损益计入 `6603 财务费用` 的明细方向。
- 税费计提采用 MVP 规则输入，不替代正式纳税申报。规则结果生成 `2221 应交税费` 相关分录，并保留计算依据。

## File Structure

- Create: `backend/app/models/period_close.py`
  - 定义期末运行、检查项、期末动作、税费计提规则、重估结果与结账响应模型。
- Create: `backend/app/services/period_close_service.py`
  - 编排结账检查、期末分录生成、关闭与重开审计。
- Create: `backend/app/api/period_close.py`
  - 提供检查、预览、生成、关闭、重开、查询运行记录 API。
- Modify: `backend/app/api/router_registry.py`
  - 注册期末处理 API。
- Modify: `backend/app/services/accounting_period_service.py`
  - 将期间关闭/重开委托给期末处理服务，增加关闭守卫。
- Modify: `backend/app/services/accounting_service.py`
  - 支持期末分录幂等来源键，禁止关闭期间写入，支持按 `source_type` 查询。
- Modify: `backend/app/services/fixed_asset_service.py`
  - 暴露折旧计提摘要，供期末服务生成正式分录。
- Modify: `backend/app/services/payroll_service.py`
  - 暴露工资计提摘要，供期末服务生成正式分录。
- Modify: `backend/app/services/system_admin_service.py`
  - 增加期末处理查看、执行、重开权限。
- Modify: `backend/app/services/module_registry_service.py`
  - 注册期末处理模块、权限与审计事件。
- Create: `backend/tests/test_period_close_service.py`
- Create: `backend/tests/test_period_close_api.py`
- Modify: `backend/tests/test_accounting_period_service.py`
- Modify: `backend/tests/test_accounting_service.py`
- Modify: `backend/tests/test_fixed_asset_service.py`
- Modify: `backend/tests/test_payroll_service.py`
- Create: `frontend/src/types/periodClose.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/PeriodClosePanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Create: `frontend/tests/periodCloseApi.test.mjs`
- Create: `frontend/tests/periodClosePanel.test.mjs`
- Modify: `README.md`
- Modify: `docs/01-mvp-design.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

## Task 1: 期末处理模型与运行记录

**Files:**
- Create: `backend/app/models/period_close.py`
- Create: `backend/app/services/period_close_service.py`
- Create: `backend/tests/test_period_close_service.py`

- [ ] **Step 1: Write failing period-close run tests**

Create `backend/tests/test_period_close_service.py`:

```python
from app.models.period_close import PeriodCloseRunCreate
from app.services.period_close_service import (
    get_period_close_run,
    list_period_close_runs,
    reset_period_close_store,
    start_period_close_run,
)


def setup_function():
    reset_period_close_store()


def test_start_period_close_run_records_scope_and_status():
    run = start_period_close_run(
        PeriodCloseRunCreate(
            account_set_id="default",
            period="2026-06",
            close_type="month",
            requested_by="finance-user",
        )
    )

    loaded = get_period_close_run(run.run_id)
    listed = list_period_close_runs("default", period="2026-06")

    assert run.status == "draft"
    assert loaded.account_set_id == "default"
    assert listed.total == 1
```

- [ ] **Step 2: Implement period-close models**

Create `backend/app/models/period_close.py`:

```python
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


PeriodCloseStatus = Literal["draft", "checking", "ready", "generated", "closed", "reopened", "failed"]
PeriodCloseType = Literal["month", "year"]
PeriodCloseActionType = Literal[
    "fixed_asset_depreciation",
    "payroll_accrual",
    "tax_accrual",
    "fx_revaluation",
    "profit_loss_carryforward",
    "year_end_profit_distribution",
]


class PeriodCloseRunCreate(BaseModel):
    account_set_id: str = "default"
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    close_type: PeriodCloseType = "month"
    requested_by: str


class PeriodCloseRun(BaseModel):
    run_id: str
    account_set_id: str
    period: str
    close_type: PeriodCloseType
    status: PeriodCloseStatus
    requested_by: str
    created_at: str
    updated_at: str
    closed_at: str | None = None
    reopened_at: str | None = None


class PeriodCloseCheckItem(BaseModel):
    check_code: str
    check_name: str
    status: Literal["passed", "failed", "warning"]
    severity: Literal["blocker", "warning"]
    message: str
    evidence: dict[str, str | int | Decimal] = {}


class PeriodCloseActionResult(BaseModel):
    action_type: PeriodCloseActionType
    status: Literal["skipped", "generated", "existing", "failed"]
    journal_entry_ids: list[str] = []
    amount: Decimal = Decimal("0")
    message: str
```

- [ ] **Step 3: Implement in-memory store first, keep persistence shape explicit**

In `backend/app/services/period_close_service.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.models.period_close import PeriodCloseRun, PeriodCloseRunCreate

_PERIOD_CLOSE_RUNS: dict[str, PeriodCloseRun] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def reset_period_close_store() -> None:
    _PERIOD_CLOSE_RUNS.clear()


def start_period_close_run(payload: PeriodCloseRunCreate) -> PeriodCloseRun:
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
```

- [ ] **Step 4: Run backend tests and commit**

```powershell
python -m pytest backend/tests/test_period_close_service.py
git add backend/app/models/period_close.py backend/app/services/period_close_service.py backend/tests/test_period_close_service.py
git commit -m "feat: add period close run model"
```

## Task 2: 结账检查清单与关闭前守卫

**Files:**
- Modify: `backend/app/services/period_close_service.py`
- Modify: `backend/app/services/accounting_period_service.py`
- Modify: `backend/tests/test_period_close_service.py`
- Modify: `backend/tests/test_accounting_period_service.py`

- [ ] **Step 1: Add failing checklist tests**

Append to `backend/tests/test_period_close_service.py`:

```python
from app.services.period_close_service import run_period_close_checks


def test_period_close_checks_block_unbalanced_entries():
    items = run_period_close_checks(account_set_id="default", period="2026-06")

    assert any(item.check_code == "journal_entries_balanced" for item in items)
    assert all(item.severity in {"blocker", "warning"} for item in items)
```

- [ ] **Step 2: Implement required checks**

In `backend/app/services/period_close_service.py`, add checks:

- `period_exists`: 期间存在且属于当前账套
- `period_not_closed`: 期间未关闭
- `journal_entries_balanced`: 期间所有正式分录借贷平衡
- `voucher_posted`: 已入账凭证不存在草稿或未过账状态
- `account_subjects_active`: 分录使用的科目仍存在且未停用
- `currency_rates_ready`: 外币余额涉及币种存在期末汇率
- `depreciation_ready`: 固定资产模块无未确认折旧批次
- `payroll_ready`: 工资模块无未确认工资批次
- `tax_rule_ready`: 启用税费计提时存在税费规则

```python
def has_blocking_check(items: list[PeriodCloseCheckItem]) -> bool:
    return any(item.status == "failed" and item.severity == "blocker" for item in items)
```

- [ ] **Step 3: Wire close guard into period service**

In `backend/app/services/accounting_period_service.py`, update close flow:

```python
from app.services.period_close_service import has_blocking_check, run_period_close_checks


def close_accounting_period(account_set_id: str, period: str, closed_by: str):
    checks = run_period_close_checks(account_set_id=account_set_id, period=period)
    if has_blocking_check(checks):
        raise ValueError("期间存在未通过的结账检查，不能关闭")
    ...
```

- [ ] **Step 4: Verify and commit**

```powershell
python -m pytest backend/tests/test_period_close_service.py backend/tests/test_accounting_period_service.py
git add backend/app/services/period_close_service.py backend/app/services/accounting_period_service.py backend/tests/test_period_close_service.py backend/tests/test_accounting_period_service.py
git commit -m "feat: add period close checklist guard"
```

## Task 3: 折旧、工资与税费计提分录

**Files:**
- Modify: `backend/app/models/period_close.py`
- Modify: `backend/app/services/period_close_service.py`
- Modify: `backend/app/services/fixed_asset_service.py`
- Modify: `backend/app/services/payroll_service.py`
- Modify: `backend/tests/test_period_close_service.py`
- Modify: `backend/tests/test_fixed_asset_service.py`
- Modify: `backend/tests/test_payroll_service.py`

- [ ] **Step 1: Write accrual generation tests**

Append to `backend/tests/test_period_close_service.py`:

```python
from app.services.period_close_service import generate_period_close_actions


def test_generate_fixed_asset_depreciation_action_is_idempotent():
    first = generate_period_close_actions(
        account_set_id="default",
        period="2026-06",
        actions=["fixed_asset_depreciation"],
        generated_by="finance-user",
    )
    second = generate_period_close_actions(
        account_set_id="default",
        period="2026-06",
        actions=["fixed_asset_depreciation"],
        generated_by="finance-user",
    )

    assert first[0].status in {"generated", "skipped"}
    assert second[0].status in {"existing", "skipped"}
```

- [ ] **Step 2: Expose fixed asset depreciation summary**

In `backend/app/services/fixed_asset_service.py`, add a query function that returns confirmed monthly depreciation by asset dimension:

```python
def get_period_depreciation_summary(account_set_id: str, period: str) -> list[dict]:
    """返回指定期间可生成正式计提分录的折旧摘要。"""
    ...
```

Generated accounting rule:

- Debit: `6602 管理费用` or asset configured expense account
- Credit: `1602 累计折旧`
- `source_type`: `fixed_asset_depreciation`
- `source_id`: `fixed_asset_depreciation:{account_set_id}:{period}`

- [ ] **Step 3: Expose payroll accrual summary**

In `backend/app/services/payroll_service.py`, add:

```python
def get_period_payroll_accrual_summary(account_set_id: str, period: str) -> list[dict]:
    """返回指定期间工资计提摘要，按部门和员工辅助维度聚合。"""
    ...
```

Generated accounting rule:

- Debit: `6602 管理费用` / `6601 销售费用` / production configured account
- Credit: `2211 应付职工薪酬`
- `source_type`: `payroll_accrual`
- `source_id`: `payroll_accrual:{account_set_id}:{period}`

- [ ] **Step 4: Add MVP tax accrual rules**

In `backend/app/models/period_close.py`:

```python
class TaxAccrualRule(BaseModel):
    account_set_id: str = "default"
    tax_code: str
    tax_name: str
    rate: Decimal
    base_account_codes: list[str]
    debit_account_code: str
    credit_account_code: str = "2221"
```

Generated accounting rule examples:

- VAT surcharge: Debit `6403 税金及附加`, Credit `2221 应交税费`
- Corporate income tax provision: Debit `6901 所得税费用`, Credit `2221 应交税费`
- `source_type`: `tax_accrual`
- `source_id`: `tax_accrual:{account_set_id}:{period}:{tax_code}`

- [ ] **Step 5: Implement idempotent action generation**

In `backend/app/services/period_close_service.py`:

```python
def generate_period_close_actions(
    account_set_id: str,
    period: str,
    actions: list[str],
    generated_by: str,
    force_regenerate: bool = False,
) -> list[PeriodCloseActionResult]:
    # 期末动作必须逐项幂等，避免重复点击导致重复计提。
    ...
```

- [ ] **Step 6: Verify and commit**

```powershell
python -m pytest backend/tests/test_period_close_service.py backend/tests/test_fixed_asset_service.py backend/tests/test_payroll_service.py
git add backend/app/models/period_close.py backend/app/services/period_close_service.py backend/app/services/fixed_asset_service.py backend/app/services/payroll_service.py backend/tests/test_period_close_service.py backend/tests/test_fixed_asset_service.py backend/tests/test_payroll_service.py
git commit -m "feat: generate close accrual entries"
```

## Task 4: 外币期末重估与汇兑损益

**Files:**
- Modify: `backend/app/services/period_close_service.py`
- Modify: `backend/app/services/accounting_service.py`
- Modify: `backend/tests/test_period_close_service.py`
- Modify: `backend/tests/test_accounting_service.py`

- [ ] **Step 1: Write FX revaluation tests**

Append to `backend/tests/test_period_close_service.py`:

```python
def test_fx_revaluation_generates_base_currency_adjustment_only():
    results = generate_period_close_actions(
        account_set_id="default",
        period="2026-06",
        actions=["fx_revaluation"],
        generated_by="finance-user",
    )

    assert results[0].action_type == "fx_revaluation"
    assert results[0].status in {"generated", "existing", "skipped"}
```

- [ ] **Step 2: Add foreign currency balance query**

In `backend/app/services/accounting_service.py`, expose:

```python
def get_foreign_currency_balances(account_set_id: str, period: str) -> list[dict]:
    """按科目、币种和辅助维度返回期末外币余额及账面本位币余额。"""
    ...
```

This query must return:
- `account_code`
- `currency`
- `original_balance`
- `book_base_balance`
- `dimension_values`

- [ ] **Step 3: Generate revaluation entries**

In `backend/app/services/period_close_service.py`, calculate:

```python
expected_base_balance = original_balance * period_end_exchange_rate
adjustment = expected_base_balance - book_base_balance
```

Accounting rule:
- If asset foreign currency balance increases: Debit original asset account, Credit `6603 财务费用-汇兑损益`
- If asset foreign currency balance decreases: Debit `6603 财务费用-汇兑损益`, Credit original asset account
- Liability accounts use the opposite direction
- `original_amount` remains `0` for adjustment lines
- `currency` is base currency for adjustment lines
- `source_type`: `fx_revaluation`
- `source_id`: `fx_revaluation:{account_set_id}:{period}:{account_code}:{currency}:{dimension_hash}`

- [ ] **Step 4: Verify and commit**

```powershell
python -m pytest backend/tests/test_period_close_service.py backend/tests/test_accounting_service.py
git add backend/app/services/period_close_service.py backend/app/services/accounting_service.py backend/tests/test_period_close_service.py backend/tests/test_accounting_service.py
git commit -m "feat: add period end fx revaluation"
```

## Task 5: 损益结转与年结

**Files:**
- Modify: `backend/app/services/period_close_service.py`
- Modify: `backend/app/services/accounting_service.py`
- Modify: `backend/tests/test_period_close_service.py`
- Modify: `backend/tests/test_accounting_service.py`

- [ ] **Step 1: Write profit/loss carryforward tests**

Append to `backend/tests/test_period_close_service.py`:

```python
def test_profit_loss_carryforward_closes_revenue_and_expense_accounts():
    results = generate_period_close_actions(
        account_set_id="default",
        period="2026-06",
        actions=["profit_loss_carryforward"],
        generated_by="finance-user",
    )

    assert results[0].action_type == "profit_loss_carryforward"
    assert results[0].status in {"generated", "existing"}
```

- [ ] **Step 2: Add profit/loss account balance query**

In `backend/app/services/accounting_service.py`:

```python
def get_profit_loss_balances(account_set_id: str, period: str) -> list[dict]:
    """返回指定期间收入、成本、费用、损益类科目发生额余额。"""
    ...
```

Include accounts by category:
- Revenue: `6001`, `6051`, `6301`
- Cost and expense: `6401`, `6402`, `6403`, `6601`, `6602`, `6603`, `6701`, `6711`, `6901`

- [ ] **Step 3: Generate monthly carryforward**

Accounting rule:
- Revenue accounts with credit balance: Debit revenue account, Credit `4103 本年利润`
- Cost and expense accounts with debit balance: Debit `4103 本年利润`, Credit cost or expense account
- `source_type`: `profit_loss_carryforward`
- `source_id`: `profit_loss_carryforward:{account_set_id}:{period}`

- [ ] **Step 4: Generate year-end profit distribution**

Only for `close_type="year"`:
- Profit in `4103`: Debit `4103 本年利润`, Credit `4104 利润分配-未分配利润`
- Loss in `4103`: Debit `4104 利润分配-未分配利润`, Credit `4103 本年利润`
- `source_type`: `year_end_profit_distribution`
- `source_id`: `year_end_profit_distribution:{account_set_id}:{period}`

- [ ] **Step 5: Verify and commit**

```powershell
python -m pytest backend/tests/test_period_close_service.py backend/tests/test_accounting_service.py
git add backend/app/services/period_close_service.py backend/app/services/accounting_service.py backend/tests/test_period_close_service.py backend/tests/test_accounting_service.py
git commit -m "feat: add profit loss carryforward"
```

## Task 6: Period Close API、权限与审计

**Files:**
- Create: `backend/app/api/period_close.py`
- Modify: `backend/app/api/router_registry.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Create: `backend/tests/test_period_close_api.py`

- [ ] **Step 1: Write API tests**

Create `backend/tests/test_period_close_api.py`:

```python
def test_period_close_checks_endpoint(client):
    response = client.post(
        "/api/period-close/checks",
        json={"account_set_id": "default", "period": "2026-06"},
    )

    assert response.status_code == 200
    assert "items" in response.json()


def test_period_close_generate_endpoint(client):
    response = client.post(
        "/api/period-close/actions/generate",
        json={
            "account_set_id": "default",
            "period": "2026-06",
            "actions": ["profit_loss_carryforward"],
            "generated_by": "finance-user",
        },
    )

    assert response.status_code in {200, 409}
```

- [ ] **Step 2: Add API routes**

In `backend/app/api/period_close.py`:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/period-close", tags=["period-close"])


@router.post("/checks")
def run_checks(payload: PeriodCloseCheckRequest):
    return {"items": run_period_close_checks(payload.account_set_id, payload.period)}


@router.post("/actions/generate")
def generate_actions(payload: PeriodCloseGenerateRequest):
    return {
        "results": generate_period_close_actions(
            account_set_id=payload.account_set_id,
            period=payload.period,
            actions=payload.actions,
            generated_by=payload.generated_by,
            force_regenerate=payload.force_regenerate,
        )
    }
```

Endpoints:
- `POST /api/period-close/runs`
- `GET /api/period-close/runs`
- `POST /api/period-close/checks`
- `POST /api/period-close/actions/preview`
- `POST /api/period-close/actions/generate`
- `POST /api/period-close/close`
- `POST /api/period-close/reopen`

- [ ] **Step 3: Register permissions and audit events**

Permissions:
- `period_close.view`
- `period_close.check`
- `period_close.generate`
- `period_close.close`
- `period_close.reopen`

Audit event codes:
- `period_close.run_started`
- `period_close.checks_completed`
- `period_close.actions_generated`
- `period_close.period_closed`
- `period_close.period_reopened`

- [ ] **Step 4: Verify and commit**

```powershell
python -m pytest backend/tests/test_period_close_api.py backend/tests/test_period_close_service.py
git add backend/app/api/period_close.py backend/app/api/router_registry.py backend/app/services/system_admin_service.py backend/app/services/module_registry_service.py backend/tests/test_period_close_api.py
git commit -m "feat: expose period close api"
```

## Task 7: 前端期末处理面板

**Files:**
- Create: `frontend/src/types/periodClose.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/PeriodClosePanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Create: `frontend/tests/periodCloseApi.test.mjs`
- Create: `frontend/tests/periodClosePanel.test.mjs`

- [ ] **Step 1: Add frontend API tests**

Create `frontend/tests/periodCloseApi.test.mjs`:

```javascript
import assert from "node:assert/strict";
import test from "node:test";

import {
  generatePeriodCloseActions,
  runPeriodCloseChecks,
} from "../src/services/dashboardApi.js";

test("period close checks api keeps request scope explicit", async () => {
  const request = { account_set_id: "default", period: "2026-06" };
  const result = await runPeriodCloseChecks(request);

  assert.ok(Array.isArray(result.items));
});
```

- [ ] **Step 2: Add TypeScript types**

Create `frontend/src/types/periodClose.ts`:

```typescript
export type PeriodCloseStatus =
  | "draft"
  | "checking"
  | "ready"
  | "generated"
  | "closed"
  | "reopened"
  | "failed";

export type PeriodCloseActionType =
  | "fixed_asset_depreciation"
  | "payroll_accrual"
  | "tax_accrual"
  | "fx_revaluation"
  | "profit_loss_carryforward"
  | "year_end_profit_distribution";

export interface PeriodCloseCheckItem {
  check_code: string;
  check_name: string;
  status: "passed" | "failed" | "warning";
  severity: "blocker" | "warning";
  message: string;
}
```

- [ ] **Step 3: Add dashboard API methods**

In `frontend/src/services/dashboardApi.ts`:

```typescript
export async function runPeriodCloseChecks(request: PeriodCloseCheckRequest) {
  return apiPost<PeriodCloseCheckResponse>("/period-close/checks", request);
}

export async function generatePeriodCloseActions(request: PeriodCloseGenerateRequest) {
  return apiPost<PeriodCloseGenerateResponse>("/period-close/actions/generate", request);
}
```

- [ ] **Step 4: Build PeriodClosePanel**

Create `frontend/src/components/PeriodClosePanel.tsx` with:
- Period selector
- Close type selector: month/year
- Checklist section with passed/failed/warning states
- Action generation section for depreciation, payroll, tax, FX and P&L carryforward
- Generated journal entry link list
- Close button disabled until blocker checks are resolved and required actions are generated
- Reopen button visible only for closed periods and authorized users

Use existing UI density and panel conventions from dashboard components. Do not add marketing copy or explanatory hero sections.

- [ ] **Step 5: Wire navigation**

In `frontend/src/components/DashboardLayout.tsx`, add `PeriodClosePanel` as an accounting operation view near voucher, ledger and report panels.

- [ ] **Step 6: Verify and commit**

```powershell
npm --prefix frontend test
npm --prefix frontend run build
git add frontend/src/types/periodClose.ts frontend/src/services/dashboardApi.ts frontend/src/components/PeriodClosePanel.tsx frontend/src/components/DashboardLayout.tsx frontend/tests/periodCloseApi.test.mjs frontend/tests/periodClosePanel.test.mjs
git commit -m "feat: add period close panel"
```

## Task 8: 文档、回归验证与集成检查

**Files:**
- Modify: `README.md`
- Modify: `docs/01-mvp-design.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

- [ ] **Step 1: Document close workflow**

Update docs with:
- 期末处理入口和角色权限
- 结账检查清单
- 自动期末分录范围
- 外币重估计算口径
- 损益结转和年结规则
- 关闭期间后的写入限制
- 重开期间审计规则

- [ ] **Step 2: Add regression commands**

Document and run:

```powershell
python -m pytest backend/tests/test_period_close_service.py backend/tests/test_period_close_api.py backend/tests/test_accounting_period_service.py backend/tests/test_accounting_service.py backend/tests/test_fixed_asset_service.py backend/tests/test_payroll_service.py
npm --prefix frontend test
npm --prefix frontend run build
```

- [ ] **Step 3: Run focused manual verification**

Manual scenario:
1. Create June 2026 accounting period.
2. Post normal revenue, expense and foreign currency entries.
3. Run close checks.
4. Generate depreciation, payroll, tax, FX revaluation and P&L carryforward actions.
5. Confirm generated journal entries are balanced and linked to source actions.
6. Close the period.
7. Attempt to post a June 2026 entry and confirm the service rejects it.
8. Reopen the period and confirm audit event is recorded without deleting close entries.

- [ ] **Step 4: Final commit**

```powershell
git add README.md docs/01-mvp-design.md docs/02-api-design.md docs/03-frd-v1.0.md
git commit -m "docs: document period close workflow"
```

## Acceptance Criteria

- Period close checks return deterministic blocker/warning/passed results.
- A period with blocker checks cannot be closed.
- Depreciation, payroll, tax, FX and P&L close actions generate balanced formal journal entries.
- Re-running the same close action does not duplicate entries.
- Closed periods reject new journal entries, voucher postings and regenerated close entries.
- Reopening a period records audit history and keeps existing formal entries intact.
- FX revaluation adjusts only base currency carrying value and keeps original currency balances unchanged.
- Monthly P&L carryforward clears period revenue and expense balances into `4103 本年利润`.
- Year close transfers `4103 本年利润` into `4104 利润分配-未分配利润`.
- Frontend exposes a compact operational panel for checking, generating, closing and reopening periods.
- Documentation states the exact accounting rules, permissions and verification commands.

## Risk Controls

- Use `Decimal` for all money and exchange-rate calculations.
- Use service-level source keys to prevent duplicate generated entries.
- Keep generated close entries visible in normal ledger and statement queries.
- Do not allow automatic deletion of generated entries after close.
- Keep `force_regenerate` unavailable for closed periods.
- Store calculation evidence for tax and FX actions so accountants can review results.
- Run backend and frontend regression commands before merging implementation work.
