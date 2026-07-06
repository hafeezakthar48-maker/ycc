# Voucher Posting Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为凭证中心增加“未过账 / 已过账 / 反过账”的状态模型、权限、审计和前端操作入口。

**Architecture:** 复用现有 SQLite 凭证中心，把过账状态作为 `VoucherCenterRecord` 的工作流字段保存到 `payload_json`。后端新增 `post_voucher` / `unpost_voucher` 服务和 API，沿用 `X-Actor-Id`、`authorize`、`record_audit_log` 模式；前端在凭证中心按钮区和凭证列表展示过账状态。

**Tech Stack:** FastAPI、Pydantic v2、SQLite、React、TypeScript、node:test。

---

### Task 1: 后端状态模型

**Files:**
- Modify: `backend/app/models/voucher_center.py`
- Modify: `backend/app/services/voucher_center_service.py`
- Test: `backend/tests/test_voucher_posting_service.py`

- [ ] **Step 1: Write failing service tests**

```python
def test_reviewed_voucher_can_be_posted_and_unposted():
    voucher = create_voucher(_request())
    reviewed = review_voucher(voucher.id, "财务主管")
    posted = post_voucher(reviewed.id, "财务主管")
    assert posted.posting_status == "posted"
    assert posted.posted_by == "财务主管"
    unposted = unpost_voucher(posted.id)
    assert unposted.posting_status == "unposted"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_voucher_posting_service.py -q`
Expected: FAIL because posting functions and fields do not exist.

- [ ] **Step 3: Implement minimal service behavior**

Add default fields `posting_status="unposted"`, `posted_by=None`, `posted_at=None`. Allow posting only reviewed vouchers; block draft posting, duplicate posting, unposting non-posted vouchers, and unreviewing posted vouchers.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_voucher_posting_service.py -q`
Expected: PASS.

### Task 2: API 权限与审计

**Files:**
- Modify: `backend/app/api/vouchers.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Test: `backend/tests/test_voucher_posting_api.py`

- [ ] **Step 1: Write failing API tests**

```python
def test_post_and_unpost_endpoints_require_permission_and_record_audit():
    post_response = client.post(f"/api/v1/vouchers/center/{voucher_id}/post", json={"operator": "财务主管"})
    assert post_response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_voucher_posting_api.py -q`
Expected: FAIL with 404 or missing permission.

- [ ] **Step 3: Implement API**

Expose `POST /api/v1/vouchers/center/{voucher_id}/post` and `/unpost`, add `voucher.post` and `voucher.unpost` permissions to finance manager, and record `voucher.post` / `voucher.unpost` audit events.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_voucher_posting_api.py -q`
Expected: PASS.

### Task 3: 前端接入

**Files:**
- Modify: `frontend/src/types/voucherCenter.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Modify: `frontend/src/components/VoucherCenterPanel.tsx`
- Test: `frontend/tests/voucherPostingPanel.test.mjs`

- [ ] **Step 1: Write failing frontend tests**

```js
assert.match(panel, /postVoucherCenterRecord/);
assert.match(panel, /unpostVoucherCenterRecord/);
assert.match(panel, /posting_status/);
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend; node tests/voucherPostingPanel.test.mjs`
Expected: FAIL because UI and API helper do not exist.

- [ ] **Step 3: Implement frontend**

Add posting status fields, helper functions, buttons and list labels.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend; node tests/voucherPostingPanel.test.mjs`
Expected: PASS.

### Task 4: 文档与验证

**Files:**
- Modify: `README.md`
- Modify: `docs/01-mvp-design.md`
- Modify: `docs/02-api-design.md`

- [ ] **Step 1: Document state boundary**

Document that posted status is a workflow state only; it does not yet create formal immutable ledger postings.

- [ ] **Step 2: Run full verification**

Run:
```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend/tests
cd frontend
npm run test:nav
npm run build
```

Expected: tests and build pass; existing Vite chunk warning may remain.
