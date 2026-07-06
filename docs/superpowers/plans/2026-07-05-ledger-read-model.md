# Ledger Read Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于已审核凭证生成只读总账、明细账和科目余额表读模型。

**Architecture:** 后端新增独立 `ledger` 模型、服务和 API 路由，数据源复用凭证中心 SQLite 读出的 `VoucherCenterRecord`，只统计 `reviewed` 状态凭证。前端新增账簿类型、API 方法和财务中心面板，展示期间、借贷合计、科目余额和明细分录。

**Tech Stack:** FastAPI、Pydantic v2、SQLite 凭证中心、React、TypeScript、Vite、node:test。

---

### Task 1: 后端账簿读模型

**Files:**
- Create: `backend/app/models/ledger.py`
- Create: `backend/app/services/ledger_service.py`
- Test: `backend/tests/test_ledger_service.py`

- [ ] **Step 1: Write the failing service test**

```python
def test_general_ledger_uses_only_reviewed_vouchers():
    reset_voucher_store()
    reviewed = create_voucher(_request("2026-06-30", "已审核费用"))
    review_voucher(reviewed.id, "财务主管")
    create_voucher(_request("2026-06-30", "草稿费用"))

    ledger = build_general_ledger("2026-06")

    assert ledger.voucher_count == 1
    assert ledger.total_debit == Decimal("1060.00")
    assert ledger.total_credit == Decimal("1060.00")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_ledger_service.py -q`
Expected: FAIL because `app.services.ledger_service` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create Pydantic response models for account summaries, detail lines, general ledger, detail ledger, and account balance table. Implement service functions that filter reviewed vouchers by `YYYY-MM`, sum debit and credit lines, and return deterministic account ordering.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_ledger_service.py -q`
Expected: PASS.

### Task 2: 后端账簿 API

**Files:**
- Create: `backend/app/api/ledger.py`
- Modify: `backend/app/api/router_registry.py`
- Test: `backend/tests/test_ledger_api.py`

- [ ] **Step 1: Write the failing API test**

```python
def test_ledger_api_returns_general_detail_and_balance_reports():
    response = client.get("/api/v1/ledger/general?period=2026-06")
    assert response.status_code == 200
    assert response.json()["balanced"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_ledger_api.py -q`
Expected: FAIL with 404 because ledger router is not mounted.

- [ ] **Step 3: Write minimal implementation**

Expose `GET /api/v1/ledger/general`, `GET /api/v1/ledger/detail`, and `GET /api/v1/ledger/account-balances` with `period` query validation and optional `account_code` on detail ledger.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_ledger_api.py -q`
Expected: PASS.

### Task 3: 前端账簿面板

**Files:**
- Create: `frontend/src/types/ledger.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/LedgerPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Modify: `frontend/src/styles.css`
- Test: `frontend/tests/ledgerApi.test.mjs`
- Test: `frontend/tests/ledgerPanel.test.mjs`

- [ ] **Step 1: Write failing frontend tests**

```js
assert.equal(fetcher.calls[0], "http://api.local/api/v1/ledger/general?period=2026-06");
assert.match(layout, /LedgerPanel/);
assert.match(panel, /fetchGeneralLedger/);
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend; node tests/ledgerApi.test.mjs && node tests/ledgerPanel.test.mjs`
Expected: FAIL because API helpers and panel do not exist.

- [ ] **Step 3: Write minimal implementation**

Add ledger TypeScript types, fetch helpers, a compact账簿面板, and mount it under AI 财务中心 after凭证中心。

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend; node tests/ledgerApi.test.mjs && node tests/ledgerPanel.test.mjs`
Expected: PASS.

### Task 4: 文档与验证

**Files:**
- Modify: `docs/01-mvp-design.md`
- Modify: `docs/02-api-design.md`
- Modify: `README.md`

- [ ] **Step 1: Update documentation**

Document that current ledgers are read-only views derived from reviewed voucher-center records, not a formal posting engine.

- [ ] **Step 2: Run full verification**

Run:
```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend/tests
cd frontend; npm run test:nav; npm run build
```

Expected: 后端全部通过，前端测试和构建通过；若 Vite chunk 体积警告仍存在，只作为既有非阻塞警告记录。
