# 正式核算引擎十二期 存货与成本核算 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立正式存货台账、入库出库、移动加权成本、销售成本结转、存货跌价准备和库存账实核对能力。
**Architecture:** 新增 `inventory_accounting` 模型和服务，库存业务流水作为数量事实，正式分录作为金额事实。系统按 SKU、仓库和账套维护库存移动流水，采用移动加权平均成本计算出库成本，并通过正式分录结转主营业务成本、存货跌价和盘盈盘亏。
**Tech Stack:** FastAPI、Pydantic、SQLite、Decimal、pytest、React、TypeScript、Vite、Node test runner。

---

## 前置条件

- 一期正式分录服务可创建幂等分录。
- 三期辅助核算支持 `sku`、`warehouse`、`platform` 和 `project` 维度。
- 四期期末处理可注册成本结转、跌价准备和盘点差异动作。
- 八期应付模块可承接采购挂账。
- 九期银行资金模块可承接采购付款。

本期不做 WMS 实时集成，不做批次保质期管理，不做生产制造 BOM 和工序成本，不做跨境电商平台真实 API 抓单。

## 核算决策

- 存货入库借记 `1405 库存商品`，贷记 `2202 应付账款`、`1002 银行存款` 或暂估科目。
- 销售出库按移动加权成本借记 `6401 主营业务成本`，贷记 `1405 库存商品`。
- 移动加权成本在每次入库后重新计算：`新单位成本 = (原库存金额 + 本次入库金额) / (原库存数量 + 本次入库数量)`。
- 销售退货按原销售出库成本回冲；无法定位原出库时按当前移动加权成本回冲并记录风险提示。
- 存货跌价准备借记 `6701 资产减值损失`，贷记 `1471 存货跌价准备`。
- 盘盈盘亏先进入 `1901 待处理财产损溢`，审批后转入损益或责任人往来。
- 已关闭期间不能新增库存入库、出库、成本结转、跌价和盘点差异分录。

## 文件结构

- Create: `backend/app/models/inventory_accounting.py`
- Create: `backend/app/services/inventory_accounting_service.py`
- Create: `backend/app/api/inventory_accounting.py`
- Modify: `backend/app/services/ecommerce_profit_service.py`
- Modify: `backend/app/services/period_close_service.py`
- Modify: `backend/app/services/accounting_service.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Modify: `backend/app/api/router_registry.py`
- Create: `backend/tests/test_inventory_accounting_service.py`
- Create: `backend/tests/test_inventory_accounting_api.py`
- Modify: `backend/tests/test_period_close_service.py`
- Create: `frontend/src/types/inventoryAccounting.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/InventoryAccountingPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Create: `frontend/tests/inventoryAccountingApi.test.mjs`
- Create: `frontend/tests/inventoryAccountingPanel.test.mjs`
- Modify: `README.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

## Task 1: SKU、仓库和库存移动模型

**Files:**
- Create: `backend/app/models/inventory_accounting.py`
- Test: `backend/tests/test_inventory_accounting_service.py`

- [ ] **Step 1: Write failing model test**

```python
from decimal import Decimal

from app.models.inventory_accounting import InventoryMovementCreate


def test_inventory_movement_keeps_quantity_and_amount():
    movement = InventoryMovementCreate(
        account_set_id="default",
        sku_id="SKU-001",
        warehouse_id="WH-SH",
        movement_date="2026-06-10",
        movement_type="purchase_receipt",
        quantity=Decimal("10"),
        amount=Decimal("1000.00"),
        source_id="po-001",
    )

    assert movement.quantity == Decimal("10")
    assert movement.amount == Decimal("1000.00")
```

- [ ] **Step 2: Run failing test**

```powershell
python -m pytest backend/tests/test_inventory_accounting_service.py::test_inventory_movement_keeps_quantity_and_amount -v
```

Expected result: fails because inventory accounting models do not exist.

- [ ] **Step 3: Create models**

```python
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


InventoryMovementType = Literal["purchase_receipt", "sales_issue", "sales_return", "purchase_return", "adjustment_in", "adjustment_out"]


class InventoryMovementCreate(BaseModel):
    account_set_id: str
    sku_id: str
    warehouse_id: str
    movement_date: str
    movement_type: InventoryMovementType
    quantity: Decimal = Field(gt=Decimal("0"))
    amount: Decimal = Field(ge=Decimal("0"))
    source_id: str


class InventoryMovement(InventoryMovementCreate):
    movement_id: str
    unit_cost: Decimal
    journal_entry_id: str | None = None


class InventoryBalance(BaseModel):
    account_set_id: str
    sku_id: str
    warehouse_id: str
    quantity: Decimal
    amount: Decimal
    moving_average_cost: Decimal
```

- [ ] **Step 4: Run model test**

```powershell
python -m pytest backend/tests/test_inventory_accounting_service.py::test_inventory_movement_keeps_quantity_and_amount -v
```

Expected result: test passes.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/models/inventory_accounting.py backend/tests/test_inventory_accounting_service.py
git commit -m "feat: add inventory movement models"
```

## Task 2: 移动加权平均成本

**Files:**
- Create: `backend/app/services/inventory_accounting_service.py`
- Test: `backend/tests/test_inventory_accounting_service.py`

- [ ] **Step 1: Add failing weighted average test**

```python
from decimal import Decimal

from app.services.inventory_accounting_service import calculate_moving_average_cost


def test_calculate_moving_average_cost_after_purchase_receipt():
    result = calculate_moving_average_cost(
        existing_quantity=Decimal("10"),
        existing_amount=Decimal("1000.00"),
        receipt_quantity=Decimal("10"),
        receipt_amount=Decimal("1200.00"),
    )

    assert result == Decimal("110.00")
```

- [ ] **Step 2: Implement calculation**

```python
from decimal import Decimal


def calculate_moving_average_cost(existing_quantity: Decimal, existing_amount: Decimal, receipt_quantity: Decimal, receipt_amount: Decimal) -> Decimal:
    total_quantity = existing_quantity + receipt_quantity
    if total_quantity <= Decimal("0"):
        return Decimal("0.00")
    return ((existing_amount + receipt_amount) / total_quantity).quantize(Decimal("0.01"))
```

- [ ] **Step 3: Run cost test**

```powershell
python -m pytest backend/tests/test_inventory_accounting_service.py::test_calculate_moving_average_cost_after_purchase_receipt -v
```

Expected result: moving average cost equals `110.00`.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/services/inventory_accounting_service.py backend/tests/test_inventory_accounting_service.py
git commit -m "feat: calculate moving average inventory cost"
```

## Task 3: 采购入库和正式分录

**Files:**
- Modify: `backend/app/services/inventory_accounting_service.py`
- Test: `backend/tests/test_inventory_accounting_service.py`

- [ ] **Step 1: Add failing purchase receipt test**

```python
from decimal import Decimal

from app.services.inventory_accounting_service import post_purchase_receipt


def test_post_purchase_receipt_debits_inventory_and_credits_payable():
    result = post_purchase_receipt(
        account_set_id="default",
        sku_id="SKU-001",
        warehouse_id="WH-SH",
        period="2026-06",
        quantity=Decimal("10"),
        amount=Decimal("1000.00"),
        supplier_id="SUP-001",
        actor_id="inventory-user",
    )

    assert result.source_id == "inventory_receipt:default:2026-06:SKU-001:SUP-001"
```

- [ ] **Step 2: Implement purchase receipt entry**

```python
def build_purchase_receipt_lines(amount: Decimal, sku_id: str, warehouse_id: str, supplier_id: str):
    return [
        {"account_code": "1405", "debit": amount, "credit": Decimal("0.00"), "dimension_type": "sku", "dimension_id": sku_id},
        {"account_code": "2202", "debit": Decimal("0.00"), "credit": amount, "dimension_type": "supplier", "dimension_id": supplier_id},
    ]
```

- [ ] **Step 3: Run purchase receipt test**

```powershell
python -m pytest backend/tests/test_inventory_accounting_service.py::test_post_purchase_receipt_debits_inventory_and_credits_payable -v
```

Expected result: purchase receipt creates inventory movement and balanced journal entry.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/services/inventory_accounting_service.py backend/tests/test_inventory_accounting_service.py
git commit -m "feat: post inventory purchase receipts"
```

## Task 4: 销售出库和成本结转

**Files:**
- Modify: `backend/app/services/inventory_accounting_service.py`
- Modify: `backend/app/services/period_close_service.py`
- Test: `backend/tests/test_inventory_accounting_service.py`
- Test: `backend/tests/test_period_close_service.py`

- [ ] **Step 1: Add failing sales issue test**

```python
from decimal import Decimal

from app.services.inventory_accounting_service import post_sales_issue


def test_post_sales_issue_credits_inventory_and_debits_cogs():
    result = post_sales_issue(
        account_set_id="default",
        sku_id="SKU-001",
        warehouse_id="WH-SH",
        period="2026-06",
        quantity=Decimal("3"),
        actor_id="inventory-user",
    )

    assert result.cogs_account_code == "6401"
    assert result.journal_entry_id.startswith("je-")
```

- [ ] **Step 2: Implement sales issue lines**

```python
def build_sales_issue_lines(cost_amount: Decimal, sku_id: str, warehouse_id: str):
    return [
        {"account_code": "6401", "debit": cost_amount, "credit": Decimal("0.00"), "dimension_type": "sku", "dimension_id": sku_id},
        {"account_code": "1405", "debit": Decimal("0.00"), "credit": cost_amount, "dimension_type": "sku", "dimension_id": sku_id},
    ]
```

- [ ] **Step 3: Add negative inventory guard**

```python
def ensure_available_stock(balance, issue_quantity: Decimal):
    if balance.quantity < issue_quantity:
        raise ValueError("库存数量不足，不能结转销售成本")
```

- [ ] **Step 4: Run sales issue tests**

```powershell
python -m pytest backend/tests/test_inventory_accounting_service.py backend/tests/test_period_close_service.py -v
```

Expected result: cost issue posts only when stock is sufficient.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/inventory_accounting_service.py backend/app/services/period_close_service.py backend/tests/test_inventory_accounting_service.py backend/tests/test_period_close_service.py
git commit -m "feat: post inventory cost of goods sold"
```

## Task 5: 存货跌价和盘点差异

**Files:**
- Modify: `backend/app/models/inventory_accounting.py`
- Modify: `backend/app/services/inventory_accounting_service.py`
- Test: `backend/tests/test_inventory_accounting_service.py`

- [ ] **Step 1: Add falling price provision test**

```python
from decimal import Decimal

from app.services.inventory_accounting_service import record_inventory_impairment


def test_record_inventory_impairment_posts_allowance():
    entry = record_inventory_impairment("default", "SKU-001", "2026-06", Decimal("500.00"), "inventory-user")

    assert entry.source_id == "inventory_impairment:default:2026-06:SKU-001"
```

- [ ] **Step 2: Implement impairment entry**

```python
def record_inventory_impairment(account_set_id: str, sku_id: str, period: str, amount: Decimal, actor_id: str):
    source_id = f"inventory_impairment:{account_set_id}:{period}:{sku_id}"
    return create_journal_entry(
        account_set_id=account_set_id,
        period=period,
        entry_date=f"{period}-28",
        source_type="inventory_impairment",
        source_id=source_id,
        lines=[
            {"account_code": "6701", "debit": amount, "credit": Decimal("0.00"), "dimension_type": "sku", "dimension_id": sku_id},
            {"account_code": "1471", "debit": Decimal("0.00"), "credit": amount, "dimension_type": "sku", "dimension_id": sku_id},
        ],
        created_by=actor_id,
    )
```

- [ ] **Step 3: Add inventory count variance handling**

盘盈：借记 `1405 库存商品`，贷记 `1901 待处理财产损溢`。
盘亏：借记 `1901 待处理财产损溢`，贷记 `1405 库存商品`。
审批后：转入 `6711 营业外支出`、`6301 营业外收入` 或责任人往来科目。

- [ ] **Step 4: Run impairment and count tests**

```powershell
python -m pytest backend/tests/test_inventory_accounting_service.py -v
```

Expected result: impairment and count variance entries are balanced.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/models/inventory_accounting.py backend/app/services/inventory_accounting_service.py backend/tests/test_inventory_accounting_service.py
git commit -m "feat: account for inventory impairment and count variance"
```

## Task 6: API、前端和文档

**Files:**
- Create: `backend/app/api/inventory_accounting.py`
- Modify: `backend/app/api/router_registry.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Create: `backend/tests/test_inventory_accounting_api.py`
- Create: `frontend/src/types/inventoryAccounting.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/InventoryAccountingPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Create: `frontend/tests/inventoryAccountingApi.test.mjs`
- Create: `frontend/tests/inventoryAccountingPanel.test.mjs`
- Modify: `README.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

- [ ] **Step 1: Implement endpoints**

Endpoints:
- `GET /api/v1/inventory-accounting/balances`
- `POST /api/v1/inventory-accounting/purchase-receipts`
- `POST /api/v1/inventory-accounting/sales-issues`
- `POST /api/v1/inventory-accounting/impairments`
- `POST /api/v1/inventory-accounting/count-variances`

Permissions:
- `inventory_accounting.read`
- `inventory_accounting.receipt`
- `inventory_accounting.issue`
- `inventory_accounting.impair`
- `inventory_accounting.count`

- [ ] **Step 2: Build frontend panel**

Panel must show:
- SKU 库存数量、金额和移动平均成本。
- 入库和出库流水。
- 销售成本结转状态。
- 跌价准备和盘点差异状态。

- [ ] **Step 3: Run regression**

```powershell
python -m pytest backend/tests/test_inventory_accounting_service.py backend/tests/test_inventory_accounting_api.py backend/tests/test_ecommerce_profit_service.py backend/tests/test_period_close_service.py
npm --prefix frontend test
npm --prefix frontend run build
```

Expected result: selected backend tests, frontend tests and build pass.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/api/inventory_accounting.py backend/app/api/router_registry.py backend/app/services/system_admin_service.py backend/app/services/module_registry_service.py backend/tests/test_inventory_accounting_api.py frontend/src/types/inventoryAccounting.ts frontend/src/services/dashboardApi.ts frontend/src/components/InventoryAccountingPanel.tsx frontend/src/components/DashboardLayout.tsx frontend/tests/inventoryAccountingApi.test.mjs frontend/tests/inventoryAccountingPanel.test.mjs README.md docs/02-api-design.md docs/03-frd-v1.0.md
git commit -m "feat: expose inventory accounting workflow"
```

## 验收标准

- 存货入库能更新数量、金额和移动平均成本。
- 销售出库能按移动平均成本结转主营业务成本。
- 库存不足时拒绝出库结转。
- 存货跌价准备能生成正式分录。
- 盘盈盘亏能生成待处理财产损溢分录。
- 前端展示 SKU 库存余额、成本和风险状态。
- 期间关闭后拒绝新增库存核算分录。

## 风险控制

- 数量和金额均使用 `Decimal`。
- 库存业务流水和正式分录通过 source key 关联，不相互覆盖。
- 出库成本不允许导致库存金额为负。
- 盘点差异必须保留审批人和审批时间。
- 不把电商分析口径直接当成正式库存事实。
