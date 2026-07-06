# Account Set Isolation And Close Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为凭证、账簿和会计期间增加账套隔离，并让关账前阻止存在未过账凭证的期间。

**Architecture:** `account_set_id` 作为轻量租户/账套边界，默认值保持 `default`，旧接口不传参数仍保持现有行为。凭证记录保存账套字段，账簿与期间统计按账套过滤；关账服务在写入关闭状态前检查该账套该期间内是否仍有未过账凭证。

**Tech Stack:** FastAPI, Pydantic, SQLite JSON payload, React, TypeScript, Vite, node:test, pytest.

---

### Task 1: Backend Red Tests

**Files:**
- Create: `backend/tests/test_account_set_isolation_service.py`
- Create: `backend/tests/test_account_set_isolation_api.py`

- [ ] **Step 1: Write failing service tests**

Cover:
- 同月不同账套凭证在账簿汇总中互不串账。
- 一个账套关闭期间不影响另一个账套过账。
- 关账前若存在未过账凭证，返回 `409`。

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_account_set_isolation_service.py backend/tests/test_account_set_isolation_api.py -q
```

Expected: fail because voucher models and ledger builders do not yet support `account_set_id`.

### Task 2: Backend Implementation

**Files:**
- Modify: `backend/app/models/voucher_center.py`
- Modify: `backend/app/services/voucher_center_service.py`
- Modify: `backend/app/services/accounting_period_service.py`
- Modify: `backend/app/services/ledger_service.py`
- Modify: `backend/app/api/ledger.py`
- Modify: `backend/app/api/vouchers.py`

- [ ] **Step 1: Add `account_set_id` to voucher request/record**
- [ ] **Step 2: Filter voucher listing and ledger reads by account set**
- [ ] **Step 3: Validate period close by rejecting unposted vouchers**
- [ ] **Step 4: Add optional `account_set_id` query parameters to ledger/voucher APIs**

### Task 3: Frontend Integration

**Files:**
- Modify: `frontend/src/types/voucherCenter.ts`
- Modify: `frontend/src/types/ledger.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Modify: `frontend/src/components/LedgerPanel.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/tests/ledgerApi.test.mjs`
- Modify: `frontend/tests/ledgerPanel.test.mjs`

- [ ] **Step 1: Add API helper account set parameters**
- [ ] **Step 2: Add account-set selector to ledger panel**
- [ ] **Step 3: Load ledgers and period state for selected account set**

### Task 4: Docs And Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/01-mvp-design.md`
- Modify: `docs/02-api-design.md`

- [ ] **Step 1: Document MVP boundary**
- [ ] **Step 2: Run backend full tests**
- [ ] **Step 3: Run frontend tests and build**
- [ ] **Step 4: Verify live API and UI screenshots**
