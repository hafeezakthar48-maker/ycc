# Formal Accounting Engine Phase 8 Receivable Payable Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在正式分录、辅助核算和期末处理基础上，建立应收应付与往来核算模块，支持客户/供应商往来余额、账龄、核销、收付款匹配和坏账准备。  
**Architecture:** 新增 `receivable_payable` 领域模型和服务，核心对象为从正式分录生成的往来未清项 `open_item`。应收应付余额、账龄和风险提示从正式分录行与客户/供应商辅助维度推导；核销记录只记录匹配关系和已核销金额，不改写历史分录；坏账准备通过期末动作生成正式分录。  
**Tech Stack:** FastAPI、Pydantic、SQLite、Decimal、pytest、React、TypeScript、Vite、Node test runner。
---

## Prerequisite

必须先完成并验证：
- `docs/superpowers/plans/2026-07-06-formal-accounting-engine-phase-1.md`
- `docs/superpowers/plans/2026-07-06-formal-accounting-engine-phase-2-multi-currency.md`
- `docs/superpowers/plans/2026-07-06-formal-accounting-engine-phase-3-auxiliary-dimensions.md`
- `docs/superpowers/plans/2026-07-06-formal-accounting-engine-phase-4-period-close.md`
- 正式分录行支持客户和供应商辅助核算维度
- 正式分录行支持本位币金额、原币金额和币种
- 账簿服务可按科目和辅助维度查询正式分录
- 期末处理服务可生成正式期末分录并保证幂等

本期不做供应链订单、销售合同、采购合同、发票验真、银行流水自动抓取、自动付款、信用额度审批流、完整催收工作流和复杂重分类报表。本期只做财务核算需要的往来余额、账龄、核销和坏账准备底座。

## Accounting Decisions

- 应收应付以正式分录为唯一核算来源，不从凭证摘要或报表缓存反推。
- 应收未清项来自 `1122 应收账款`、`1221 其他应收款` 等借方余额类分录行，必须挂 `customer` 维度。
- 应付未清项来自 `2202 应付账款`、`2241 其他应付款` 等贷方余额类分录行，必须挂 `supplier` 维度。
- 预收、预付本期只进入往来余额摘要，不纳入应收/应付账龄主表。
- 核销不修改原始正式分录；核销记录通过 `settlement_id` 连接来源未清项和收付款分录行。
- 支持部分核销，同一未清项可以被多笔收付款逐步核销。
- 账龄按未清项发生日到查询截止日计算，默认分组为 `0-30`、`31-60`、`61-90`、`91-180`、`181-365`、`365+`。
- 坏账准备基于应收账龄和配置比例生成：借记 `6701 资产减值损失`，贷记 `1231 坏账准备`。
- 坏账核销基于已确认坏账：借记 `1231 坏账准备`，贷记 `1122 应收账款`，并保留客户维度。
- 多币种往来展示原币和本位币；账龄和坏账准备以本位币金额为准。
- 已关闭期间不能新增核销记录；已关闭期间可以查询余额和账龄。

## File Structure

- Create: `backend/app/models/receivable_payable.py`
  - 定义往来类型、未清项、核销记录、账龄桶、坏账准备规则和响应模型。
- Create: `backend/app/services/receivable_payable_service.py`
  - 从正式分录构建未清项，计算余额、账龄、核销、坏账准备和坏账核销。
- Create: `backend/app/api/receivable_payable.py`
  - 提供往来余额、账龄、核销、坏账准备和坏账核销 API。
- Modify: `backend/app/api/router_registry.py`
  - 注册往来核算 API。
- Modify: `backend/app/services/accounting_service.py`
  - 暴露按期间、科目、客户/供应商维度读取正式分录行的查询函数。
- Modify: `backend/app/services/period_close_service.py`
  - 接入坏账准备期末动作。
- Modify: `backend/app/services/system_admin_service.py`
  - 增加往来查看、核销、坏账准备权限。
- Modify: `backend/app/services/module_registry_service.py`
  - 注册往来 API、权限和审计事件。
- Create: `backend/tests/test_receivable_payable_service.py`
- Create: `backend/tests/test_receivable_payable_api.py`
- Modify: `backend/tests/test_period_close_service.py`
- Create: `frontend/src/types/receivablePayable.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/ReceivablePayablePanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Create: `frontend/tests/receivablePayableApi.test.mjs`
- Create: `frontend/tests/receivablePayablePanel.test.mjs`
- Modify: `frontend/package.json`
- Modify: `README.md`
- Modify: `docs/01-mvp-design.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

## Task 1: 往来模型与正式分录行查询

**Files:**
- Create: `backend/app/models/receivable_payable.py`
- Modify: `backend/app/services/accounting_service.py`
- Create: `backend/tests/test_receivable_payable_service.py`

- [ ] **Step 1: Write failing formal-line query tests**

Create `backend/tests/test_receivable_payable_service.py`:

```python
from decimal import Decimal

from app.models.accounting import (
    AuxiliaryDimensionCreate,
    JournalEntryCreate,
    JournalLineCreate,
    JournalLineDimension,
)
from app.services.accounting_service import (
    list_counterparty_journal_lines,
    post_journal_entry,
    reset_accounting_store,
    upsert_auxiliary_dimension,
)


def setup_function():
    reset_accounting_store()


def _seed_customer():
    upsert_auxiliary_dimension(
        AuxiliaryDimensionCreate(
            account_set_id="default",
            dimension_type="customer",
            dimension_code="CUST-SH-001",
            dimension_name="上海客户",
        )
    )


def test_list_counterparty_journal_lines_reads_customer_ar_lines():
    _seed_customer()
    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-05",
            source_type="voucher_center",
            source_id="voucher-ar-001",
            description="确认客户应收",
            lines=[
                JournalLineCreate(
                    account_code="1122",
                    account_name="应收账款",
                    direction="debit",
                    original_amount=Decimal("1060.00"),
                    base_amount=Decimal("1060.00"),
                    dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-SH-001")],
                ),
                JournalLineCreate(
                    account_code="6001",
                    account_name="主营业务收入",
                    direction="credit",
                    original_amount=Decimal("1000.00"),
                    base_amount=Decimal("1000.00"),
                    dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-SH-001")],
                ),
                JournalLineCreate(
                    account_code="2221",
                    account_name="应交税费",
                    direction="credit",
                    original_amount=Decimal("60.00"),
                    base_amount=Decimal("60.00"),
                ),
            ],
        )
    )

    lines = list_counterparty_journal_lines(
        account_set_id="default",
        period_to="2026-06",
        account_prefixes=["1122"],
        dimension_type="customer",
    )

    assert len(lines) == 1
    assert lines[0]["account_code"] == "1122"
    assert lines[0]["counterparty_code"] == "CUST-SH-001"
    assert lines[0]["counterparty_name"] == "上海客户"
```

- [ ] **Step 2: Implement receivable/payable models**

Create `backend/app/models/receivable_payable.py`:

```python
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CounterpartyType = Literal["customer", "supplier"]
OpenItemType = Literal["receivable", "payable"]
SettlementStatus = Literal["open", "partial", "settled", "written_off"]
AgingBucketCode = Literal["0-30", "31-60", "61-90", "91-180", "181-365", "365+"]


class CounterpartyOpenItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    open_item_id: str
    account_set_id: str
    open_item_type: OpenItemType
    period: str
    source_entry_id: str
    source_line_id: str
    source_type: str
    source_id: str
    document_date: str
    due_date: str | None = None
    account_code: str
    account_name: str
    counterparty_type: CounterpartyType
    counterparty_code: str
    counterparty_name: str
    currency: str = "CNY"
    original_amount: Decimal
    base_amount: Decimal
    settled_base_amount: Decimal = Decimal("0.00")
    open_base_amount: Decimal
    status: SettlementStatus = "open"


class CounterpartyBalanceItem(BaseModel):
    counterparty_type: CounterpartyType
    counterparty_code: str
    counterparty_name: str
    open_item_type: OpenItemType
    currency: str = "CNY"
    original_balance: Decimal
    base_balance: Decimal
    open_item_count: int


class CounterpartyBalanceResponse(BaseModel):
    account_set_id: str
    period: str
    open_item_type: OpenItemType
    total_base_balance: Decimal
    item_count: int
    items: list[CounterpartyBalanceItem]
```

- [ ] **Step 3: Add formal line query to accounting service**

Modify `backend/app/services/accounting_service.py`:

```python
def list_counterparty_journal_lines(
    account_set_id: str,
    period_to: str,
    account_prefixes: list[str],
    dimension_type: str,
) -> list[dict]:
    entries = list_journal_entries(account_set_id=account_set_id, period=None).entries
    rows: list[dict] = []
    for entry in entries:
        if entry.entry_date[:7] > period_to:
            continue
        for line in entry.lines:
            if not any(line.account_code.startswith(prefix) for prefix in account_prefixes):
                continue
            dimension = next((item for item in line.dimensions if item.dimension_type == dimension_type), None)
            if dimension is None:
                continue
            rows.append(
                {
                    "entry_id": entry.id,
                    "line_id": line.id,
                    "entry_date": entry.entry_date,
                    "period": entry.entry_date[:7],
                    "source_type": entry.source_type,
                    "source_id": entry.source_id,
                    "account_code": line.account_code,
                    "account_name": line.account_name,
                    "direction": line.direction,
                    "currency": line.currency,
                    "original_amount": line.original_amount,
                    "base_amount": line.base_amount,
                    "counterparty_type": dimension.dimension_type,
                    "counterparty_code": dimension.dimension_code,
                    "counterparty_name": dimension.dimension_name,
                }
            )
    return rows
```

If the existing `list_journal_entries` requires a non-null period, add a small helper:

```python
def list_all_journal_entries(account_set_id: str) -> JournalEntryListResponse:
    entries = [entry for entry in _JOURNAL_ENTRIES.values() if entry.account_set_id == account_set_id]
    entries.sort(key=lambda item: (item.entry_date, item.id))
    return JournalEntryListResponse(account_set_id=account_set_id, period="", total=len(entries), entries=entries)
```

Then use `list_all_journal_entries(account_set_id).entries` inside `list_counterparty_journal_lines`.

- [ ] **Step 4: Verify and commit**

```powershell
python -m pytest backend/tests/test_receivable_payable_service.py
git add backend/app/models/receivable_payable.py backend/app/services/accounting_service.py backend/tests/test_receivable_payable_service.py
git commit -m "feat: query counterparty journal lines"
```

## Task 2: 未清项构建与往来余额

**Files:**
- Create: `backend/app/services/receivable_payable_service.py`
- Modify: `backend/tests/test_receivable_payable_service.py`

- [ ] **Step 1: Write failing open item tests**

Append to `backend/tests/test_receivable_payable_service.py`:

```python
from app.services.receivable_payable_service import (
    build_counterparty_open_items,
    build_counterparty_balances,
    reset_receivable_payable_store,
)


def test_build_receivable_open_items_from_formal_ar_lines():
    reset_receivable_payable_store()
    _seed_customer()
    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-05",
            source_type="voucher_center",
            source_id="voucher-ar-001",
            description="确认客户应收",
            lines=[
                JournalLineCreate(account_code="1122", account_name="应收账款", direction="debit", original_amount=Decimal("1060.00"), base_amount=Decimal("1060.00"), dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-SH-001")]),
                JournalLineCreate(account_code="6001", account_name="主营业务收入", direction="credit", original_amount=Decimal("1000.00"), base_amount=Decimal("1000.00"), dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-SH-001")]),
                JournalLineCreate(account_code="2221", account_name="应交税费", direction="credit", original_amount=Decimal("60.00"), base_amount=Decimal("60.00")),
            ],
        )
    )

    items = build_counterparty_open_items("default", "2026-06", "receivable")
    balances = build_counterparty_balances("default", "2026-06", "receivable")

    assert len(items) == 1
    assert items[0].counterparty_code == "CUST-SH-001"
    assert items[0].open_base_amount == Decimal("1060.00")
    assert balances.total_base_balance == Decimal("1060.00")
    assert balances.items[0].open_item_count == 1
```

- [ ] **Step 2: Implement service constants and reset**

Create `backend/app/services/receivable_payable_service.py`:

```python
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from app.models.receivable_payable import (
    CounterpartyBalanceItem,
    CounterpartyBalanceResponse,
    CounterpartyOpenItem,
)
from app.services.accounting_service import list_counterparty_journal_lines

ZERO = Decimal("0.00")
RECEIVABLE_ACCOUNT_PREFIXES = ["1122", "1221"]
PAYABLE_ACCOUNT_PREFIXES = ["2202", "2241"]
PREPAYMENT_ACCOUNT_PREFIXES = ["1123", "2203"]

_SETTLEMENTS: dict[str, dict] = {}


def reset_receivable_payable_store() -> None:
    _SETTLEMENTS.clear()
```

- [ ] **Step 3: Build open items from formal lines**

In `backend/app/services/receivable_payable_service.py`:

```python
def build_counterparty_open_items(
    account_set_id: str,
    period: str,
    open_item_type: str,
) -> list[CounterpartyOpenItem]:
    if open_item_type == "receivable":
        rows = list_counterparty_journal_lines(account_set_id, period, RECEIVABLE_ACCOUNT_PREFIXES, "customer")
        normal_direction = "debit"
    elif open_item_type == "payable":
        rows = list_counterparty_journal_lines(account_set_id, period, PAYABLE_ACCOUNT_PREFIXES, "supplier")
        normal_direction = "credit"
    else:
        raise ValueError("往来类型必须为 receivable 或 payable")

    items: list[CounterpartyOpenItem] = []
    for row in rows:
        signed_amount = _signed_open_amount(row["direction"], row["base_amount"], normal_direction)
        if signed_amount <= ZERO:
            continue
        settled_amount = _settled_amount_for_line(row["line_id"])
        open_amount = signed_amount - settled_amount
        status = "settled" if open_amount == ZERO else "partial" if settled_amount > ZERO else "open"
        items.append(
            CounterpartyOpenItem(
                open_item_id=f"{open_item_type}:{row['entry_id']}:{row['line_id']}",
                account_set_id=account_set_id,
                open_item_type=open_item_type,
                period=row["period"],
                source_entry_id=row["entry_id"],
                source_line_id=row["line_id"],
                source_type=row["source_type"],
                source_id=row["source_id"],
                document_date=row["entry_date"],
                account_code=row["account_code"],
                account_name=row["account_name"],
                counterparty_type=row["counterparty_type"],
                counterparty_code=row["counterparty_code"],
                counterparty_name=row["counterparty_name"],
                currency=row["currency"],
                original_amount=row["original_amount"],
                base_amount=signed_amount,
                settled_base_amount=settled_amount,
                open_base_amount=open_amount,
                status=status,
            )
        )
    return items
```

Add helpers:

```python
def _signed_open_amount(direction: str, amount: Decimal, normal_direction: str) -> Decimal:
    if direction == normal_direction:
        return amount
    return -amount


def _settled_amount_for_line(source_line_id: str) -> Decimal:
    total = ZERO
    for settlement in _SETTLEMENTS.values():
        for item in settlement["items"]:
            if item["source_line_id"] == source_line_id:
                total += item["settled_base_amount"]
    return total
```

- [ ] **Step 4: Build counterparty balances**

In `backend/app/services/receivable_payable_service.py`:

```python
def build_counterparty_balances(
    account_set_id: str,
    period: str,
    open_item_type: str,
) -> CounterpartyBalanceResponse:
    open_items = [item for item in build_counterparty_open_items(account_set_id, period, open_item_type) if item.open_base_amount > ZERO]
    grouped: dict[tuple[str, str, str], list[CounterpartyOpenItem]] = defaultdict(list)
    for item in open_items:
        grouped[(item.counterparty_code, item.counterparty_name, item.currency)].append(item)

    balance_items: list[CounterpartyBalanceItem] = []
    for (counterparty_code, counterparty_name, currency), items in sorted(grouped.items()):
        balance_items.append(
            CounterpartyBalanceItem(
                counterparty_type=items[0].counterparty_type,
                counterparty_code=counterparty_code,
                counterparty_name=counterparty_name,
                open_item_type=open_item_type,
                currency=currency,
                original_balance=sum((item.original_amount for item in items), ZERO),
                base_balance=sum((item.open_base_amount for item in items), ZERO),
                open_item_count=len(items),
            )
        )

    return CounterpartyBalanceResponse(
        account_set_id=account_set_id,
        period=period,
        open_item_type=open_item_type,
        total_base_balance=sum((item.base_balance for item in balance_items), ZERO),
        item_count=len(balance_items),
        items=balance_items,
    )
```

- [ ] **Step 5: Verify and commit**

```powershell
python -m pytest backend/tests/test_receivable_payable_service.py
git add backend/app/services/receivable_payable_service.py backend/tests/test_receivable_payable_service.py
git commit -m "feat: build counterparty open items"
```

## Task 3: 账龄分析

**Files:**
- Modify: `backend/app/models/receivable_payable.py`
- Modify: `backend/app/services/receivable_payable_service.py`
- Modify: `backend/tests/test_receivable_payable_service.py`

- [ ] **Step 1: Write failing aging tests**

Append to `backend/tests/test_receivable_payable_service.py`:

```python
from app.services.receivable_payable_service import build_aging_report


def test_build_aging_report_places_open_items_into_buckets():
    reset_receivable_payable_store()
    _seed_customer()
    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-04-01",
            source_type="voucher_center",
            source_id="voucher-ar-aging-001",
            description="确认客户应收",
            lines=[
                JournalLineCreate(account_code="1122", account_name="应收账款", direction="debit", original_amount=Decimal("1000.00"), base_amount=Decimal("1000.00"), dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-SH-001")]),
                JournalLineCreate(account_code="6001", account_name="主营业务收入", direction="credit", original_amount=Decimal("1000.00"), base_amount=Decimal("1000.00"), dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-SH-001")]),
            ],
        )
    )

    report = build_aging_report("default", "2026-06", "receivable", as_of_date="2026-06-30")

    bucket_by_code = {bucket.bucket_code: bucket.amount for bucket in report.buckets}
    assert bucket_by_code["61-90"] == Decimal("1000.00")
    assert report.total_base_balance == Decimal("1000.00")
```

- [ ] **Step 2: Add aging models**

Modify `backend/app/models/receivable_payable.py`:

```python
class AgingBucket(BaseModel):
    bucket_code: AgingBucketCode
    day_from: int
    day_to: int | None
    amount: Decimal
    open_item_count: int


class CounterpartyAgingItem(BaseModel):
    counterparty_type: CounterpartyType
    counterparty_code: str
    counterparty_name: str
    buckets: list[AgingBucket]
    total_base_balance: Decimal


class CounterpartyAgingResponse(BaseModel):
    account_set_id: str
    period: str
    as_of_date: str
    open_item_type: OpenItemType
    buckets: list[AgingBucket]
    items: list[CounterpartyAgingItem]
    total_base_balance: Decimal
```

- [ ] **Step 3: Implement aging calculation**

Modify `backend/app/services/receivable_payable_service.py` imports:

```python
from datetime import date
from app.models.receivable_payable import AgingBucket, CounterpartyAgingItem, CounterpartyAgingResponse
```

Add bucket config:

```python
AGING_BUCKETS = [
    ("0-30", 0, 30),
    ("31-60", 31, 60),
    ("61-90", 61, 90),
    ("91-180", 91, 180),
    ("181-365", 181, 365),
    ("365+", 366, None),
]
```

Add functions:

```python
def build_aging_report(
    account_set_id: str,
    period: str,
    open_item_type: str,
    as_of_date: str,
) -> CounterpartyAgingResponse:
    open_items = [item for item in build_counterparty_open_items(account_set_id, period, open_item_type) if item.open_base_amount > ZERO]
    overall_buckets = _empty_bucket_map()
    counterparty_bucket_map: dict[tuple[str, str, str], dict[str, dict]] = defaultdict(_empty_bucket_map)
    as_of = date.fromisoformat(as_of_date)

    for item in open_items:
        age_days = (as_of - date.fromisoformat(item.document_date)).days
        bucket_code = _bucket_code(age_days)
        overall_buckets[bucket_code]["amount"] += item.open_base_amount
        overall_buckets[bucket_code]["count"] += 1
        key = (item.counterparty_type, item.counterparty_code, item.counterparty_name)
        counterparty_bucket_map[key][bucket_code]["amount"] += item.open_base_amount
        counterparty_bucket_map[key][bucket_code]["count"] += 1

    return CounterpartyAgingResponse(
        account_set_id=account_set_id,
        period=period,
        as_of_date=as_of_date,
        open_item_type=open_item_type,
        buckets=_bucket_list(overall_buckets),
        items=[
            CounterpartyAgingItem(
                counterparty_type=counterparty_type,
                counterparty_code=counterparty_code,
                counterparty_name=counterparty_name,
                buckets=_bucket_list(bucket_map),
                total_base_balance=sum((bucket["amount"] for bucket in bucket_map.values()), ZERO),
            )
            for (counterparty_type, counterparty_code, counterparty_name), bucket_map in sorted(counterparty_bucket_map.items())
        ],
        total_base_balance=sum((bucket["amount"] for bucket in overall_buckets.values()), ZERO),
    )
```

Add helpers:

```python
def _empty_bucket_map() -> dict[str, dict]:
    return {code: {"amount": ZERO, "count": 0, "from": day_from, "to": day_to} for code, day_from, day_to in AGING_BUCKETS}


def _bucket_code(age_days: int) -> str:
    for code, day_from, day_to in AGING_BUCKETS:
        if age_days >= day_from and (day_to is None or age_days <= day_to):
            return code
    return "365+"


def _bucket_list(bucket_map: dict[str, dict]) -> list[AgingBucket]:
    return [
        AgingBucket(
            bucket_code=code,
            day_from=bucket_map[code]["from"],
            day_to=bucket_map[code]["to"],
            amount=bucket_map[code]["amount"],
            open_item_count=bucket_map[code]["count"],
        )
        for code, _, _ in AGING_BUCKETS
    ]
```

- [ ] **Step 4: Verify and commit**

```powershell
python -m pytest backend/tests/test_receivable_payable_service.py
git add backend/app/models/receivable_payable.py backend/app/services/receivable_payable_service.py backend/tests/test_receivable_payable_service.py
git commit -m "feat: add counterparty aging report"
```

## Task 4: 收付款匹配与核销

**Files:**
- Modify: `backend/app/models/receivable_payable.py`
- Modify: `backend/app/services/receivable_payable_service.py`
- Modify: `backend/tests/test_receivable_payable_service.py`

- [ ] **Step 1: Write failing settlement tests**

Append to `backend/tests/test_receivable_payable_service.py`:

```python
from app.models.receivable_payable import CounterpartySettlementCreate, CounterpartySettlementItemCreate
from app.services.receivable_payable_service import create_counterparty_settlement


def test_create_partial_receivable_settlement_reduces_open_amount():
    reset_receivable_payable_store()
    _seed_customer()
    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-05",
            source_type="voucher_center",
            source_id="voucher-ar-settle-001",
            description="确认客户应收",
            lines=[
                JournalLineCreate(account_code="1122", account_name="应收账款", direction="debit", original_amount=Decimal("1060.00"), base_amount=Decimal("1060.00"), dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-SH-001")]),
                JournalLineCreate(account_code="6001", account_name="主营业务收入", direction="credit", original_amount=Decimal("1000.00"), base_amount=Decimal("1000.00"), dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-SH-001")]),
                JournalLineCreate(account_code="2221", account_name="应交税费", direction="credit", original_amount=Decimal("60.00"), base_amount=Decimal("60.00")),
            ],
        )
    )
    open_item = build_counterparty_open_items("default", "2026-06", "receivable")[0]

    settlement = create_counterparty_settlement(
        CounterpartySettlementCreate(
            account_set_id="default",
            period="2026-06",
            open_item_type="receivable",
            settlement_date="2026-06-20",
            counterparty_type="customer",
            counterparty_code="CUST-SH-001",
            payment_entry_id="bank-receipt-001",
            items=[
                CounterpartySettlementItemCreate(
                    open_item_id=open_item.open_item_id,
                    source_line_id=open_item.source_line_id,
                    settled_base_amount=Decimal("600.00"),
                )
            ],
            settled_by="finance-user",
        )
    )
    items_after = build_counterparty_open_items("default", "2026-06", "receivable")

    assert settlement.total_settled_base_amount == Decimal("600.00")
    assert items_after[0].open_base_amount == Decimal("460.00")
    assert items_after[0].status == "partial"
```

- [ ] **Step 2: Add settlement models**

Modify `backend/app/models/receivable_payable.py`:

```python
class CounterpartySettlementItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    open_item_id: str
    source_line_id: str
    settled_base_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class CounterpartySettlementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = "default"
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    open_item_type: OpenItemType
    settlement_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    counterparty_type: CounterpartyType
    counterparty_code: str
    payment_entry_id: str
    items: list[CounterpartySettlementItemCreate] = Field(min_length=1, max_length=100)
    settled_by: str


class CounterpartySettlement(BaseModel):
    settlement_id: str
    account_set_id: str
    period: str
    open_item_type: OpenItemType
    settlement_date: str
    counterparty_type: CounterpartyType
    counterparty_code: str
    payment_entry_id: str
    items: list[CounterpartySettlementItemCreate]
    total_settled_base_amount: Decimal
    settled_by: str
    created_at: str
```

- [ ] **Step 3: Implement settlement service**

Modify `backend/app/services/receivable_payable_service.py` imports:

```python
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import HTTPException
from app.models.receivable_payable import CounterpartySettlement, CounterpartySettlementCreate
```

Add service:

```python
def create_counterparty_settlement(payload: CounterpartySettlementCreate) -> CounterpartySettlement:
    from app.services.accounting_period_service import is_accounting_period_closed

    if is_accounting_period_closed(payload.period, payload.account_set_id):
        raise HTTPException(status_code=409, detail="会计期间已关闭，不能新增往来核销。")

    open_items = {
        item.open_item_id: item
        for item in build_counterparty_open_items(payload.account_set_id, payload.period, payload.open_item_type)
    }
    for settlement_item in payload.items:
        open_item = open_items.get(settlement_item.open_item_id)
        if open_item is None:
            raise HTTPException(status_code=404, detail=f"未找到往来未清项：{settlement_item.open_item_id}")
        if open_item.counterparty_code != payload.counterparty_code:
            raise HTTPException(status_code=422, detail="核销客户或供应商与未清项不一致。")
        if settlement_item.settled_base_amount > open_item.open_base_amount:
            raise HTTPException(status_code=422, detail="核销金额不能超过未清金额。")

    settlement = CounterpartySettlement(
        settlement_id=f"settle_{uuid4().hex}",
        account_set_id=payload.account_set_id,
        period=payload.period,
        open_item_type=payload.open_item_type,
        settlement_date=payload.settlement_date,
        counterparty_type=payload.counterparty_type,
        counterparty_code=payload.counterparty_code,
        payment_entry_id=payload.payment_entry_id,
        items=payload.items,
        total_settled_base_amount=sum((item.settled_base_amount for item in payload.items), ZERO),
        settled_by=payload.settled_by,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    _SETTLEMENTS[settlement.settlement_id] = settlement.model_dump()
    return settlement
```

Adjust `_settled_amount_for_line`:

```python
def _settled_amount_for_line(source_line_id: str) -> Decimal:
    total = ZERO
    for settlement in _SETTLEMENTS.values():
        for item in settlement["items"]:
            if item["source_line_id"] == source_line_id:
                total += item["settled_base_amount"]
    return total
```

- [ ] **Step 4: Verify and commit**

```powershell
python -m pytest backend/tests/test_receivable_payable_service.py
git add backend/app/models/receivable_payable.py backend/app/services/receivable_payable_service.py backend/tests/test_receivable_payable_service.py
git commit -m "feat: settle counterparty open items"
```

## Task 5: 坏账准备与坏账核销

**Files:**
- Modify: `backend/app/models/receivable_payable.py`
- Modify: `backend/app/services/receivable_payable_service.py`
- Modify: `backend/app/services/period_close_service.py`
- Modify: `backend/tests/test_receivable_payable_service.py`
- Modify: `backend/tests/test_period_close_service.py`

- [ ] **Step 1: Write failing bad-debt tests**

Append to `backend/tests/test_receivable_payable_service.py`:

```python
from app.models.receivable_payable import BadDebtProvisionRule
from app.services.receivable_payable_service import calculate_bad_debt_provision


def test_calculate_bad_debt_provision_from_aging_buckets():
    reset_receivable_payable_store()
    _seed_customer()
    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-01-01",
            source_type="voucher_center",
            source_id="voucher-ar-bad-debt-001",
            description="确认客户应收",
            lines=[
                JournalLineCreate(account_code="1122", account_name="应收账款", direction="debit", original_amount=Decimal("1000.00"), base_amount=Decimal("1000.00"), dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-SH-001")]),
                JournalLineCreate(account_code="6001", account_name="主营业务收入", direction="credit", original_amount=Decimal("1000.00"), base_amount=Decimal("1000.00"), dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-SH-001")]),
            ],
        )
    )

    result = calculate_bad_debt_provision(
        account_set_id="default",
        period="2026-06",
        as_of_date="2026-06-30",
        rule=BadDebtProvisionRule(bucket_rates={"181-365": Decimal("0.10"), "365+": Decimal("0.50")}),
    )

    assert result.required_provision_amount == Decimal("100.00")
    assert result.debit_account_code == "6701"
    assert result.credit_account_code == "1231"
```

- [ ] **Step 2: Add bad debt models**

Modify `backend/app/models/receivable_payable.py`:

```python
class BadDebtProvisionRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bucket_rates: dict[AgingBucketCode, Decimal] = Field(default_factory=dict)
    debit_account_code: str = "6701"
    debit_account_name: str = "资产减值损失"
    credit_account_code: str = "1231"
    credit_account_name: str = "坏账准备"


class BadDebtProvisionResult(BaseModel):
    account_set_id: str
    period: str
    as_of_date: str
    required_provision_amount: Decimal
    debit_account_code: str
    debit_account_name: str
    credit_account_code: str
    credit_account_name: str
    evidence: list[dict]
```

- [ ] **Step 3: Implement bad debt calculation**

Modify `backend/app/services/receivable_payable_service.py`:

```python
from app.models.receivable_payable import BadDebtProvisionResult, BadDebtProvisionRule


def calculate_bad_debt_provision(
    account_set_id: str,
    period: str,
    as_of_date: str,
    rule: BadDebtProvisionRule,
) -> BadDebtProvisionResult:
    aging = build_aging_report(account_set_id, period, "receivable", as_of_date)
    provision_amount = ZERO
    evidence: list[dict] = []
    for bucket in aging.buckets:
        rate = rule.bucket_rates.get(bucket.bucket_code, ZERO)
        amount = (bucket.amount * rate).quantize(Decimal("0.01"))
        if amount > ZERO:
            evidence.append(
                {
                    "bucket_code": bucket.bucket_code,
                    "bucket_amount": bucket.amount,
                    "rate": rate,
                    "provision_amount": amount,
                }
            )
            provision_amount += amount
    return BadDebtProvisionResult(
        account_set_id=account_set_id,
        period=period,
        as_of_date=as_of_date,
        required_provision_amount=provision_amount,
        debit_account_code=rule.debit_account_code,
        debit_account_name=rule.debit_account_name,
        credit_account_code=rule.credit_account_code,
        credit_account_name=rule.credit_account_name,
        evidence=evidence,
    )
```

- [ ] **Step 4: Wire period close action**

Modify `backend/app/services/period_close_service.py`:

```python
from app.models.receivable_payable import BadDebtProvisionRule
from app.services.receivable_payable_service import calculate_bad_debt_provision
```

Add action type:

```python
"bad_debt_provision"
```

Generate formal entry:

```python
def _generate_bad_debt_provision(account_set_id: str, period: str, generated_by: str) -> PeriodCloseActionResult:
    provision = calculate_bad_debt_provision(
        account_set_id=account_set_id,
        period=period,
        as_of_date=f"{period}-30",
        rule=BadDebtProvisionRule(
            bucket_rates={
                "91-180": Decimal("0.05"),
                "181-365": Decimal("0.10"),
                "365+": Decimal("0.50"),
            }
        ),
    )
    if provision.required_provision_amount == ZERO:
        return PeriodCloseActionResult(action_type="bad_debt_provision", status="skipped", amount=ZERO, message="本期无需计提坏账准备")
    entry = post_journal_entry(
        JournalEntryCreate(
            account_set_id=account_set_id,
            entry_date=f"{period}-30",
            source_type="bad_debt_provision",
            source_id=f"bad_debt_provision:{account_set_id}:{period}",
            description="计提坏账准备",
            lines=[
                JournalLineCreate(account_code=provision.debit_account_code, account_name=provision.debit_account_name, direction="debit", original_amount=provision.required_provision_amount, base_amount=provision.required_provision_amount),
                JournalLineCreate(account_code=provision.credit_account_code, account_name=provision.credit_account_name, direction="credit", original_amount=provision.required_provision_amount, base_amount=provision.required_provision_amount),
            ],
        )
    )
    return PeriodCloseActionResult(action_type="bad_debt_provision", status="generated", journal_entry_ids=[entry.id], amount=provision.required_provision_amount, message="已生成坏账准备分录")
```

- [ ] **Step 5: Verify and commit**

```powershell
python -m pytest backend/tests/test_receivable_payable_service.py backend/tests/test_period_close_service.py
git add backend/app/models/receivable_payable.py backend/app/services/receivable_payable_service.py backend/app/services/period_close_service.py backend/tests/test_receivable_payable_service.py backend/tests/test_period_close_service.py
git commit -m "feat: calculate bad debt provision"
```

## Task 6: 往来核算 API、权限与审计

**Files:**
- Create: `backend/app/api/receivable_payable.py`
- Modify: `backend/app/api/router_registry.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Create: `backend/tests/test_receivable_payable_api.py`

- [ ] **Step 1: Write failing API tests**

Create `backend/tests/test_receivable_payable_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import app
from app.services.accounting_service import reset_accounting_store
from app.services.receivable_payable_service import reset_receivable_payable_store
from app.services.system_admin_service import reset_system_admin_store

client = TestClient(app)


def setup_function():
    reset_accounting_store()
    reset_receivable_payable_store()
    reset_system_admin_store()


def test_receivable_balance_endpoint_requires_permission_and_returns_shape():
    response = client.get(
        "/api/v1/receivable-payable/balances?account_set_id=default&period=2026-06&open_item_type=receivable",
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert response.status_code == 200
    assert response.json()["open_item_type"] == "receivable"
    assert "total_base_balance" in response.json()


def test_receivable_aging_endpoint_returns_buckets():
    response = client.get(
        "/api/v1/receivable-payable/aging?account_set_id=default&period=2026-06&open_item_type=receivable&as_of_date=2026-06-30",
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert response.status_code == 200
    assert [bucket["bucket_code"] for bucket in response.json()["buckets"]] == ["0-30", "31-60", "61-90", "91-180", "181-365", "365+"]
```

- [ ] **Step 2: Create API router**

Create `backend/app/api/receivable_payable.py`:

```python
from fastapi import APIRouter, Header, HTTPException, Query

from app.models.receivable_payable import CounterpartySettlementCreate
from app.models.system_admin import AuditLogCreateRequest
from app.services.receivable_payable_service import (
    build_aging_report,
    build_counterparty_balances,
    create_counterparty_settlement,
)
from app.services.system_admin_service import authorize, record_audit_log

router = APIRouter(prefix="/api/v1/receivable-payable", tags=["receivable-payable"])
```

Add routes:

```python
@router.get("/balances")
def get_balances(
    account_set_id: str = "default",
    period: str = Query(pattern=r"^\d{4}-\d{2}$"),
    open_item_type: str = Query(pattern="^(receivable|payable)$"),
    x_actor_id: str = Header(default="system"),
):
    _require_rp_permission(x_actor_id, "receivable_payable.read", "receivable_payable.balance.read", f"{account_set_id}:{period}:{open_item_type}", {"period": period, "open_item_type": open_item_type})
    return build_counterparty_balances(account_set_id, period, open_item_type)


@router.get("/aging")
def get_aging(
    account_set_id: str = "default",
    period: str = Query(pattern=r"^\d{4}-\d{2}$"),
    open_item_type: str = Query(pattern="^(receivable|payable)$"),
    as_of_date: str = Query(pattern=r"^\d{4}-\d{2}-\d{2}$"),
    x_actor_id: str = Header(default="system"),
):
    _require_rp_permission(x_actor_id, "receivable_payable.read", "receivable_payable.aging.read", f"{account_set_id}:{period}:{open_item_type}", {"period": period, "open_item_type": open_item_type, "as_of_date": as_of_date})
    return build_aging_report(account_set_id, period, open_item_type, as_of_date)


@router.post("/settlements")
def create_settlement(request: CounterpartySettlementCreate, x_actor_id: str = Header(default="system")):
    _require_rp_permission(x_actor_id, "receivable_payable.settle", "receivable_payable.settle", f"{request.account_set_id}:{request.period}:{request.counterparty_code}", {"period": request.period, "counterparty_code": request.counterparty_code})
    try:
        settlement = create_counterparty_settlement(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    _record_rp_audit(x_actor_id, "receivable_payable.settle", settlement.settlement_id, {"period": settlement.period, "counterparty_code": settlement.counterparty_code, "amount": str(settlement.total_settled_base_amount)})
    return settlement
```

Add helpers:

```python
def _record_rp_audit(actor_id: str, event: str, target_id: str, metadata: dict[str, str | int | float | bool | None], result: str = "success") -> None:
    record_audit_log(
        AuditLogCreateRequest(
            actor_id=actor_id,
            module_id="finance-center",
            event=event,
            target_id=target_id,
            result=result,
            metadata=metadata,
        )
    )


def _require_rp_permission(actor_id: str, permission_code: str, event: str, target_id: str, metadata: dict[str, str | int | float | bool | None]) -> None:
    if actor_id == "system":
        return
    decision = authorize(actor_id, permission_code)
    if decision.allowed:
        return
    _record_rp_audit(actor_id, event, target_id, {**metadata, "permission_code": permission_code, "reason": decision.reason}, result="denied")
    raise HTTPException(status_code=403, detail=decision.reason)
```

- [ ] **Step 3: Register router, permissions and audit events**

Modify `backend/app/api/router_registry.py`:

```python
from app.api import receivable_payable
```

and:

```python
app.include_router(receivable_payable.router)
```

Modify `backend/app/services/system_admin_service.py`, add permissions:
- `receivable_payable.read`
- `receivable_payable.settle`
- `receivable_payable.bad_debt`

Finance manager gets all three. Auditor gets `receivable_payable.read`.

Modify `backend/app/services/module_registry_service.py`, add API prefix:
- `/api/v1/receivable-payable`

Audit events:
- `receivable_payable.balance.read`
- `receivable_payable.aging.read`
- `receivable_payable.settle`
- `receivable_payable.bad_debt.provision`

- [ ] **Step 4: Verify and commit**

```powershell
python -m pytest backend/tests/test_receivable_payable_api.py backend/tests/test_receivable_payable_service.py backend/tests/test_system_admin_api.py
git add backend/app/api/receivable_payable.py backend/app/api/router_registry.py backend/app/services/system_admin_service.py backend/app/services/module_registry_service.py backend/tests/test_receivable_payable_api.py
git commit -m "feat: expose receivable payable api"
```

## Task 7: 前端往来核算面板

**Files:**
- Create: `frontend/src/types/receivablePayable.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/ReceivablePayablePanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Create: `frontend/tests/receivablePayableApi.test.mjs`
- Create: `frontend/tests/receivablePayablePanel.test.mjs`
- Modify: `frontend/package.json`

- [ ] **Step 1: Write frontend API tests**

Create `frontend/tests/receivablePayableApi.test.mjs`:

```javascript
import assert from "node:assert/strict";
import test from "node:test";

import { fetchCounterpartyAging, fetchCounterpartyBalances } from "../src/services/dashboardApi.ts";

function createFetcher(payloads) {
  const calls = [];
  const fetcher = async (url, init = {}) => {
    calls.push({ url, init });
    return {
      ok: true,
      status: 200,
      json: async () => payloads[url]
    };
  };
  fetcher.calls = calls;
  return fetcher;
}

test("往来余额 API helper 请求 balances endpoint", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/receivable-payable/balances?account_set_id=default&period=2026-06&open_item_type=receivable": {
      account_set_id: "default",
      period: "2026-06",
      open_item_type: "receivable",
      total_base_balance: "0.00",
      item_count: 0,
      items: []
    }
  });

  await fetchCounterpartyBalances("default", "2026-06", "receivable", "http://api.local", fetcher);

  assert.equal(fetcher.calls[0].init.headers["X-Actor-Id"], "u-finance-manager");
});

test("往来账龄 API helper 请求 aging endpoint", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/receivable-payable/aging?account_set_id=default&period=2026-06&open_item_type=receivable&as_of_date=2026-06-30": {
      account_set_id: "default",
      period: "2026-06",
      as_of_date: "2026-06-30",
      open_item_type: "receivable",
      buckets: [],
      items: [],
      total_base_balance: "0.00"
    }
  });

  await fetchCounterpartyAging("default", "2026-06", "receivable", "2026-06-30", "http://api.local", fetcher);

  assert.equal(fetcher.calls[0].url, "http://api.local/api/v1/receivable-payable/aging?account_set_id=default&period=2026-06&open_item_type=receivable&as_of_date=2026-06-30");
});
```

- [ ] **Step 2: Add frontend types**

Create `frontend/src/types/receivablePayable.ts`:

```typescript
export type OpenItemType = "receivable" | "payable";
export type CounterpartyType = "customer" | "supplier";

export interface CounterpartyBalanceItem {
  counterparty_type: CounterpartyType;
  counterparty_code: string;
  counterparty_name: string;
  open_item_type: OpenItemType;
  currency: string;
  original_balance: string | number;
  base_balance: string | number;
  open_item_count: number;
}

export interface CounterpartyBalanceResponse {
  account_set_id: string;
  period: string;
  open_item_type: OpenItemType;
  total_base_balance: string | number;
  item_count: number;
  items: CounterpartyBalanceItem[];
}

export interface AgingBucket {
  bucket_code: string;
  day_from: number;
  day_to?: number | null;
  amount: string | number;
  open_item_count: number;
}

export interface CounterpartyAgingItem {
  counterparty_type: CounterpartyType;
  counterparty_code: string;
  counterparty_name: string;
  buckets: AgingBucket[];
  total_base_balance: string | number;
}

export interface CounterpartyAgingResponse {
  account_set_id: string;
  period: string;
  as_of_date: string;
  open_item_type: OpenItemType;
  buckets: AgingBucket[];
  items: CounterpartyAgingItem[];
  total_base_balance: string | number;
}
```

- [ ] **Step 3: Add dashboard API helpers**

Modify `frontend/src/services/dashboardApi.ts` imports:

```typescript
import type {
  CounterpartyAgingResponse,
  CounterpartyBalanceResponse,
  OpenItemType
} from "../types/receivablePayable";
```

Add helpers:

```typescript
export function fetchCounterpartyBalances(
  accountSetId = "default",
  period: string,
  openItemType: OpenItemType,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<CounterpartyBalanceResponse> {
  return requestLedgerJson<CounterpartyBalanceResponse>(
    `/api/v1/receivable-payable/balances?account_set_id=${encodeURIComponent(accountSetId)}&period=${encodeURIComponent(period)}&open_item_type=${openItemType}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchCounterpartyAging(
  accountSetId = "default",
  period: string,
  openItemType: OpenItemType,
  asOfDate: string,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<CounterpartyAgingResponse> {
  return requestLedgerJson<CounterpartyAgingResponse>(
    `/api/v1/receivable-payable/aging?account_set_id=${encodeURIComponent(accountSetId)}&period=${encodeURIComponent(period)}&open_item_type=${openItemType}&as_of_date=${encodeURIComponent(asOfDate)}`,
    apiBase,
    fetcher,
    actorId
  );
}
```

- [ ] **Step 4: Build ReceivablePayablePanel**

Create `frontend/src/components/ReceivablePayablePanel.tsx`:

```tsx
import { useEffect, useMemo, useState } from "react";
import { fetchCounterpartyAging, fetchCounterpartyBalances } from "../services/dashboardApi";
import type { CounterpartyAgingResponse, CounterpartyBalanceResponse, OpenItemType } from "../types/receivablePayable";

interface ReceivablePayablePanelProps {
  period: string;
}

function money(value: string | number) {
  return Number(value).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function ReceivablePayablePanel({ period }: ReceivablePayablePanelProps) {
  const [openItemType, setOpenItemType] = useState<OpenItemType>("receivable");
  const [balances, setBalances] = useState<CounterpartyBalanceResponse | null>(null);
  const [aging, setAging] = useState<CounterpartyAgingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const asOfDate = useMemo(() => `${period}-30`, [period]);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    Promise.all([
      fetchCounterpartyBalances("default", period, openItemType),
      fetchCounterpartyAging("default", period, openItemType, asOfDate)
    ])
      .then(([balancePayload, agingPayload]) => {
        if (!cancelled) {
          setBalances(balancePayload);
          setAging(agingPayload);
        }
      })
      .catch((rpError) => {
        if (!cancelled) {
          setError(rpError instanceof Error ? rpError.message : "往来核算读取失败");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [period, openItemType, asOfDate]);

  return (
    <section id="receivable-payable-panel" className="receivable-payable-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">往来核算</span>
          <h2>应收应付余额与账龄</h2>
        </div>
        <div className="statement-actions">
          <button type="button" className={openItemType === "receivable" ? "" : "button-secondary"} onClick={() => setOpenItemType("receivable")}>
            应收
          </button>
          <button type="button" className={openItemType === "payable" ? "" : "button-secondary"} onClick={() => setOpenItemType("payable")}>
            应付
          </button>
        </div>
      </div>
      {error ? <p className="inline-error">{error}</p> : null}
      <div className="ledger-summary-grid">
        <article>
          <span>往来余额</span>
          <strong>{money(balances?.total_base_balance ?? 0)}</strong>
        </article>
        <article>
          <span>往来对象</span>
          <strong>{balances?.item_count ?? 0}</strong>
        </article>
        <article>
          <span>账龄余额</span>
          <strong>{money(aging?.total_base_balance ?? 0)}</strong>
        </article>
        <article>
          <span>截止日</span>
          <strong>{asOfDate}</strong>
        </article>
      </div>
      <div className="receivable-payable-grid">
        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">余额</span>
              <h3>{openItemType === "receivable" ? "客户应收" : "供应商应付"}</h3>
            </div>
          </div>
          <div className="voucher-table-wrap">
            <table className="voucher-table">
              <thead>
                <tr>
                  <th>往来对象</th>
                  <th>币种</th>
                  <th>本位币余额</th>
                  <th>未清项</th>
                </tr>
              </thead>
              <tbody>
                {(balances?.items ?? []).map((item) => (
                  <tr key={`${item.counterparty_type}-${item.counterparty_code}`}>
                    <td>{item.counterparty_name}</td>
                    <td>{item.currency}</td>
                    <td>{money(item.base_balance)}</td>
                    <td>{item.open_item_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">账龄</span>
              <h3>账龄分布</h3>
            </div>
          </div>
          <div className="voucher-table-wrap">
            <table className="voucher-table">
              <thead>
                <tr>
                  <th>账龄</th>
                  <th>金额</th>
                  <th>未清项</th>
                </tr>
              </thead>
              <tbody>
                {(aging?.buckets ?? []).map((bucket) => (
                  <tr key={bucket.bucket_code}>
                    <td>{bucket.bucket_code}</td>
                    <td>{money(bucket.amount)}</td>
                    <td>{bucket.open_item_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </section>
  );
}
```

- [ ] **Step 5: Add panel tests and layout wiring**

Create `frontend/tests/receivablePayablePanel.test.mjs`:

```javascript
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("往来核算面板展示余额、账龄和应收应付切换", async () => {
  const panel = await readFile(resolve("src/components/ReceivablePayablePanel.tsx"), "utf8");
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");

  assert.match(panel, /receivable-payable-panel/);
  assert.match(panel, /fetchCounterpartyBalances/);
  assert.match(panel, /fetchCounterpartyAging/);
  assert.match(panel, /应收/);
  assert.match(panel, /应付/);
  assert.match(panel, /账龄/);
  assert.match(layout, /ReceivablePayablePanel/);
});
```

In `frontend/src/components/DashboardLayout.tsx`, render `ReceivablePayablePanel` after `LedgerPanel`.

In `frontend/package.json`, add:

```json
"node tests/receivablePayableApi.test.mjs && node tests/receivablePayablePanel.test.mjs"
```

to the existing `test:nav` command.

- [ ] **Step 6: Verify and commit**

```powershell
npm --prefix frontend test
npm --prefix frontend run build
git add frontend/src/types/receivablePayable.ts frontend/src/services/dashboardApi.ts frontend/src/components/ReceivablePayablePanel.tsx frontend/src/components/DashboardLayout.tsx frontend/tests/receivablePayableApi.test.mjs frontend/tests/receivablePayablePanel.test.mjs frontend/package.json
git commit -m "feat: add receivable payable panel"
```

## Task 8: 文档、回归验证与边界

**Files:**
- Modify: `README.md`
- Modify: `docs/01-mvp-design.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

- [ ] **Step 1: Document receivable/payable workflow**

Update docs with:
- 客户/供应商维度是往来核算前提
- 应收应付未清项来源科目
- 应收应付余额计算口径
- 账龄桶定义
- 核销和部分核销规则
- 坏账准备计提规则
- 关闭期间核销限制
- 权限和审计事件

- [ ] **Step 2: Document API changes**

In `docs/02-api-design.md`, add:

```markdown
GET /api/v1/receivable-payable/balances?account_set_id=default&period=2026-06&open_item_type=receivable
GET /api/v1/receivable-payable/aging?account_set_id=default&period=2026-06&open_item_type=receivable&as_of_date=2026-06-30
POST /api/v1/receivable-payable/settlements
```

Permissions:
- `receivable_payable.read`
- `receivable_payable.settle`
- `receivable_payable.bad_debt`

Audit events:
- `receivable_payable.balance.read`
- `receivable_payable.aging.read`
- `receivable_payable.settle`
- `receivable_payable.bad_debt.provision`

- [ ] **Step 3: Run backend regression**

```powershell
python -m pytest backend/tests/test_receivable_payable_service.py backend/tests/test_receivable_payable_api.py backend/tests/test_period_close_service.py backend/tests/test_accounting_service.py backend/tests/test_system_admin_api.py
```

Expected result: all selected backend tests pass.

- [ ] **Step 4: Run frontend regression and build**

```powershell
npm --prefix frontend test
npm --prefix frontend run build
```

Expected result: frontend tests and production build pass. Existing Vite chunk-size warnings are acceptable only when the build exits with code 0.

- [ ] **Step 5: Manual verification scenario**

手工验证场景：
1. 创建客户 `CUST-SH-001` 和供应商 `SUP-BJ-001` 辅助核算维度。
2. 过账一笔挂客户维度的 `1122 应收账款` 销售分录。
3. 过账一笔挂供应商维度的 `2202 应付账款` 采购分录。
4. 查询应收余额，确认客户余额等于未清应收金额。
5. 查询应付余额，确认供应商余额等于未清应付金额。
6. 以 `2026-06-30` 查询账龄，确认未清项进入正确账龄桶。
7. 对应收未清项创建一笔部分核销，确认未清金额减少、状态变为 `partial`。
8. 关闭期间后再次创建核销，确认 API 返回 `409`。
9. 运行坏账准备期末动作，确认生成借记 `6701`、贷记 `1231` 的正式分录。

- [ ] **Step 6: Final docs commit**

```powershell
git add README.md docs/01-mvp-design.md docs/02-api-design.md docs/03-frd-v1.0.md
git commit -m "docs: document receivable payable workflow"
```

## Acceptance Criteria

- 应收未清项从正式 `1122/1221` 分录和客户维度生成。
- 应付未清项从正式 `2202/2241` 分录和供应商维度生成。
- 往来余额按客户/供应商、币种和本位币金额汇总。
- 账龄报告包含固定六个账龄桶和客户/供应商明细。
- 核销记录支持部分核销，并且不修改历史正式分录。
- 已关闭期间拒绝新增核销。
- 坏账准备基于应收账龄规则计算并能接入期末分录生成。
- API 具备权限控制和审计日志。
- 前端展示应收/应付余额、账龄分布和往来对象明细。
- 文档说明核算口径、权限、边界和验证命令。

## Risk Controls

- 使用正式分录和辅助核算维度作为唯一数据源。
- 核销记录只追加，不覆盖原始分录。
- 使用 `Decimal` 计算所有金额。
- 多币种展示原币，本位币用于账龄和坏账准备。
- 坏账准备生成必须通过期末动作幂等 source key。
- 期间关闭后禁止新增核销。
- 不引入订单、合同和银行自动对账范围，避免本期过宽。
