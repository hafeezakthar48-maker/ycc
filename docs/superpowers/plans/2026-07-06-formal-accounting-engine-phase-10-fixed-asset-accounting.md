# 正式核算引擎十期 固定资产正式核算 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有固定资产台账 MVP 升级为正式固定资产核算模块，支持资产卡片、折旧、减值、处置和正式分录生成。  
**Architecture:** 新增 `fixed_asset_accounting` 服务作为正式核算层，现有 `fixed_asset_service` 继续承载资产录入和生命周期动作。正式资产核算层从资产卡片和期间动作生成不可变正式分录，并将折旧、减值、清理和处置损益接入期末处理。  
**Tech Stack:** FastAPI、Pydantic、SQLite、Decimal、pytest、React、TypeScript、Vite、Node test runner。

---

## 前置条件

- 一期正式分录服务可创建幂等来源分录。
- 三期辅助核算支持 `asset`、`department`、`project` 维度。
- 四期期末处理支持折旧动作注册和幂等执行。
- 现有固定资产 MVP 已有新增、折旧、出售、报废、盘点接口。

本期不做复杂融资租赁准则、不做资产评估机构接口、不做税务系统自动申报、不处理集团资产跨法人调拨。

## 核算决策

- 固定资产卡片是资产核算主数据，正式分录是账务事实。
- 固定资产入账分录默认借记 `1601 固定资产`，贷记 `1002 银行存款`、`2202 应付账款` 或来源凭证科目。
- 月折旧默认借记费用或成本科目，贷记 `1602 累计折旧`。
- 减值准备借记 `6701 资产减值损失`，贷记 `1603 固定资产减值准备`。
- 处置进入 `1606 固定资产清理`，最终差额结转营业外收入或营业外支出。
- 折旧和处置分录通过 source key 幂等生成，不允许重复计提。
- 已关闭期间不能新增资产入账、折旧、减值或处置分录。

## 文件结构

- Create: `backend/app/models/fixed_asset_accounting.py`
- Create: `backend/app/services/fixed_asset_accounting_service.py`
- Create: `backend/app/api/fixed_asset_accounting.py`
- Modify: `backend/app/services/fixed_asset_service.py`
- Modify: `backend/app/services/period_close_service.py`
- Modify: `backend/app/api/router_registry.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Create: `backend/tests/test_fixed_asset_accounting_service.py`
- Create: `backend/tests/test_fixed_asset_accounting_api.py`
- Modify: `backend/tests/test_period_close_service.py`
- Create: `frontend/src/types/fixedAssetAccounting.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Modify: `frontend/src/components/FixedAssetPanel.tsx`
- Create: `frontend/tests/fixedAssetAccountingApi.test.mjs`
- Modify: `README.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

## Task 1: 正式资产卡片模型

**Files:**
- Create: `backend/app/models/fixed_asset_accounting.py`
- Test: `backend/tests/test_fixed_asset_accounting_service.py`

- [ ] **Step 1: Write failing model test**

```python
from decimal import Decimal

from app.models.fixed_asset_accounting import FormalAssetCardCreate


def test_formal_asset_card_uses_decimal_original_cost():
    card = FormalAssetCardCreate(
        account_set_id="default",
        asset_code="FA-2026-001",
        asset_name="生产设备A",
        category="机器设备",
        acquisition_date="2026-01-10",
        original_cost=Decimal("120000.00"),
        salvage_value=Decimal("6000.00"),
        useful_life_months=60,
        department_id="dept-prod",
        asset_account_code="1601",
        depreciation_account_code="1602",
        expense_account_code="5101",
    )

    assert card.original_cost == Decimal("120000.00")
    assert card.useful_life_months == 60
```

- [ ] **Step 2: Run failing test**

```powershell
python -m pytest backend/tests/test_fixed_asset_accounting_service.py::test_formal_asset_card_uses_decimal_original_cost -v
```

Expected result: fails because formal fixed asset models do not exist.

- [ ] **Step 3: Create models**

```python
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


AssetAccountingStatus = Literal["draft", "active", "fully_depreciated", "disposed"]


class FormalAssetCardCreate(BaseModel):
    account_set_id: str
    asset_code: str
    asset_name: str
    category: str
    acquisition_date: str
    original_cost: Decimal = Field(gt=Decimal("0"))
    salvage_value: Decimal = Field(ge=Decimal("0"))
    useful_life_months: int = Field(gt=0)
    department_id: str
    asset_account_code: str = "1601"
    depreciation_account_code: str = "1602"
    expense_account_code: str


class FormalAssetCard(FormalAssetCardCreate):
    asset_card_id: str
    accumulated_depreciation: Decimal = Decimal("0.00")
    impairment_amount: Decimal = Decimal("0.00")
    net_book_value: Decimal
    status: AssetAccountingStatus = "active"
```

- [ ] **Step 4: Run model test**

```powershell
python -m pytest backend/tests/test_fixed_asset_accounting_service.py::test_formal_asset_card_uses_decimal_original_cost -v
```

Expected result: test passes.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/models/fixed_asset_accounting.py backend/tests/test_fixed_asset_accounting_service.py
git commit -m "feat: add formal fixed asset card models"
```

## Task 2: 资产入账正式分录

**Files:**
- Create: `backend/app/services/fixed_asset_accounting_service.py`
- Modify: `backend/app/services/accounting_service.py`
- Test: `backend/tests/test_fixed_asset_accounting_service.py`

- [ ] **Step 1: Add failing capitalization test**

```python
from app.services.fixed_asset_accounting_service import capitalize_asset


def test_capitalize_asset_creates_formal_journal_entry():
    result = capitalize_asset(
        account_set_id="default",
        asset_code="FA-2026-001",
        period="2026-01",
        credit_account_code="2202",
        actor_id="asset-user",
    )

    assert result.journal_entry_id.startswith("je-")
    assert result.source_id == "fixed_asset_capitalize:default:FA-2026-001"
```

- [ ] **Step 2: Implement capitalization service**

```python
def capitalize_asset(account_set_id: str, asset_code: str, period: str, credit_account_code: str, actor_id: str):
    card = get_asset_card(account_set_id, asset_code)
    source_id = f"fixed_asset_capitalize:{account_set_id}:{asset_code}"
    return create_journal_entry(
        account_set_id=account_set_id,
        period=period,
        entry_date=f"{period}-01",
        source_type="fixed_asset_capitalization",
        source_id=source_id,
        lines=[
            {"account_code": card.asset_account_code, "debit": card.original_cost, "credit": Decimal("0.00"), "dimension_type": "asset", "dimension_id": card.asset_code},
            {"account_code": credit_account_code, "debit": Decimal("0.00"), "credit": card.original_cost, "dimension_type": "asset", "dimension_id": card.asset_code},
        ],
        created_by=actor_id,
    )
```

- [ ] **Step 3: Run capitalization test**

```powershell
python -m pytest backend/tests/test_fixed_asset_accounting_service.py::test_capitalize_asset_creates_formal_journal_entry -v
```

Expected result: capitalization creates one balanced formal journal entry.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/services/fixed_asset_accounting_service.py backend/app/services/accounting_service.py backend/tests/test_fixed_asset_accounting_service.py
git commit -m "feat: capitalize fixed assets to formal ledger"
```

## Task 3: 月折旧与期末处理接入

**Files:**
- Modify: `backend/app/services/fixed_asset_accounting_service.py`
- Modify: `backend/app/services/period_close_service.py`
- Test: `backend/tests/test_fixed_asset_accounting_service.py`
- Test: `backend/tests/test_period_close_service.py`

- [ ] **Step 1: Add failing depreciation test**

```python
from decimal import Decimal

from app.services.fixed_asset_accounting_service import calculate_monthly_depreciation


def test_calculate_monthly_depreciation_uses_straight_line():
    amount = calculate_monthly_depreciation(
        original_cost=Decimal("120000.00"),
        salvage_value=Decimal("6000.00"),
        useful_life_months=60,
    )

    assert amount == Decimal("1900.00")
```

- [ ] **Step 2: Implement depreciation calculation**

```python
def calculate_monthly_depreciation(original_cost: Decimal, salvage_value: Decimal, useful_life_months: int) -> Decimal:
    depreciable_amount = original_cost - salvage_value
    return (depreciable_amount / Decimal(useful_life_months)).quantize(Decimal("0.01"))
```

- [ ] **Step 3: Implement period close action**

```python
def run_fixed_asset_depreciation(account_set_id: str, period: str, actor_id: str):
    entries = []
    for card in list_active_asset_cards(account_set_id):
        amount = calculate_monthly_depreciation(card.original_cost, card.salvage_value, card.useful_life_months)
        source_id = f"fixed_asset_depreciation:{account_set_id}:{period}:{card.asset_code}"
        entries.append(create_depreciation_entry(card, amount, period, source_id, actor_id))
    return entries
```

- [ ] **Step 4: Run close tests**

```powershell
python -m pytest backend/tests/test_fixed_asset_accounting_service.py backend/tests/test_period_close_service.py -v
```

Expected result: depreciation is calculated once per active card and period.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/fixed_asset_accounting_service.py backend/app/services/period_close_service.py backend/tests/test_fixed_asset_accounting_service.py backend/tests/test_period_close_service.py
git commit -m "feat: post formal fixed asset depreciation"
```

## Task 4: 减值、处置和处置损益

**Files:**
- Modify: `backend/app/models/fixed_asset_accounting.py`
- Modify: `backend/app/services/fixed_asset_accounting_service.py`
- Test: `backend/tests/test_fixed_asset_accounting_service.py`

- [ ] **Step 1: Add impairment and disposal tests**

```python
from decimal import Decimal

from app.services.fixed_asset_accounting_service import record_asset_impairment, dispose_asset


def test_record_asset_impairment_posts_loss_and_allowance():
    entry = record_asset_impairment("default", "FA-2026-001", "2026-06", Decimal("3000.00"), "asset-user")
    assert entry.source_id == "fixed_asset_impairment:default:2026-06:FA-2026-001"


def test_dispose_asset_posts_clearance_and_gain_or_loss():
    result = dispose_asset("default", "FA-2026-001", "2026-07", Decimal("80000.00"), "asset-user")
    assert result.asset_status == "disposed"
    assert result.clearance_account_code == "1606"
```

- [ ] **Step 2: Implement impairment entry**

```python
def record_asset_impairment(account_set_id: str, asset_code: str, period: str, amount: Decimal, actor_id: str):
    source_id = f"fixed_asset_impairment:{account_set_id}:{period}:{asset_code}"
    return create_journal_entry(
        account_set_id=account_set_id,
        period=period,
        entry_date=f"{period}-28",
        source_type="fixed_asset_impairment",
        source_id=source_id,
        lines=[
            {"account_code": "6701", "debit": amount, "credit": Decimal("0.00")},
            {"account_code": "1603", "debit": Decimal("0.00"), "credit": amount},
        ],
        created_by=actor_id,
    )
```

- [ ] **Step 3: Implement disposal workflow**

Required entries:
- Transfer original cost: debit `1606`, credit `1601`.
- Transfer accumulated depreciation: debit `1602`, credit `1606`.
- Transfer impairment allowance: debit `1603`, credit `1606`.
- Record sale proceeds: debit `1002` or `1122`, credit `1606`.
- Close gain or loss: credit `6301 营业外收入` or debit `6711 营业外支出`.

- [ ] **Step 4: Run impairment and disposal tests**

```powershell
python -m pytest backend/tests/test_fixed_asset_accounting_service.py -v
```

Expected result: impairment and disposal tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/models/fixed_asset_accounting.py backend/app/services/fixed_asset_accounting_service.py backend/tests/test_fixed_asset_accounting_service.py
git commit -m "feat: account for fixed asset impairment and disposal"
```

## Task 5: API、权限、前端和文档

**Files:**
- Create: `backend/app/api/fixed_asset_accounting.py`
- Modify: `backend/app/api/router_registry.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Create: `backend/tests/test_fixed_asset_accounting_api.py`
- Create: `frontend/src/types/fixedAssetAccounting.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Modify: `frontend/src/components/FixedAssetPanel.tsx`
- Create: `frontend/tests/fixedAssetAccountingApi.test.mjs`
- Modify: `README.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

- [ ] **Step 1: Implement API endpoints**

Endpoints:
- `GET /api/v1/fixed-asset-accounting/cards`
- `POST /api/v1/fixed-asset-accounting/capitalize`
- `POST /api/v1/fixed-asset-accounting/depreciation`
- `POST /api/v1/fixed-asset-accounting/impairment`
- `POST /api/v1/fixed-asset-accounting/disposal`

Permissions:
- `fixed_asset_accounting.read`
- `fixed_asset_accounting.post`
- `fixed_asset_accounting.impair`
- `fixed_asset_accounting.dispose`

Audit events:
- `fixed_asset_accounting.card.read`
- `fixed_asset_accounting.capitalize`
- `fixed_asset_accounting.depreciation.post`
- `fixed_asset_accounting.impairment.post`
- `fixed_asset_accounting.disposal.post`

- [ ] **Step 2: Add frontend fields**

Fixed asset panel must show:
- 正式入账状态。
- 累计折旧。
- 账面净值。
- 最近折旧期间。
- 处置状态。
- 正式分录号。

- [ ] **Step 3: Run regression**

```powershell
python -m pytest backend/tests/test_fixed_asset_accounting_service.py backend/tests/test_fixed_asset_accounting_api.py backend/tests/test_period_close_service.py backend/tests/test_fixed_asset_service.py
npm --prefix frontend test
npm --prefix frontend run build
```

Expected result: selected backend tests, frontend tests and build pass.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/api/fixed_asset_accounting.py backend/app/api/router_registry.py backend/app/services/system_admin_service.py backend/app/services/module_registry_service.py backend/tests/test_fixed_asset_accounting_api.py frontend/src/types/fixedAssetAccounting.ts frontend/src/services/dashboardApi.ts frontend/src/components/FixedAssetPanel.tsx frontend/tests/fixedAssetAccountingApi.test.mjs README.md docs/02-api-design.md docs/03-frd-v1.0.md
git commit -m "feat: expose formal fixed asset accounting"
```

## 验收标准

- 固定资产卡片可正式入账并生成不可变分录。
- 月折旧能按期间幂等生成正式分录。
- 减值准备能生成借记 `6701`、贷记 `1603` 的正式分录。
- 处置流程能生成清理、收入和处置损益分录。
- 固定资产面板显示正式入账、折旧和处置状态。
- 期间关闭后拒绝新增折旧、减值和处置。
- 权限与审计事件覆盖读取、入账、折旧、减值和处置。

## 风险控制

- 不修改历史正式分录，调整通过新分录完成。
- 折旧 source key 必须包含账套、期间和资产编码。
- 资产处置必须校验资产未处置且已正式入账。
- 所有金额使用 `Decimal` 并量化为两位小数。
- 现有固定资产 MVP 数据迁移前保留兼容读取。
