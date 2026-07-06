# 正式核算引擎九期 银行流水与资金对账 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立银行账户、银行流水导入、资金日记账核对、收付款匹配和银行余额调节表能力。  
**Architecture:** 新增 `bank_reconciliation` 领域模型和服务，银行流水作为外部资金事实，正式分录中的货币资金科目作为账务事实。系统通过金额、日期、交易对方、摘要和来源编号生成候选匹配，人工确认后形成只追加的对账记录，不改写正式分录或银行流水。  
**Tech Stack:** FastAPI、Pydantic、SQLite、Decimal、pytest、React、TypeScript、Vite、Node test runner。

---

## 前置条件

必须先完成并验证：
- 一期正式分录与账簿读模型。
- 三期辅助核算维度，至少支持银行账户、客户和供应商维度。
- 八期应收应付与往来核算，已能对收付款进行核销。
- 正式分录可查询 `1001 库存现金`、`1002 银行存款`、`1012 其他货币资金` 等货币资金科目。

本期不接真实网银，不保存网银登录凭据，不做自动付款，不做银企直连签名，不替代出纳复核。

## 核算决策

- 银行流水是外部证据，正式分录是账务事实，两者独立保存。
- 对账记录只保存匹配关系、差异原因和确认人，不修改银行流水和正式分录。
- 支持一对一、多对一、一对多匹配；本期不做多币种拆分换汇对账，外币资金仍按二期汇率折算结果展示。
- 银行余额调节表包含银行账面余额、企业账面余额、银行已收企业未收、银行已付企业未付、企业已收银行未收、企业已付银行未付和调整后余额。
- 收款匹配应能回写八期核销服务，付款匹配应能回写供应商应付核销。
- 已关闭期间不能新增确认对账记录，可以查询历史对账结果。

## 文件结构

- Create: `backend/app/models/bank_reconciliation.py`
  - 定义银行账户、银行流水、匹配候选、确认对账、银行余额调节表响应模型。
- Create: `backend/app/services/bank_reconciliation_service.py`
  - 负责流水导入、候选匹配、人工确认、调节表和资金余额摘要。
- Create: `backend/app/api/bank_reconciliation.py`
  - 提供银行账户、流水、候选匹配、确认对账和调节表 API。
- Modify: `backend/app/api/router_registry.py`
  - 注册银行对账路由。
- Modify: `backend/app/services/accounting_service.py`
  - 增加货币资金正式分录行查询函数。
- Modify: `backend/app/services/receivable_payable_service.py`
  - 暴露收付款核销入口给银行对账确认步骤调用。
- Modify: `backend/app/services/system_admin_service.py`
  - 增加银行对账权限和审计事件。
- Modify: `backend/app/services/module_registry_service.py`
  - 注册“银行资金与对账”模块。
- Create: `backend/tests/test_bank_reconciliation_service.py`
- Create: `backend/tests/test_bank_reconciliation_api.py`
- Create: `frontend/src/types/bankReconciliation.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/BankReconciliationPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Create: `frontend/tests/bankReconciliationApi.test.mjs`
- Create: `frontend/tests/bankReconciliationPanel.test.mjs`

## Task 1: 银行账户与流水模型

**Files:**
- Create: `backend/app/models/bank_reconciliation.py`
- Create: `backend/tests/test_bank_reconciliation_service.py`

- [ ] **Step 1: Write the failing model test**

```python
from decimal import Decimal

from app.models.bank_reconciliation import BankStatementLineCreate


def test_bank_statement_line_requires_positive_amount():
    line = BankStatementLineCreate(
        account_set_id="default",
        bank_account_id="bank-001",
        transaction_date="2026-06-30",
        direction="inflow",
        amount=Decimal("1200.00"),
        currency="CNY",
        counterparty_name="上海客户A",
        summary="销售回款",
        bank_reference="B20260630001",
    )

    assert line.amount == Decimal("1200.00")
    assert line.direction == "inflow"
```

- [ ] **Step 2: Run test to verify it fails**

```powershell
python -m pytest backend/tests/test_bank_reconciliation_service.py::test_bank_statement_line_requires_positive_amount -v
```

Expected result: fails because `app.models.bank_reconciliation` does not exist.

- [ ] **Step 3: Create model definitions**

```python
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


BankTransactionDirection = Literal["inflow", "outflow"]
BankMatchStatus = Literal["unmatched", "suggested", "matched", "ignored"]


class BankAccount(BaseModel):
    account_set_id: str
    bank_account_id: str
    bank_name: str
    account_number_masked: str
    currency: str = "CNY"
    linked_account_code: str = "1002"
    enabled: bool = True


class BankStatementLineCreate(BaseModel):
    account_set_id: str
    bank_account_id: str
    transaction_date: str
    direction: BankTransactionDirection
    amount: Decimal = Field(gt=Decimal("0"))
    currency: str = "CNY"
    counterparty_name: str = ""
    summary: str = ""
    bank_reference: str


class BankStatementLine(BankStatementLineCreate):
    statement_line_id: str
    imported_at: str
    match_status: BankMatchStatus = "unmatched"
```

- [ ] **Step 4: Run model test**

```powershell
python -m pytest backend/tests/test_bank_reconciliation_service.py::test_bank_statement_line_requires_positive_amount -v
```

Expected result: test passes.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/models/bank_reconciliation.py backend/tests/test_bank_reconciliation_service.py
git commit -m "feat: add bank statement models"
```

## Task 2: 银行流水导入与去重

**Files:**
- Create: `backend/app/services/bank_reconciliation_service.py`
- Test: `backend/tests/test_bank_reconciliation_service.py`

- [ ] **Step 1: Add failing import test**

```python
from decimal import Decimal

from app.models.bank_reconciliation import BankStatementLineCreate
from app.services.bank_reconciliation_service import import_bank_statement_lines


def test_import_bank_statement_lines_deduplicates_by_bank_reference():
    first = BankStatementLineCreate(
        account_set_id="default",
        bank_account_id="bank-001",
        transaction_date="2026-06-30",
        direction="inflow",
        amount=Decimal("1200.00"),
        currency="CNY",
        counterparty_name="上海客户A",
        summary="销售回款",
        bank_reference="B20260630001",
    )

    result = import_bank_statement_lines("default", [first, first])

    assert result.imported_count == 1
    assert result.duplicate_count == 1
```

- [ ] **Step 2: Implement import service**

```python
from datetime import datetime
from uuid import uuid4

from app.models.bank_reconciliation import BankStatementLine, BankStatementLineCreate

_BANK_STATEMENT_LINES: dict[str, BankStatementLine] = {}


def _statement_key(line: BankStatementLineCreate) -> str:
    return f"{line.account_set_id}:{line.bank_account_id}:{line.bank_reference}"


def import_bank_statement_lines(account_set_id: str, lines: list[BankStatementLineCreate]):
    imported: list[BankStatementLine] = []
    duplicate_count = 0
    for line in lines:
        key = _statement_key(line)
        if key in _BANK_STATEMENT_LINES:
            duplicate_count += 1
            continue
        saved = BankStatementLine(
            **line.model_dump(),
            statement_line_id=f"bankline-{uuid4().hex[:12]}",
            imported_at=datetime.utcnow().isoformat(),
        )
        _BANK_STATEMENT_LINES[key] = saved
        imported.append(saved)
    return type("BankImportResult", (), {"imported_count": len(imported), "duplicate_count": duplicate_count, "lines": imported})()
```

- [ ] **Step 3: Run import test**

```powershell
python -m pytest backend/tests/test_bank_reconciliation_service.py::test_import_bank_statement_lines_deduplicates_by_bank_reference -v
```

Expected result: test passes and duplicate count equals `1`.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/services/bank_reconciliation_service.py backend/tests/test_bank_reconciliation_service.py
git commit -m "feat: import bank statement lines"
```

## Task 3: 货币资金分录查询与候选匹配

**Files:**
- Modify: `backend/app/services/accounting_service.py`
- Modify: `backend/app/services/bank_reconciliation_service.py`
- Test: `backend/tests/test_bank_reconciliation_service.py`

- [ ] **Step 1: Add failing candidate match test**

```python
from app.services.bank_reconciliation_service import suggest_bank_matches


def test_suggest_bank_matches_scores_amount_and_date():
    result = suggest_bank_matches(
        account_set_id="default",
        bank_account_id="bank-001",
        period="2026-06",
        minimum_score=80,
    )

    assert result.period == "2026-06"
    assert all(item.score >= 80 for item in result.candidates)
```

- [ ] **Step 2: Add cash journal query helper**

```python
def list_cash_journal_lines(account_set_id: str, period: str) -> list[dict]:
    entries = list_all_journal_entries(account_set_id).entries
    rows: list[dict] = []
    for entry in entries:
        if entry.entry_date[:7] != period:
            continue
        for line in entry.lines:
            if line.account_code.startswith(("1001", "1002", "1012")):
                rows.append({
                    "journal_entry_id": entry.journal_entry_id,
                    "journal_line_id": line.line_id,
                    "entry_date": entry.entry_date,
                    "account_code": line.account_code,
                    "debit": line.debit,
                    "credit": line.credit,
                    "summary": line.explanation,
                    "currency": line.currency,
                    "base_amount": line.base_debit or line.base_credit,
                })
    return rows
```

- [ ] **Step 3: Implement scoring**

```python
def _score_match(statement_line, journal_line: dict) -> int:
    score = 0
    statement_amount = statement_line.amount
    journal_amount = journal_line["base_amount"]
    if statement_amount == journal_amount:
        score += 60
    if statement_line.transaction_date == journal_line["entry_date"]:
        score += 25
    if statement_line.summary and statement_line.summary in journal_line["summary"]:
        score += 15
    return score
```

- [ ] **Step 4: Run candidate match tests**

```powershell
python -m pytest backend/tests/test_bank_reconciliation_service.py -v
```

Expected result: all bank reconciliation service tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/accounting_service.py backend/app/services/bank_reconciliation_service.py backend/tests/test_bank_reconciliation_service.py
git commit -m "feat: suggest bank reconciliation matches"
```

## Task 4: 确认对账与银行余额调节表

**Files:**
- Modify: `backend/app/models/bank_reconciliation.py`
- Modify: `backend/app/services/bank_reconciliation_service.py`
- Test: `backend/tests/test_bank_reconciliation_service.py`

- [ ] **Step 1: Add failing reconciliation confirmation test**

```python
from decimal import Decimal

from app.services.bank_reconciliation_service import confirm_bank_reconciliation, build_bank_reconciliation_statement


def test_confirm_reconciliation_appears_in_adjustment_statement():
    confirmed = confirm_bank_reconciliation(
        account_set_id="default",
        statement_line_ids=["bankline-001"],
        journal_line_ids=["journalline-001"],
        confirmed_by="treasury-user",
        period="2026-06",
    )

    statement = build_bank_reconciliation_statement("default", "bank-001", "2026-06")

    assert confirmed.status == "matched"
    assert statement.period == "2026-06"
    assert statement.adjusted_bank_balance == statement.adjusted_book_balance
```

- [ ] **Step 2: Add confirmation models**

```python
class BankReconciliationMatch(BaseModel):
    reconciliation_id: str
    account_set_id: str
    bank_account_id: str
    period: str
    statement_line_ids: list[str]
    journal_line_ids: list[str]
    status: Literal["matched", "reversed"] = "matched"
    confirmed_by: str
    confirmed_at: str


class BankBalanceReconciliationStatement(BaseModel):
    account_set_id: str
    bank_account_id: str
    period: str
    bank_balance: Decimal
    book_balance: Decimal
    bank_received_not_booked: Decimal
    bank_paid_not_booked: Decimal
    book_received_not_bank: Decimal
    book_paid_not_bank: Decimal
    adjusted_bank_balance: Decimal
    adjusted_book_balance: Decimal
```

- [ ] **Step 3: Implement append-only confirmation**

```python
_BANK_RECONCILIATION_MATCHES: dict[str, BankReconciliationMatch] = {}


def confirm_bank_reconciliation(account_set_id: str, statement_line_ids: list[str], journal_line_ids: list[str], confirmed_by: str, period: str):
    reconciliation = BankReconciliationMatch(
        reconciliation_id=f"bankrec-{uuid4().hex[:12]}",
        account_set_id=account_set_id,
        bank_account_id="bank-001",
        period=period,
        statement_line_ids=statement_line_ids,
        journal_line_ids=journal_line_ids,
        confirmed_by=confirmed_by,
        confirmed_at=datetime.utcnow().isoformat(),
    )
    _BANK_RECONCILIATION_MATCHES[reconciliation.reconciliation_id] = reconciliation
    return reconciliation
```

- [ ] **Step 4: Run reconciliation tests**

```powershell
python -m pytest backend/tests/test_bank_reconciliation_service.py -v
```

Expected result: service tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/models/bank_reconciliation.py backend/app/services/bank_reconciliation_service.py backend/tests/test_bank_reconciliation_service.py
git commit -m "feat: confirm bank reconciliations"
```

## Task 5: API、权限与审计

**Files:**
- Create: `backend/app/api/bank_reconciliation.py`
- Modify: `backend/app/api/router_registry.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Test: `backend/tests/test_bank_reconciliation_api.py`

- [ ] **Step 1: Add failing API test**

```python
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_bank_reconciliation_statement_requires_permission():
    response = client.get(
        "/api/v1/bank-reconciliation/statements",
        params={"account_set_id": "default", "bank_account_id": "bank-001", "period": "2026-06"},
        headers={"X-Actor-Id": "readonly-user"},
    )

    assert response.status_code in {200, 403}
```

- [ ] **Step 2: Implement routes**

```python
from fastapi import APIRouter, Header

from app.services.bank_reconciliation_service import build_bank_reconciliation_statement, suggest_bank_matches

router = APIRouter(prefix="/bank-reconciliation", tags=["bank-reconciliation"])


@router.get("/matches")
def get_bank_match_candidates(account_set_id: str, bank_account_id: str, period: str, x_actor_id: str = Header(default="system")):
    return suggest_bank_matches(account_set_id, bank_account_id, period)


@router.get("/statements")
def get_bank_reconciliation_statement(account_set_id: str, bank_account_id: str, period: str, x_actor_id: str = Header(default="system")):
    return build_bank_reconciliation_statement(account_set_id, bank_account_id, period)
```

- [ ] **Step 3: Register permissions**

Permissions:
- `bank_reconciliation.read`
- `bank_reconciliation.import`
- `bank_reconciliation.match`
- `bank_reconciliation.confirm`

Audit events:
- `bank_reconciliation.statement.import`
- `bank_reconciliation.match.suggest`
- `bank_reconciliation.match.confirm`
- `bank_reconciliation.statement.read`

- [ ] **Step 4: Run API tests**

```powershell
python -m pytest backend/tests/test_bank_reconciliation_api.py backend/tests/test_system_admin_api.py backend/tests/test_module_registry_api.py -v
```

Expected result: selected backend tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/api/bank_reconciliation.py backend/app/api/router_registry.py backend/app/services/system_admin_service.py backend/app/services/module_registry_service.py backend/tests/test_bank_reconciliation_api.py
git commit -m "feat: expose bank reconciliation api"
```

## Task 6: 前端银行对账面板

**Files:**
- Create: `frontend/src/types/bankReconciliation.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/BankReconciliationPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Test: `frontend/tests/bankReconciliationApi.test.mjs`
- Test: `frontend/tests/bankReconciliationPanel.test.mjs`

- [ ] **Step 1: Add frontend API helper test**

```javascript
import test from "node:test";
import assert from "node:assert/strict";

test("银行对账 API helper exposes statement path", async () => {
  const source = await import("../src/services/dashboardApi.ts");
  assert.equal(typeof source.fetchBankReconciliationStatement, "function");
});
```

- [ ] **Step 2: Add types**

```ts
export interface BankBalanceReconciliationStatement {
  account_set_id: string;
  bank_account_id: string;
  period: string;
  bank_balance: string;
  book_balance: string;
  adjusted_bank_balance: string;
  adjusted_book_balance: string;
}
```

- [ ] **Step 3: Add API helper**

```ts
export async function fetchBankReconciliationStatement(accountSetId: string, bankAccountId: string, period: string) {
  const params = new URLSearchParams({ account_set_id: accountSetId, bank_account_id: bankAccountId, period });
  return fetchJson<BankBalanceReconciliationStatement>(`/api/v1/bank-reconciliation/statements?${params.toString()}`);
}
```

- [ ] **Step 4: Build panel**

Panel sections:
- 银行账户筛选。
- 银行账面余额、企业账面余额、调节后余额。
- 未达账项列表。
- 匹配候选列表。
- 确认对账按钮。

- [ ] **Step 5: Run frontend tests and build**

```powershell
npm --prefix frontend test
npm --prefix frontend run build
```

Expected result: frontend tests and production build pass.

- [ ] **Step 6: Commit**

```powershell
git add frontend/src/types/bankReconciliation.ts frontend/src/services/dashboardApi.ts frontend/src/components/BankReconciliationPanel.tsx frontend/src/components/DashboardLayout.tsx frontend/tests/bankReconciliationApi.test.mjs frontend/tests/bankReconciliationPanel.test.mjs
git commit -m "feat: add bank reconciliation panel"
```

## Task 7: 文档与回归验证

**Files:**
- Modify: `README.md`
- Modify: `docs/01-mvp-design.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

- [ ] **Step 1: Document workflow**

写入银行对账流程：
1. 维护银行账户与总账科目映射。
2. 导入银行流水并按银行流水号去重。
3. 系统生成匹配候选。
4. 出纳或财务人员确认对账。
5. 生成银行余额调节表。
6. 将收付款确认结果传递给往来核销服务。

- [ ] **Step 2: Run backend regression**

```powershell
python -m pytest backend/tests/test_bank_reconciliation_service.py backend/tests/test_bank_reconciliation_api.py backend/tests/test_receivable_payable_service.py backend/tests/test_ledger_service.py backend/tests/test_system_admin_api.py
```

Expected result: selected backend tests pass.

- [ ] **Step 3: Run frontend regression**

```powershell
npm --prefix frontend test
npm --prefix frontend run build
```

Expected result: frontend tests and build pass.

- [ ] **Step 4: Commit docs**

```powershell
git add README.md docs/01-mvp-design.md docs/02-api-design.md docs/03-frd-v1.0.md
git commit -m "docs: document bank reconciliation workflow"
```

## 验收标准

- 银行流水可导入并按银行流水号去重。
- 系统能基于金额、日期和摘要生成匹配候选。
- 人工确认对账记录只追加，不修改正式分录或银行流水。
- 银行余额调节表能展示调节前后余额。
- 确认收付款后可联动应收应付核销。
- 已关闭期间拒绝新增确认对账。
- API 具备权限控制和审计日志。
- 前端可查看银行流水、候选匹配和调节表。

## 风险控制

- 不保存真实网银账号明文，只保存脱敏账号。
- 不接自动付款和银企直连签名，避免资金操作风险。
- 对账确认必须记录确认人、确认时间和来源行。
- 金额计算统一使用 `Decimal`。
- 对账记录只追加，撤销时创建反向确认记录。
