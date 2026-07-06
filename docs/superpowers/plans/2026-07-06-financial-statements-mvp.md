# Financial Statements MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 AI 财务中心补齐标准财务报表自动生成 MVP，覆盖资产负债表、利润表、现金流量表、所有者权益变动表和管理报表摘要。

**Architecture:** 后端新增独立 `financial_statement` 模型、服务与 API，从已审核凭证汇总标准报表项目；当当前账套无已审核凭证时回退使用样例经营数据，保证演示工作台可用。前端新增财务报表面板，通过统一 `dashboardApi.ts` helper 调用 `/api/v1/financial-statements/generate` 并展示四张报表和管理摘要。

**Tech Stack:** FastAPI, Pydantic, Decimal, pytest, React 19, TypeScript, Vite, node:test。

---

## File Structure

- Create: `backend/app/models/financial_statement.py`
  - 定义报表项目、单张报表、生成请求、生成响应和摘要模型。
- Create: `backend/app/services/financial_statement_service.py`
  - 生成标准报表；优先读取 `ledger_service.build_account_balance_table`，必要时回退 `SAMPLE_FINANCE_DATA`。
- Create: `backend/app/api/financial_statements.py`
  - 暴露 `POST /api/v1/financial-statements/generate`，接入权限和审计。
- Modify: `backend/app/api/router_registry.py`
  - 注册新 API router。
- Modify: `backend/app/services/system_admin_service.py`
  - 新增 `statement.generate` 权限，并授予财务主管。
- Modify: `backend/app/services/module_registry_service.py`
  - 将 `/api/v1/financial-statements` 与 `statement.generate` 纳入财务中心治理声明。
- Create: `backend/tests/test_financial_statement_service.py`
  - 覆盖样例数据回退、凭证汇总和管理摘要。
- Create: `backend/tests/test_financial_statement_api.py`
  - 覆盖成功审计、拒绝审计和模块注册。
- Modify: `backend/tests/test_system_admin_api.py`
  - 断言新增权限存在并授予财务主管。
- Create: `frontend/src/types/financialStatement.ts`
  - 定义前端报表响应类型。
- Modify: `frontend/src/services/dashboardApi.ts`
  - 新增 `generateFinancialStatements` helper。
- Create: `frontend/src/components/FinancialStatementPanel.tsx`
  - 展示报表摘要、资产负债表、利润表、现金流量表、所有者权益变动表。
- Modify: `frontend/src/components/DashboardLayout.tsx`
  - 在工资管理后、管理报告前接入面板。
- Modify: `frontend/src/navigation/osModules.json`
  - 为财务中心新增“财务报表”锚点，更新下一步说明。
- Modify: `frontend/src/styles.css`
  - 增加财务报表面板、摘要卡、报表表格和响应式样式。
- Create: `frontend/tests/financialStatementApi.test.mjs`
  - 覆盖 API helper URL、POST body 和 `X-Actor-Id`。
- Create: `frontend/tests/financialStatementPanel.test.mjs`
  - 静态断言面板接入、核心 class 和报表标题。
- Modify: `frontend/tests/osModules.test.mjs`
  - 断言财务中心包含 `financial-statements-panel`。
- Modify: `frontend/package.json`
  - 将新增前端测试纳入 `test:nav`。
- Modify: `README.md`, `docs/01-mvp-design.md`, `docs/02-api-design.md`, `docs/03-frd-v1.0.md`
  - 记录当前 MVP 能力和边界。

---

### Task 1: Backend Service Red Tests

**Files:**
- Create: `backend/tests/test_financial_statement_service.py`
- Create later: `backend/app/models/financial_statement.py`
- Create later: `backend/app/services/financial_statement_service.py`

- [ ] **Step 1: Write failing service tests**

```python
from decimal import Decimal

import pytest

from app.models.financial_statement import FinancialStatementGenerateRequest
from app.models.voucher_center import VoucherCenterCreateRequest, VoucherCenterLine
from app.services.financial_statement_service import generate_financial_statements
from app.services.voucher_center_service import create_voucher, reset_voucher_store, review_voucher


@pytest.fixture(autouse=True)
def isolated_voucher_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_AI_VOUCHER_DB_PATH", str(tmp_path / "voucher-center.sqlite3"))
    reset_voucher_store()


def test_financial_statements_fallback_to_sample_finance_data():
    result = generate_financial_statements(FinancialStatementGenerateRequest(period="2026-06"))

    assert result.period == "2026-06"
    assert result.source == "sample_finance_data"
    assert result.summary.asset_liability_balanced is True
    assert result.balance_sheet.total_assets == Decimal("2216.00")
    assert result.balance_sheet.total_liabilities_and_equity == Decimal("2216.00")
    assert result.income_statement.total_revenue == Decimal("1286.00")
    assert result.cash_flow_statement.net_cash_flow == Decimal("62.00")
    assert result.management_summary.key_metrics["净利率"] == "11.35%"
    assert {item.name for item in result.equity_statement.items} >= {"期初所有者权益", "本期净利润", "期末所有者权益"}


def test_financial_statements_use_reviewed_voucher_account_balances():
    voucher = create_voucher(
        VoucherCenterCreateRequest(
            voucher_date="2026-06-30",
            summary="主营业务收入确认",
            counterparty="上海客户",
            invoice_number="INV-202606",
            amount=Decimal("1000.00"),
            tax_amount=Decimal("60.00"),
            total_amount_with_tax=Decimal("1060.00"),
            lines=[
                VoucherCenterLine(account_code="1122", account_name="应收账款", direction="借", amount=Decimal("1060.00"), explanation="确认应收"),
                VoucherCenterLine(account_code="6001", account_name="主营业务收入", direction="贷", amount=Decimal("1000.00"), explanation="确认收入"),
                VoucherCenterLine(account_code="22210102", account_name="应交税费-销项税额", direction="贷", amount=Decimal("60.00"), explanation="销项税"),
            ],
        )
    )
    review_voucher(voucher.id, "财务主管")

    result = generate_financial_statements(FinancialStatementGenerateRequest(period="2026-06"))

    assert result.source == "reviewed_vouchers"
    assert result.balance_sheet.total_assets == Decimal("1060.00")
    assert result.balance_sheet.total_liabilities == Decimal("60.00")
    assert result.income_statement.total_revenue == Decimal("1000.00")
    assert result.income_statement.net_profit == Decimal("1000.00")
    assert result.summary.reviewed_voucher_count == 1
```

- [ ] **Step 2: Run service tests to verify RED**

Run: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_financial_statement_service.py -q`

Expected: FAIL because `app.models.financial_statement` or `generate_financial_statements` does not exist.

---

### Task 2: Backend Service Green

**Files:**
- Create: `backend/app/models/financial_statement.py`
- Create: `backend/app/services/financial_statement_service.py`

- [ ] **Step 1: Implement minimal models**

Create Pydantic models with these fields:

```python
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.finance import MONTH_PATTERN


class FinancialStatementGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: str = Field(pattern=MONTH_PATTERN)
    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    operator: str = Field(default="财务主管", min_length=1, max_length=32)


class StatementLineItem(BaseModel):
    code: str
    name: str
    amount: Decimal
    formula: str


class BalanceSheet(BaseModel):
    title: str
    period: str
    items: list[StatementLineItem]
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    total_liabilities_and_equity: Decimal
    balanced: bool


class IncomeStatement(BaseModel):
    title: str
    period: str
    items: list[StatementLineItem]
    total_revenue: Decimal
    total_cost: Decimal
    total_expense: Decimal
    total_profit: Decimal
    net_profit: Decimal


class CashFlowStatement(BaseModel):
    title: str
    period: str
    items: list[StatementLineItem]
    operating_cash_flow_net: Decimal
    investing_cash_flow_net: Decimal
    financing_cash_flow_net: Decimal
    net_cash_flow: Decimal


class EquityStatement(BaseModel):
    title: str
    period: str
    items: list[StatementLineItem]
    opening_equity: Decimal
    current_period_profit: Decimal
    closing_equity: Decimal


class ManagementStatementSummary(BaseModel):
    title: str
    key_metrics: dict[str, str]
    highlights: list[str]
    risks: list[str]


class FinancialStatementGenerationSummary(BaseModel):
    account_set_id: str
    period: str
    source: str
    reviewed_voucher_count: int
    asset_liability_balanced: bool
    generated_statement_count: int


class FinancialStatementBundle(BaseModel):
    account_set_id: str
    period: str
    company_name: str
    source: str
    summary: FinancialStatementGenerationSummary
    balance_sheet: BalanceSheet
    income_statement: IncomeStatement
    cash_flow_statement: CashFlowStatement
    equity_statement: EquityStatement
    management_summary: ManagementStatementSummary
```

- [ ] **Step 2: Implement minimal service**

Service behavior:
- Validate period and account set through existing ledger/accounting period path.
- Call `build_account_balance_table(period, account_set_id)`.
- If reviewed voucher count/account count is positive, map account prefixes:
  - `1001`, `1002` -> cash
  - `1122` -> accounts receivable
  - `1405` -> inventory
  - `1601` -> fixed assets
  - `2202` -> accounts payable
  - `2001` -> short-term loans
  - `2221` -> tax payable
  - `4001` -> paid-in capital/equity
  - `6001`, `6051` -> revenue
  - `6401` -> cost
  - `6601`, `6602`, `6603` -> expenses
- If no reviewed vouchers, use `SAMPLE_FINANCE_DATA` current and previous periods.
- Decimal amounts quantized to `0.01`.

- [ ] **Step 3: Run service tests to verify GREEN**

Run: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_financial_statement_service.py -q`

Expected: PASS.

---

### Task 3: Backend API, Permissions, Registry

**Files:**
- Create: `backend/tests/test_financial_statement_api.py`
- Modify: `backend/tests/test_system_admin_api.py`
- Create: `backend/app/api/financial_statements.py`
- Modify: `backend/app/api/router_registry.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`

- [ ] **Step 1: Write failing API tests**

```python
from fastapi.testclient import TestClient

from app.main import app
from app.services.system_admin_service import reset_system_admin_store


client = TestClient(app)


def test_financial_statement_api_generates_bundle_and_records_success_audit():
    reset_system_admin_store()

    response = client.post(
        "/api/v1/financial-statements/generate",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={"period": "2026-06", "account_set_id": "default", "operator": "财务主管"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["period"] == "2026-06"
    assert payload["balance_sheet"]["title"] == "资产负债表"
    assert payload["income_statement"]["title"] == "利润表"
    assert payload["cash_flow_statement"]["title"] == "现金流量表"
    assert payload["equity_statement"]["title"] == "所有者权益变动表"

    logs_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=5")
    log = logs_response.json()["logs"][0]
    assert log["event"] == "statement.generate"
    assert log["actor_id"] == "u-finance-manager"
    assert log["result"] == "success"
    assert log["metadata"]["period"] == "2026-06"
    assert log["metadata"]["statement_count"] == 5


def test_financial_statement_api_rejects_unauthorized_actor_and_records_denied_audit():
    reset_system_admin_store()

    response = client.post(
        "/api/v1/financial-statements/generate",
        headers={"X-Actor-Id": "u-api-integrator"},
        json={"period": "2026-06"},
    )

    assert response.status_code == 403

    logs_response = client.get("/api/v1/system/audit-logs?module_id=finance-center&limit=5")
    log = logs_response.json()["logs"][0]
    assert log["event"] == "statement.generate"
    assert log["result"] == "denied"
    assert log["metadata"]["permission_code"] == "statement.generate"


def test_finance_center_registry_declares_financial_statement_api():
    response = client.get("/api/v1/modules/finance-center")

    assert response.status_code == 200
    module = response.json()
    assert "/api/v1/financial-statements" in module["api_prefixes"]
    assert "statement.generate" in module["audit_events"]
```

Add assertions to `test_system_admin_api.py`:

```python
assert "statement.generate" in permission_codes
assert "statement.generate" in role_by_id["finance_manager"]["permission_codes"]
```

- [ ] **Step 2: Run API tests to verify RED**

Run: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_financial_statement_api.py backend/tests/test_system_admin_api.py -q`

Expected: FAIL because route and permission are missing.

- [ ] **Step 3: Implement API and governance**

Implement:
- Router prefix `/api/v1/financial-statements`
- `POST /generate`
- Permission `statement.generate`
- Audit event `statement.generate`
- Register router in `router_registry.py`
- Add prefix/event to `module_registry_service.py`

- [ ] **Step 4: Run API tests to verify GREEN**

Run: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_financial_statement_api.py backend/tests/test_system_admin_api.py -q`

Expected: PASS.

---

### Task 4: Frontend API And Panel Red Tests

**Files:**
- Create: `frontend/tests/financialStatementApi.test.mjs`
- Create: `frontend/tests/financialStatementPanel.test.mjs`
- Modify later: `frontend/src/types/financialStatement.ts`
- Modify later: `frontend/src/services/dashboardApi.ts`
- Create later: `frontend/src/components/FinancialStatementPanel.tsx`
- Modify later: `frontend/src/components/DashboardLayout.tsx`

- [ ] **Step 1: Write failing frontend tests**

```js
import assert from "node:assert/strict";
import test from "node:test";

import { generateFinancialStatements } from "../src/services/dashboardApi.ts";

function createFetcher(payloads) {
  const calls = [];
  const fetcher = async (url, init = {}) => {
    calls.push({ url, init });
    const payload = payloads[url];
    return {
      ok: Boolean(payload),
      status: payload ? 200 : 404,
      json: async () => payload ?? { detail: "not found" }
    };
  };
  fetcher.calls = calls;
  return fetcher;
}

test("财务报表 API helper 发送生成请求", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/financial-statements/generate": {
      period: "2026-06",
      source: "sample_finance_data",
      balance_sheet: { title: "资产负债表", items: [] },
      income_statement: { title: "利润表", items: [] },
      cash_flow_statement: { title: "现金流量表", items: [] },
      equity_statement: { title: "所有者权益变动表", items: [] },
      management_summary: { title: "管理报表摘要", key_metrics: {}, highlights: [], risks: [] }
    }
  });

  const result = await generateFinancialStatements(
    { period: "2026-06", account_set_id: "default", operator: "财务主管" },
    "http://api.local",
    fetcher
  );

  assert.equal(result.balance_sheet.title, "资产负债表");
  assert.equal(fetcher.calls[0].url, "http://api.local/api/v1/financial-statements/generate");
  assert.equal(fetcher.calls[0].init.method, "POST");
  assert.equal(fetcher.calls[0].init.headers["X-Actor-Id"], "u-finance-manager");
  assert.match(fetcher.calls[0].init.body, /2026-06/);
});
```

```js
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("AI财务中心接入财务报表生成面板", async () => {
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");
  const panel = await readFile(resolve("src/components/FinancialStatementPanel.tsx"), "utf8");

  assert.match(layout, /FinancialStatementPanel/);
  assert.match(panel, /financial-statements-panel/);
  assert.match(panel, /generateFinancialStatements/);
  assert.match(panel, /financial-statement-summary-grid/);
  assert.match(panel, /statement-table/);
  assert.match(panel, /资产负债表/);
  assert.match(panel, /利润表/);
  assert.match(panel, /现金流量表/);
  assert.match(panel, /所有者权益变动表/);
});
```

- [ ] **Step 2: Run frontend tests to verify RED**

Run: `cd frontend; node tests/financialStatementApi.test.mjs && node tests/financialStatementPanel.test.mjs`

Expected: FAIL because helper and panel are missing.

---

### Task 5: Frontend Green

**Files:**
- Create: `frontend/src/types/financialStatement.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/FinancialStatementPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Modify: `frontend/src/navigation/osModules.json`
- Modify: `frontend/tests/osModules.test.mjs`
- Modify: `frontend/package.json`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Implement frontend types and helper**

Define `FinancialStatementGenerateRequest`, `StatementLineItem`, `FinancialStatementBundle` and related statement interfaces. Add `generateFinancialStatements(request, apiBase, fetcher, actorId)` using `POST /api/v1/financial-statements/generate` and `X-Actor-Id`.

- [ ] **Step 2: Implement panel**

Panel behavior:
- Props: `period: string`
- On mount and on “重新生成” click call `generateFinancialStatements`
- Show summary cards: source, balance status, reviewed voucher count, generated count
- Render four statement tables with `statement-table`
- Render management summary highlights and risks
- Use `id="financial-statements-panel"`

- [ ] **Step 3: Wire layout, nav, tests and styles**

Insert panel after `<PayrollPanel />`; add nav item anchor; add `financialStatementApi.test.mjs` and `financialStatementPanel.test.mjs` to `test:nav`; add responsive CSS.

- [ ] **Step 4: Run frontend tests to verify GREEN**

Run: `cd frontend; npm run test:nav`

Expected: PASS.

---

### Task 6: Docs And Full Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/01-mvp-design.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

- [ ] **Step 1: Update docs**

Document:
- New API: `POST /api/v1/financial-statements/generate`
- Permission: `statement.generate`
- Audit event: `statement.generate`
- MVP coverage: 单账套、单期间、凭证/样例数据生成四张标准报表和管理摘要
- Boundary: 不覆盖合并报表、复杂金融工具、长期股权投资、递延所得税、现金流量表补充资料和正式申报报表

- [ ] **Step 2: Run backend full tests**

Run: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests -q`

Expected: PASS.

- [ ] **Step 3: Run frontend tests and build**

Run: `cd frontend; npm run test:nav`

Expected: PASS.

Run: `cd frontend; npm run build`

Expected: PASS. Existing Vite chunk-size warning is acceptable if build exits 0.

- [ ] **Step 4: Verify real API and UI**

Restart backend if needed. Verify:
- `POST http://127.0.0.1:8000/api/v1/financial-statements/generate`
- Desktop screenshot: `output/playwright/financial-statements-desktop.png`
- Mobile screenshot: `output/playwright/financial-statements-mobile.png`

Expected:
- API returns four statements and management summary.
- Desktop and mobile show financial statement panel with no obvious overlap or unreadable controls.

---

## Self-Review

- Spec coverage: FRD 报表项中的资产负债表、利润表、现金流量表、所有者权益变动表、管理报表均有任务覆盖。
- Placeholder scan: 无 TBD、TODO、implement later、fill in details。
- Type consistency: 后端 `FinancialStatementBundle`、前端 `FinancialStatementBundle`、API helper 和面板均使用同一概念名；权限和审计统一为 `statement.generate`。
