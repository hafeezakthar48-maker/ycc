# Fixed Assets MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 AI 财务中心落地固定资产台账 MVP，覆盖新增、自动折旧、报废、出售、盘点和摘要统计。

**Architecture:** 后端新增固定资产模型、内存服务和 `/api/v1/fixed-assets` 路由，复用账套校验、权限控制和审计日志。前端新增 `FixedAssetPanel`，通过 dashboard API helper 读取与操作固定资产，并接入财务中心导航和文档。

**Tech Stack:** FastAPI, Pydantic, pytest, React, TypeScript, Vite, node:test, 系统 Chrome CDP 视觉验证。

---

### Task 1: 后端固定资产服务

**Files:**
- Create: `backend/app/models/fixed_asset.py`
- Create: `backend/app/services/fixed_asset_service.py`
- Test: `backend/tests/test_fixed_asset_service.py`

- [ ] **Step 1: Write the failing service tests**

```python
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.fixed_asset import FixedAssetCreateRequest, FixedAssetInventoryRequest, FixedAssetSaleRequest
from app.services.fixed_asset_service import (
    create_fixed_asset,
    dispose_fixed_asset,
    inventory_fixed_asset,
    list_fixed_assets,
    reset_fixed_asset_store,
    run_monthly_depreciation,
    sell_fixed_asset,
)


@pytest.fixture(autouse=True)
def isolated_assets():
    reset_fixed_asset_store()


def _asset() -> FixedAssetCreateRequest:
    return FixedAssetCreateRequest(
        account_set_id="default",
        name="自动贴标机",
        category="生产设备",
        acquisition_date="2026-01-15",
        original_cost=Decimal("120000.00"),
        salvage_value=Decimal("12000.00"),
        useful_life_months=60,
        location="一号仓",
        custodian="设备管理员",
    )


def test_create_asset_calculates_monthly_depreciation_and_summary():
    asset = create_fixed_asset(_asset())
    payload = list_fixed_assets("default")
    assert asset.asset_code.startswith("FA-202601-")
    assert asset.monthly_depreciation == Decimal("1800.00")
    assert payload.summary.asset_count == 1
    assert payload.summary.original_cost_total == Decimal("120000.00")
    assert payload.summary.net_book_value_total == Decimal("120000.00")


def test_monthly_depreciation_is_idempotent_and_updates_net_book_value():
    asset = create_fixed_asset(_asset())
    result = run_monthly_depreciation("2026-06", "default", "财务主管")
    repeat = run_monthly_depreciation("2026-06", "default", "财务主管")
    updated = list_fixed_assets("default").assets[0]
    assert result.depreciated_count == 1
    assert result.total_depreciation == Decimal("1800.00")
    assert repeat.depreciated_count == 0
    assert updated.accumulated_depreciation == Decimal("1800.00")
    assert updated.net_book_value == Decimal("118200.00")
    assert updated.last_depreciated_period == "2026-06"


def test_dispose_and_sell_close_asset_lifecycle():
    disposed = dispose_fixed_asset(create_fixed_asset(_asset()).id, "2026-06-30", "损坏报废", "财务主管")
    sold_asset = create_fixed_asset(_asset().model_copy(update={"name": "测试设备", "original_cost": Decimal("60000.00")}))
    sold = sell_fixed_asset(
        sold_asset.id,
        FixedAssetSaleRequest(sale_date="2026-06-30", sale_amount=Decimal("58000.00"), reason="更新换代", operator="财务主管"),
    )
    assert disposed.status == "disposed"
    assert sold.status == "sold"
    assert sold.sale_gain_or_loss == Decimal("-2000.00")
    with pytest.raises(HTTPException):
        run_monthly_depreciation("2026-07", "default", "财务主管")


def test_inventory_updates_location_condition_and_checked_by():
    asset = create_fixed_asset(_asset())
    checked = inventory_fixed_asset(
        asset.id,
        FixedAssetInventoryRequest(
            inventory_date="2026-06-30",
            location="二号仓",
            custodian="资产专员",
            condition="正常",
            operator="盘点员",
            note="已贴标签",
        ),
    )
    assert checked.location == "二号仓"
    assert checked.custodian == "资产专员"
    assert checked.inventory_status == "checked"
    assert checked.last_inventory_by == "盘点员"
```

- [ ] **Step 2: Run service tests to verify RED**

Run: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_fixed_asset_service.py -q`

Expected: fails because `app.models.fixed_asset` and `app.services.fixed_asset_service` do not exist.

- [ ] **Step 3: Implement models and service**

Implement Pydantic models with strict fields, date validation, Decimal money fields, status literals, list response, depreciation result, and reset helper. Service stores records in memory, validates account set, auto-generates `FA-YYYYMM-0001`, calculates straight-line monthly depreciation as `(original_cost - salvage_value) / useful_life_months`, prevents duplicate depreciation by period, and rejects depreciation when no active assets exist.

- [ ] **Step 4: Run service tests to verify GREEN**

Run: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_fixed_asset_service.py -q`

Expected: all fixed asset service tests pass.

### Task 2: 后端 API、权限与模块注册

**Files:**
- Create: `backend/app/api/fixed_assets.py`
- Modify: `backend/app/api/router_registry.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Test: `backend/tests/test_fixed_asset_api.py`

- [ ] **Step 1: Write failing API tests**

Create tests that call `GET /api/v1/fixed-assets`, `POST /api/v1/fixed-assets`, `POST /api/v1/fixed-assets/depreciation/run`, `POST /api/v1/fixed-assets/{id}/inventory`, and verify finance-manager access plus auditor denial for write operations.

- [ ] **Step 2: Run API tests to verify RED**

Run: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_fixed_asset_api.py -q`

Expected: fails with 404 for missing routes.

- [ ] **Step 3: Implement API route and governance wiring**

Route prefix: `/api/v1/fixed-assets`. Required permissions: `fixed_asset.read`, `fixed_asset.write`, `fixed_asset.depreciate`, `fixed_asset.dispose`, `fixed_asset.inventory`. All successful and denied operations record `module_id="finance-center"` audit logs with asset id, account set id, period or operation metadata. Finance center registry adds `/api/v1/fixed-assets` and audit events.

- [ ] **Step 4: Run API tests to verify GREEN**

Run: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_fixed_asset_api.py -q`

Expected: all API tests pass.

### Task 3: 前端固定资产面板

**Files:**
- Create: `frontend/src/types/fixedAsset.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/FixedAssetPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Modify: `frontend/src/styles.css`
- Test: `frontend/tests/fixedAssetApi.test.mjs`
- Test: `frontend/tests/fixedAssetPanel.test.mjs`

- [ ] **Step 1: Write failing frontend tests**

`fixedAssetApi.test.mjs` checks helper URLs and methods for list, create, depreciation run, inventory, dispose, and sell. `fixedAssetPanel.test.mjs` checks DashboardLayout imports/renders `FixedAssetPanel`, and the panel contains `fixed-asset-panel`, `runMonthlyDepreciation`, `inventoryFixedAsset`, `disposeFixedAsset`, and `sellFixedAsset`.

- [ ] **Step 2: Run frontend tests to verify RED**

Run: `node tests/fixedAssetApi.test.mjs` and `node tests/fixedAssetPanel.test.mjs`

Expected: fails because helpers and panel do not exist.

- [ ] **Step 3: Implement types, API helpers, panel and styles**

Use a dense operational panel: summary cards, asset table, compact create form, lifecycle buttons, depreciation button, and inventory form. Avoid nested cards; reuse existing `panel`, `voucher-table`, `ledger-summary-grid`, and add scoped fixed-asset classes only where needed.

- [ ] **Step 4: Run frontend tests to verify GREEN**

Run: `node tests/fixedAssetApi.test.mjs` and `node tests/fixedAssetPanel.test.mjs`

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

Finance center items add `{ "label": "固定资产", "anchor": "fixed-asset-panel" }`. `nextIntegration` advances to salary management. Docs describe fixed asset MVP boundary: local in-memory台账、直线法折旧、生命周期状态、盘点记录，不生成正式总账凭证。

- [ ] **Step 2: Run full verification**

Run:
`.\backend\.venv\Scripts\python.exe -m pytest backend/tests -q`
`npm run test:nav`
`npm run build`

Expected: backend and frontend tests pass; Vite may keep existing chunk-size warning.

- [ ] **Step 3: Browser visual verification**

Capture desktop and mobile screenshots of `#fixed-asset-panel` into `output/playwright/fixed-assets-desktop.png` and `output/playwright/fixed-assets-mobile.png`, then inspect that summary cards, table, form and buttons do not overlap or overflow incoherently.
