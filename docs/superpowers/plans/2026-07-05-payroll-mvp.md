# Payroll MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 AI 财务中心落地工资管理 MVP，覆盖工资计算、社保、公积金、个税计算和工资分析。

**Architecture:** 后端新增工资模型、计算服务和 `/api/v1/payroll` 路由，复用账套校验、权限控制、模块注册和审计日志。前端新增 `PayrollPanel`，通过 dashboard API helper 调用工资计算接口，并在财务中心固定资产之后展示工资摘要、员工明细和部门分析。

**Tech Stack:** FastAPI, Pydantic, pytest, React, TypeScript, Vite, node:test, 系统 Chrome CDP 视觉验证。

---

### Task 1: 后端工资计算服务

**Files:**
- Create: `backend/app/models/payroll.py`
- Create: `backend/app/services/payroll_service.py`
- Test: `backend/tests/test_payroll_service.py`

- [ ] **Step 1: Write the failing service tests**

新增测试覆盖单人工资、社保、公积金、个税、实发工资、企业成本和部门分析。

- [ ] **Step 2: Run service tests to verify RED**

Run: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_payroll_service.py -q`

Expected: fails because payroll model/service do not exist.

- [ ] **Step 3: Implement models and calculation service**

实现 `PayrollCalculateRequest`、`PayrollEmployeeInput`、`PayrollEmployeeResult`、`PayrollSummary`、`PayrollDepartmentSummary`、`PayrollCalculationResponse`。计算公式使用 MVP 简化口径：员工社保 10.5%，企业社保 26.3%，公积金个人/企业各 7%，个税基本扣除 5000 元，月度综合所得税率表按应纳税所得额计算。

- [ ] **Step 4: Run service tests to verify GREEN**

Run: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_payroll_service.py -q`

Expected: all payroll service tests pass.

### Task 2: 后端 API、权限与模块注册

**Files:**
- Create: `backend/app/api/payroll.py`
- Modify: `backend/app/api/router_registry.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Test: `backend/tests/test_payroll_api.py`

- [ ] **Step 1: Write failing API tests**

新增测试覆盖 `POST /api/v1/payroll/calculate`、权限通过、权限拒绝、审计日志和财务中心模块注册。

- [ ] **Step 2: Run API tests to verify RED**

Run: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_payroll_api.py -q`

Expected: fails with 404 and missing registry entries.

- [ ] **Step 3: Implement API and governance wiring**

Route prefix: `/api/v1/payroll`。读取和计算使用 `payroll.calculate` 权限，成功与拒绝都记录 `module_id="finance-center"` 的 `payroll.calculate` 审计日志。Finance center registry adds `/api/v1/payroll` and `payroll.calculate`.

- [ ] **Step 4: Run API tests to verify GREEN**

Run: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_payroll_api.py -q`

Expected: all payroll API tests pass.

### Task 3: 前端工资管理面板

**Files:**
- Create: `frontend/src/types/payroll.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/PayrollPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Modify: `frontend/src/styles.css`
- Test: `frontend/tests/payrollApi.test.mjs`
- Test: `frontend/tests/payrollPanel.test.mjs`

- [ ] **Step 1: Write failing frontend tests**

`payrollApi.test.mjs` checks helper URL, method, headers and returned totals. `payrollPanel.test.mjs` checks DashboardLayout imports/renders `PayrollPanel`, and panel contains `payroll-panel`, `calculatePayroll`, employee table and department analysis.

- [ ] **Step 2: Run frontend tests to verify RED**

Run: `node tests/payrollApi.test.mjs` and `node tests/payrollPanel.test.mjs`

Expected: fails because helper and panel do not exist.

- [ ] **Step 3: Implement types, API helper, panel and styles**

Use a dense finance operations UI: summary cards, editable employee inputs, calculation button, employee payroll table and department analysis table. Avoid nested cards and keep mobile layout single column.

- [ ] **Step 4: Run frontend tests to verify GREEN**

Run: `node tests/payrollApi.test.mjs` and `node tests/payrollPanel.test.mjs`

Expected: both pass.

### Task 4: 文档、导航与完整验证

**Files:**
- Modify: `frontend/src/navigation/osModules.json`
- Modify: `frontend/tests/osModules.test.mjs`
- Modify: `frontend/package.json`
- Modify: `README.md`
- Modify: `docs/01-mvp-design.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

- [ ] **Step 1: Update navigation and docs**

Finance center items add `{ "label": "工资管理", "anchor": "payroll-panel" }` and `nextIntegration` advances to报表增强。Docs describe payroll MVP boundary: simplified calculation rules, not a payroll declaration or bank payment system.

- [ ] **Step 2: Run full verification**

Run:
`.\backend\.venv\Scripts\python.exe -m pytest backend/tests -q`
`npm run test:nav`
`npm run build`

Expected: backend and frontend tests pass; Vite may keep existing chunk-size warning.

- [ ] **Step 3: Browser visual verification**

Capture desktop and mobile screenshots of `#payroll-panel` into `output/playwright/payroll-desktop.png` and `output/playwright/payroll-mobile.png`, then inspect that summary cards, employee table and department analysis do not overlap or overflow incoherently.
