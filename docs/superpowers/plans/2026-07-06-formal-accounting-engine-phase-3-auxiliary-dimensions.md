# Formal Accounting Engine Phase 3 Auxiliary Dimensions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在正式核算一、二期基础上，为分录行增加客户、供应商、员工、部门、项目、资产、平台和 SKU 等辅助核算维度，并支持按维度查询账簿。

**Architecture:** 辅助核算维度作为正式分录行的结构化标签，而不是写在摘要文本里。后端新增维度主数据和分录行维度校验；账簿服务支持按维度过滤与汇总；前端在正式分录、明细账和科目余额视图中展示维度标签。

**Tech Stack:** FastAPI、Pydantic、SQLite、Decimal、pytest、React、TypeScript、Vite、Node test runner。

---

## Prerequisite

必须先完成并验证：

- `docs/superpowers/plans/2026-07-06-formal-accounting-engine-phase-1.md`
- `docs/superpowers/plans/2026-07-06-formal-accounting-engine-phase-2-multi-currency.md`
- 后端已有正式分录 `JournalEntryCreate` / `JournalLineCreate`
- 后端正式分录行已有币种字段：`currency`、`original_amount`、`exchange_rate`、`base_amount`
- 前端已有正式核算类型文件 `frontend/src/types/accounting.ts`

本期不实现完整应收应付子账、项目成本管理、固定资产正式卡片或 SKU 利润模块，只打通辅助核算维度底座。

## File Structure

- Modify: `backend/app/models/accounting.py`
  - 增加辅助核算维度类型、维度主数据、分录行维度、维度账簿响应模型。
- Modify: `backend/app/services/accounting_service.py`
  - 增加维度主数据、维度校验、分录行维度保存、按维度查询正式分录。
- Modify: `backend/app/api/accounting.py`
  - 增加维度主数据 API 和维度账簿查询 API。
- Modify: `backend/app/models/ledger.py`
  - 明细账行增加 `dimensions` 字段。
- Modify: `backend/app/services/ledger_service.py`
  - 正式分录明细账支持维度过滤，账簿行展示维度标签。
- Modify: `backend/app/services/system_admin_service.py`
  - 增加辅助核算维度读取和维护权限。
- Modify: `backend/app/services/module_registry_service.py`
  - 登记维度 API 和审计事件。
- Create: `backend/tests/test_auxiliary_dimensions_service.py`
- Create: `backend/tests/test_auxiliary_dimensions_api.py`
- Modify: `backend/tests/test_ledger_service.py`
- Modify: `frontend/src/types/accounting.ts`
- Modify: `frontend/src/types/ledger.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Modify: `frontend/src/components/LedgerPanel.tsx`
- Create: `frontend/tests/auxiliaryDimensionsApi.test.mjs`
- Modify: `frontend/tests/ledgerPanel.test.mjs`
- Modify: `README.md`, `docs/01-mvp-design.md`, `docs/02-api-design.md`, `docs/03-frd-v1.0.md`

## Task 1: 辅助核算维度模型与主数据服务

**Files:**
- Modify: `backend/app/models/accounting.py`
- Modify: `backend/app/services/accounting_service.py`
- Create: `backend/tests/test_auxiliary_dimensions_service.py`

- [ ] **Step 1: Write failing dimension master-data tests**

Create `backend/tests/test_auxiliary_dimensions_service.py`:

```python
from app.models.accounting import AuxiliaryDimensionCreate
from app.services.accounting_service import (
    get_auxiliary_dimension,
    list_auxiliary_dimensions,
    reset_accounting_store,
    upsert_auxiliary_dimension,
)


def setup_function():
    reset_accounting_store()


def test_upsert_and_list_customer_dimension():
    created = upsert_auxiliary_dimension(
        AuxiliaryDimensionCreate(
            account_set_id="default",
            dimension_type="customer",
            dimension_code="CUST-SH-001",
            dimension_name="上海云智科技有限公司",
        )
    )

    loaded = get_auxiliary_dimension("default", "customer", "CUST-SH-001")
    listed = list_auxiliary_dimensions("default", "customer")

    assert created.dimension_name == "上海云智科技有限公司"
    assert loaded.dimension_code == "CUST-SH-001"
    assert listed.total == 1
    assert listed.dimensions[0].dimension_type == "customer"


def test_list_dimension_types_contains_core_finance_dimensions():
    dimensions = list_auxiliary_dimensions("default").supported_dimension_types

    assert "customer" in dimensions
    assert "supplier" in dimensions
    assert "department" in dimensions
    assert "asset" in dimensions
    assert "sku" in dimensions
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
python -m pytest tests/test_auxiliary_dimensions_service.py -q
```

Expected: FAIL with missing `AuxiliaryDimensionCreate` or missing service functions.

- [ ] **Step 3: Add auxiliary dimension models**

Modify `backend/app/models/accounting.py`:

```python
AuxiliaryDimensionType = Literal[
    "customer",
    "supplier",
    "employee",
    "department",
    "project",
    "asset",
    "platform",
    "sku",
]


class AuxiliaryDimensionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    dimension_type: AuxiliaryDimensionType
    dimension_code: str = Field(min_length=1, max_length=64)
    dimension_name: str = Field(min_length=1, max_length=120)
    is_active: bool = True


class AuxiliaryDimensionRecord(AuxiliaryDimensionCreate):
    id: str
    updated_at: str


class AuxiliaryDimensionListResponse(BaseModel):
    account_set_id: str
    dimension_type: AuxiliaryDimensionType | None = None
    supported_dimension_types: list[str]
    total: int
    dimensions: list[AuxiliaryDimensionRecord]
```

- [ ] **Step 4: Implement dimension master-data service**

Modify `backend/app/services/accounting_service.py` imports:

```python
from app.models.accounting import (
    AuxiliaryDimensionCreate,
    AuxiliaryDimensionListResponse,
    AuxiliaryDimensionRecord,
)
```

Add constants:

```python
SUPPORTED_DIMENSION_TYPES = ("customer", "supplier", "employee", "department", "project", "asset", "platform", "sku")
```

Add service functions:

```python
def upsert_auxiliary_dimension(request: AuxiliaryDimensionCreate) -> AuxiliaryDimensionRecord:
    validate_account_set(request.account_set_id)
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    dimension_id = f"{request.account_set_id}:{request.dimension_type}:{request.dimension_code}"
    record = AuxiliaryDimensionRecord(id=dimension_id, updated_at=now, **request.model_dump())
    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO auxiliary_dimensions (
                id, account_set_id, dimension_type, dimension_code, payload_json, updated_at
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                payload_json = excluded.payload_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                record.id,
                record.account_set_id,
                record.dimension_type,
                record.dimension_code,
                record.model_dump_json(),
            ),
        )
    return record


def get_auxiliary_dimension(account_set_id: str, dimension_type: str, dimension_code: str) -> AuxiliaryDimensionRecord:
    validate_account_set(account_set_id)
    dimension_id = f"{account_set_id}:{dimension_type}:{dimension_code}"
    with _connection() as connection:
        row = connection.execute("SELECT payload_json FROM auxiliary_dimensions WHERE id = ?", (dimension_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"辅助核算维度不存在：{dimension_type}:{dimension_code}")
    return AuxiliaryDimensionRecord.model_validate_json(row["payload_json"])


def list_auxiliary_dimensions(account_set_id: str = "default", dimension_type: str | None = None) -> AuxiliaryDimensionListResponse:
    validate_account_set(account_set_id)
    query = "SELECT payload_json FROM auxiliary_dimensions WHERE account_set_id = ?"
    params: list[str] = [account_set_id]
    if dimension_type:
        query += " AND dimension_type = ?"
        params.append(dimension_type)
    query += " ORDER BY dimension_type, dimension_code"
    with _connection() as connection:
        rows = connection.execute(query, params).fetchall()
    dimensions = [AuxiliaryDimensionRecord.model_validate_json(row["payload_json"]) for row in rows]
    return AuxiliaryDimensionListResponse(
        account_set_id=account_set_id,
        dimension_type=dimension_type,
        supported_dimension_types=list(SUPPORTED_DIMENSION_TYPES),
        total=len(dimensions),
        dimensions=dimensions,
    )
```

Update `_ensure_schema`:

```python
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS auxiliary_dimensions (
            id TEXT PRIMARY KEY,
            account_set_id TEXT NOT NULL,
            dimension_type TEXT NOT NULL,
            dimension_code TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_auxiliary_dimensions_lookup ON auxiliary_dimensions (account_set_id, dimension_type, dimension_code)"
    )
```

Update `reset_accounting_store`:

```python
connection.execute("DELETE FROM auxiliary_dimensions")
```

- [ ] **Step 5: Run service tests**

Run:

```powershell
cd backend
python -m pytest tests/test_auxiliary_dimensions_service.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/models/accounting.py backend/app/services/accounting_service.py backend/tests/test_auxiliary_dimensions_service.py
git commit -m "feat: add auxiliary dimension master data"
```

## Task 2: 分录行维度保存与校验

**Files:**
- Modify: `backend/app/models/accounting.py`
- Modify: `backend/app/services/accounting_service.py`
- Modify: `backend/tests/test_auxiliary_dimensions_service.py`

- [ ] **Step 1: Write failing journal dimension tests**

Append to `backend/tests/test_auxiliary_dimensions_service.py`:

```python
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.accounting import JournalEntryCreate, JournalLineCreate, JournalLineDimension
from app.services.accounting_service import get_journal_entry, post_journal_entry


def _seed_customer():
    upsert_auxiliary_dimension(
        AuxiliaryDimensionCreate(
            account_set_id="default",
            dimension_type="customer",
            dimension_code="CUST-SH-001",
            dimension_name="上海云智科技有限公司",
        )
    )


def test_post_journal_entry_persists_line_dimensions():
    _seed_customer()

    entry = post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-18",
            source_type="manual_adjustment",
            source_id="dimension-entry-1",
            description="客户维度收入",
            lines=[
                JournalLineCreate(
                    account_code="1122",
                    account_name="应收账款",
                    direction="debit",
                    original_amount=Decimal("1000.00"),
                    base_amount=Decimal("1000.00"),
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
            ],
        )
    )

    loaded = get_journal_entry(entry.id)
    assert loaded.lines[0].dimensions[0].dimension_type == "customer"
    assert loaded.lines[0].dimensions[0].dimension_code == "CUST-SH-001"
    assert loaded.lines[0].dimensions[0].dimension_name == "上海云智科技有限公司"


def test_post_journal_entry_rejects_missing_dimension_master_data():
    request = JournalEntryCreate(
        account_set_id="default",
        entry_date="2026-06-18",
        source_type="manual_adjustment",
        source_id="dimension-entry-missing",
        description="缺少客户维度",
        lines=[
            JournalLineCreate(account_code="1122", account_name="应收账款", direction="debit", original_amount=Decimal("1000.00"), base_amount=Decimal("1000.00"), dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-MISSING")]),
            JournalLineCreate(account_code="6001", account_name="主营业务收入", direction="credit", original_amount=Decimal("1000.00"), base_amount=Decimal("1000.00"), dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-MISSING")]),
        ],
    )

    with pytest.raises(HTTPException) as exc_info:
        post_journal_entry(request)

    assert exc_info.value.status_code == 422
    assert "辅助核算维度不存在" in exc_info.value.detail
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
cd backend
python -m pytest tests/test_auxiliary_dimensions_service.py -q
```

Expected: FAIL because `JournalLineDimension` is missing.

- [ ] **Step 3: Add journal line dimension models**

Modify `backend/app/models/accounting.py`:

```python
class JournalLineDimension(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension_type: AuxiliaryDimensionType
    dimension_code: str = Field(min_length=1, max_length=64)


class JournalLineDimensionRecord(JournalLineDimension):
    dimension_name: str
```

Modify `JournalLineCreate`:

```python
    dimensions: list[JournalLineDimension] = Field(default_factory=list, max_length=8)
```

Modify `JournalLineRecord`:

```python
    dimensions: list[JournalLineDimensionRecord] = Field(default_factory=list)
```

- [ ] **Step 4: Validate dimensions and hydrate names during posting**

Modify `backend/app/services/accounting_service.py` in `_build_entry` when building `JournalLineRecord`:

```python
hydrated_dimensions = _hydrate_line_dimensions(request.account_set_id, line.dimensions)
JournalLineRecord(
    id=f"jl-{uuid4().hex[:12]}",
    journal_entry_id=entry_id,
    line_no=index,
    **line.model_dump(exclude={"dimensions"}),
    dimensions=hydrated_dimensions,
)
```

Add helper:

```python
def _hydrate_line_dimensions(account_set_id: str, dimensions) -> list:
    hydrated = []
    seen: set[tuple[str, str]] = set()
    for dimension in dimensions:
        key = (dimension.dimension_type, dimension.dimension_code)
        if key in seen:
            raise HTTPException(status_code=422, detail=f"辅助核算维度重复：{dimension.dimension_type}:{dimension.dimension_code}")
        seen.add(key)
        try:
            record = get_auxiliary_dimension(account_set_id, dimension.dimension_type, dimension.dimension_code)
        except HTTPException as exc:
            if exc.status_code == 404:
                raise HTTPException(status_code=422, detail=f"辅助核算维度不存在：{dimension.dimension_type}:{dimension.dimension_code}") from exc
            raise
        if not record.is_active:
            raise HTTPException(status_code=422, detail=f"辅助核算维度未启用：{dimension.dimension_type}:{dimension.dimension_code}")
        hydrated.append(
            {
                "dimension_type": record.dimension_type,
                "dimension_code": record.dimension_code,
                "dimension_name": record.dimension_name,
            }
        )
    return hydrated
```

- [ ] **Step 5: Run service tests**

Run:

```powershell
cd backend
python -m pytest tests/test_auxiliary_dimensions_service.py tests/test_accounting_service.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/models/accounting.py backend/app/services/accounting_service.py backend/tests/test_auxiliary_dimensions_service.py
git commit -m "feat: attach dimensions to journal lines"
```

## Task 3: 维度过滤与维度账簿查询

**Files:**
- Modify: `backend/app/models/accounting.py`
- Modify: `backend/app/services/accounting_service.py`
- Modify: `backend/app/models/ledger.py`
- Modify: `backend/app/services/ledger_service.py`
- Modify: `backend/tests/test_auxiliary_dimensions_service.py`
- Modify: `backend/tests/test_ledger_service.py`

- [ ] **Step 1: Write failing dimension ledger tests**

Append to `backend/tests/test_auxiliary_dimensions_service.py`:

```python
from app.services.accounting_service import list_journal_entries_by_dimension


def test_list_journal_entries_by_dimension_returns_matching_entries_only():
    _seed_customer()
    upsert_auxiliary_dimension(AuxiliaryDimensionCreate(account_set_id="default", dimension_type="customer", dimension_code="CUST-BJ-002", dimension_name="北京客户"))

    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-18",
            source_type="manual_adjustment",
            source_id="dimension-filter-1",
            description="上海客户收入",
            lines=[
                JournalLineCreate(account_code="1122", account_name="应收账款", direction="debit", original_amount=Decimal("100.00"), base_amount=Decimal("100.00"), dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-SH-001")]),
                JournalLineCreate(account_code="6001", account_name="主营业务收入", direction="credit", original_amount=Decimal("100.00"), base_amount=Decimal("100.00"), dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-SH-001")]),
            ],
        )
    )
    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-19",
            source_type="manual_adjustment",
            source_id="dimension-filter-2",
            description="北京客户收入",
            lines=[
                JournalLineCreate(account_code="1122", account_name="应收账款", direction="debit", original_amount=Decimal("200.00"), base_amount=Decimal("200.00"), dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-BJ-002")]),
                JournalLineCreate(account_code="6001", account_name="主营业务收入", direction="credit", original_amount=Decimal("200.00"), base_amount=Decimal("200.00"), dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-BJ-002")]),
            ],
        )
    )

    result = list_journal_entries_by_dimension("default", "2026-06", "customer", "CUST-SH-001")

    assert result.total == 1
    assert result.entries[0].source_id == "dimension-filter-1"
```

Append to `backend/tests/test_ledger_service.py`:

```python
def test_detail_ledger_filters_by_auxiliary_dimension():
    reset_accounting_store()
    upsert_auxiliary_dimension(AuxiliaryDimensionCreate(account_set_id="default", dimension_type="customer", dimension_code="CUST-SH-001", dimension_name="上海客户"))
    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-18",
            source_type="manual_adjustment",
            source_id="ledger-dimension-1",
            description="上海客户收入",
            lines=[
                JournalLineCreate(account_code="1122", account_name="应收账款", direction="debit", original_amount=Decimal("100.00"), base_amount=Decimal("100.00"), dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-SH-001")]),
                JournalLineCreate(account_code="6001", account_name="主营业务收入", direction="credit", original_amount=Decimal("100.00"), base_amount=Decimal("100.00"), dimensions=[JournalLineDimension(dimension_type="customer", dimension_code="CUST-SH-001")]),
            ],
        )
    )

    detail = build_detail_ledger("2026-06", "1122", "default", dimension_type="customer", dimension_code="CUST-SH-001")

    assert detail.lines[0].dimensions[0].dimension_name == "上海客户"
    assert detail.debit_total == Decimal("100.00")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
cd backend
python -m pytest tests/test_auxiliary_dimensions_service.py::test_list_journal_entries_by_dimension_returns_matching_entries_only tests/test_ledger_service.py::test_detail_ledger_filters_by_auxiliary_dimension -q
```

Expected: FAIL because filtering functions and ledger signature are missing.

- [ ] **Step 3: Add dimension query service**

Modify `backend/app/services/accounting_service.py`:

```python
def list_journal_entries_by_dimension(
    account_set_id: str,
    period: str,
    dimension_type: str,
    dimension_code: str,
) -> JournalEntryListResponse:
    entries = list_journal_entries(account_set_id, period).entries
    matched = [
        entry
        for entry in entries
        if any(
            dimension.dimension_type == dimension_type and dimension.dimension_code == dimension_code
            for line in entry.lines
            for dimension in line.dimensions
        )
    ]
    return JournalEntryListResponse(account_set_id=account_set_id, period=period, total=len(matched), entries=matched)
```

- [ ] **Step 4: Add dimensions to ledger detail lines**

Modify `backend/app/models/ledger.py`:

```python
class LedgerLineDimension(BaseModel):
    dimension_type: str
    dimension_code: str
    dimension_name: str
```

Add to `LedgerDetailLine`:

```python
    dimensions: list[LedgerLineDimension] = Field(default_factory=list)
```

Modify `backend/app/services/ledger_service.py` `build_detail_ledger` signature:

```python
def build_detail_ledger(
    period: str,
    account_code: str,
    account_set_id: str = "default",
    dimension_type: str | None = None,
    dimension_code: str | None = None,
) -> DetailLedgerResponse:
```

In formal journal branch, filter lines:

```python
def _line_matches_dimension(line, dimension_type: str | None, dimension_code: str | None) -> bool:
    if not dimension_type and not dimension_code:
        return True
    return any(
        dimension.dimension_type == dimension_type and dimension.dimension_code == dimension_code
        for dimension in line.dimensions
    )
```

When mapping formal lines:

```python
dimensions=[
    {
        "dimension_type": dimension.dimension_type,
        "dimension_code": dimension.dimension_code,
        "dimension_name": dimension.dimension_name,
    }
    for dimension in line.dimensions
],
```

- [ ] **Step 5: Run service and ledger tests**

Run:

```powershell
cd backend
python -m pytest tests/test_auxiliary_dimensions_service.py tests/test_ledger_service.py tests/test_ledger_api.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/models/accounting.py backend/app/services/accounting_service.py backend/app/models/ledger.py backend/app/services/ledger_service.py backend/tests/test_auxiliary_dimensions_service.py backend/tests/test_ledger_service.py
git commit -m "feat: query ledgers by auxiliary dimension"
```

## Task 4: 辅助核算 API、权限与模块注册

**Files:**
- Modify: `backend/app/api/accounting.py`
- Modify: `backend/app/api/ledger.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Create: `backend/tests/test_auxiliary_dimensions_api.py`

- [ ] **Step 1: Write failing API tests**

Create `backend/tests/test_auxiliary_dimensions_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import app
from app.services.accounting_service import reset_accounting_store


client = TestClient(app)


def setup_function():
    reset_accounting_store()


def test_finance_manager_can_create_and_list_auxiliary_dimension():
    response = client.post(
        "/api/v1/accounting/dimensions",
        json={
            "account_set_id": "default",
            "dimension_type": "customer",
            "dimension_code": "CUST-SH-001",
            "dimension_name": "上海客户",
        },
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert response.status_code == 200
    assert response.json()["dimension_name"] == "上海客户"

    list_response = client.get(
        "/api/v1/accounting/dimensions?account_set_id=default&dimension_type=customer",
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1


def test_ledger_detail_accepts_dimension_filter_query_params():
    client.post(
        "/api/v1/accounting/dimensions",
        json={"account_set_id": "default", "dimension_type": "customer", "dimension_code": "CUST-SH-001", "dimension_name": "上海客户"},
        headers={"X-Actor-Id": "u-finance-manager"},
    )
    client.post(
        "/api/v1/accounting/journal-entries",
        json={
            "account_set_id": "default",
            "entry_date": "2026-06-18",
            "source_type": "manual_adjustment",
            "source_id": "api-dimension-entry",
            "description": "客户维度收入",
            "lines": [
                {"account_code": "1122", "account_name": "应收账款", "direction": "debit", "original_amount": "100.00", "base_amount": "100.00", "dimensions": [{"dimension_type": "customer", "dimension_code": "CUST-SH-001"}]},
                {"account_code": "6001", "account_name": "主营业务收入", "direction": "credit", "original_amount": "100.00", "base_amount": "100.00", "dimensions": [{"dimension_type": "customer", "dimension_code": "CUST-SH-001"}]},
            ],
        },
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    response = client.get(
        "/api/v1/ledger/detail?period=2026-06&account_code=1122&dimension_type=customer&dimension_code=CUST-SH-001",
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert response.status_code == 200
    assert response.json()["lines"][0]["dimensions"][0]["dimension_name"] == "上海客户"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
cd backend
python -m pytest tests/test_auxiliary_dimensions_api.py -q
```

Expected: FAIL with 404 for `/api/v1/accounting/dimensions`.

- [ ] **Step 3: Add accounting dimension endpoints**

Modify `backend/app/api/accounting.py` imports:

```python
from app.models.accounting import AuxiliaryDimensionCreate
from app.services.accounting_service import (
    list_auxiliary_dimensions,
    upsert_auxiliary_dimension,
)
```

Add endpoints:

```python
@router.get("/dimensions")
def get_dimensions(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    dimension_type: str | None = Query(default=None, max_length=40),
    x_actor_id: str = Header(default="system"),
):
    _require_accounting_permission(x_actor_id, "accounting.dimension.read", "accounting.dimension.read", f"dimensions:{account_set_id}:{dimension_type or 'all'}", {"account_set_id": account_set_id, "dimension_type": dimension_type})
    response = list_auxiliary_dimensions(account_set_id, dimension_type)
    _record_accounting_audit(x_actor_id, "accounting.dimension.read", f"dimensions:{account_set_id}:{dimension_type or 'all'}", {"account_set_id": account_set_id, "dimension_type": dimension_type, "dimension_count": response.total})
    return response


@router.post("/dimensions")
def save_dimension(request: AuxiliaryDimensionCreate, x_actor_id: str = Header(default="system")):
    _require_accounting_permission(x_actor_id, "accounting.dimension.write", "accounting.dimension.write", f"dimension:{request.account_set_id}:{request.dimension_type}:{request.dimension_code}", {"account_set_id": request.account_set_id, "dimension_type": request.dimension_type, "dimension_code": request.dimension_code})
    response = upsert_auxiliary_dimension(request)
    _record_accounting_audit(x_actor_id, "accounting.dimension.write", response.id, {"account_set_id": response.account_set_id, "dimension_type": response.dimension_type, "dimension_code": response.dimension_code})
    return response
```

- [ ] **Step 4: Add ledger API query params**

Modify `backend/app/api/ledger.py` `get_detail_ledger` signature:

```python
    dimension_type: str | None = Query(default=None, max_length=40),
    dimension_code: str | None = Query(default=None, max_length=64),
```

Pass into service:

```python
ledger = build_detail_ledger(period, account_code, account_set_id, dimension_type=dimension_type, dimension_code=dimension_code)
```

Add to audit metadata:

```python
"dimension_type": dimension_type,
"dimension_code": dimension_code,
```

- [ ] **Step 5: Add permissions and registry events**

Modify `backend/app/services/system_admin_service.py` finance manager permissions:

```python
"accounting.dimension.read",
"accounting.dimension.write",
```

Modify `backend/app/services/module_registry_service.py` audit events:

```python
"accounting.dimension.read",
"accounting.dimension.write",
```

- [ ] **Step 6: Run API tests**

Run:

```powershell
cd backend
python -m pytest tests/test_auxiliary_dimensions_api.py tests/test_accounting_api.py tests/test_ledger_api.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/api/accounting.py backend/app/api/ledger.py backend/app/services/system_admin_service.py backend/app/services/module_registry_service.py backend/tests/test_auxiliary_dimensions_api.py
git commit -m "feat: expose auxiliary dimension api"
```

## Task 5: 前端维度类型、API helper 与账簿展示

**Files:**
- Modify: `frontend/src/types/accounting.ts`
- Modify: `frontend/src/types/ledger.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Modify: `frontend/src/components/LedgerPanel.tsx`
- Create: `frontend/tests/auxiliaryDimensionsApi.test.mjs`
- Modify: `frontend/tests/ledgerPanel.test.mjs`

- [ ] **Step 1: Write failing frontend API tests**

Create `frontend/tests/auxiliaryDimensionsApi.test.mjs`:

```javascript
import assert from "node:assert/strict";
import test from "node:test";

import { fetchAuxiliaryDimensions, saveAuxiliaryDimension } from "../src/services/dashboardApi.ts";

test("fetchAuxiliaryDimensions calls accounting dimensions endpoint", async () => {
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    return {
      ok: true,
      json: async () => ({ account_set_id: "default", dimension_type: "customer", supported_dimension_types: [], total: 0, dimensions: [] })
    };
  };

  await fetchAuxiliaryDimensions("default", "customer", "http://api.local", fetcher, "u-finance-manager");

  assert.equal(calls[0].url, "http://api.local/api/v1/accounting/dimensions?account_set_id=default&dimension_type=customer");
  assert.equal(calls[0].options.headers["X-Actor-Id"], "u-finance-manager");
});

test("saveAuxiliaryDimension posts dimension payload", async () => {
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    return {
      ok: true,
      json: async () => ({ id: "default:customer:CUST-SH-001", dimension_name: "上海客户" })
    };
  };

  await saveAuxiliaryDimension(
    { account_set_id: "default", dimension_type: "customer", dimension_code: "CUST-SH-001", dimension_name: "上海客户", is_active: true },
    "http://api.local",
    fetcher,
    "u-finance-manager"
  );

  assert.equal(calls[0].url, "http://api.local/api/v1/accounting/dimensions");
  assert.equal(JSON.parse(calls[0].options.body).dimension_code, "CUST-SH-001");
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
cd frontend
npm test -- auxiliaryDimensionsApi
```

Expected: FAIL because helpers are missing.

- [ ] **Step 3: Add frontend dimension types**

Modify `frontend/src/types/accounting.ts`:

```typescript
export type AuxiliaryDimensionType =
  | "customer"
  | "supplier"
  | "employee"
  | "department"
  | "project"
  | "asset"
  | "platform"
  | "sku";

export interface AuxiliaryDimensionRecord {
  id: string;
  account_set_id: string;
  dimension_type: AuxiliaryDimensionType | string;
  dimension_code: string;
  dimension_name: string;
  is_active: boolean;
  updated_at: string;
}

export interface AuxiliaryDimensionCreateRequest {
  account_set_id: string;
  dimension_type: AuxiliaryDimensionType | string;
  dimension_code: string;
  dimension_name: string;
  is_active?: boolean;
}

export interface AuxiliaryDimensionListResponse {
  account_set_id: string;
  dimension_type: string | null;
  supported_dimension_types: string[];
  total: number;
  dimensions: AuxiliaryDimensionRecord[];
}

export interface JournalLineDimension {
  dimension_type: AuxiliaryDimensionType | string;
  dimension_code: string;
  dimension_name: string;
}
```

Modify `JournalLineRecord`:

```typescript
  dimensions: JournalLineDimension[];
```

Modify `frontend/src/types/ledger.ts`:

```typescript
export interface LedgerLineDimension {
  dimension_type: string;
  dimension_code: string;
  dimension_name: string;
}
```

Add to `LedgerDetailLine`:

```typescript
  dimensions: LedgerLineDimension[];
```

- [ ] **Step 4: Add dashboard API helpers**

Modify `frontend/src/services/dashboardApi.ts` imports:

```typescript
import type {
  AuxiliaryDimensionCreateRequest,
  AuxiliaryDimensionListResponse,
  AuxiliaryDimensionRecord
} from "../types/accounting";
```

Add helpers:

```typescript
export function fetchAuxiliaryDimensions(
  accountSetId = "default",
  dimensionType: string | null = null,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<AuxiliaryDimensionListResponse> {
  const typeQuery = dimensionType ? `&dimension_type=${encodeURIComponent(dimensionType)}` : "";
  return requestLedgerJson<AuxiliaryDimensionListResponse>(
    `/api/v1/accounting/dimensions?account_set_id=${encodeURIComponent(accountSetId)}${typeQuery}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function saveAuxiliaryDimension(
  request: AuxiliaryDimensionCreateRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<AuxiliaryDimensionRecord> {
  return mutateLedgerJson<AuxiliaryDimensionRecord>("/api/v1/accounting/dimensions", request, apiBase, fetcher, actorId);
}
```

Modify `fetchDetailLedger` to accept optional dimension filter:

```typescript
  dimensionType: string | null = null,
  dimensionCode: string | null = null
```

Append query params:

```typescript
const dimensionQuery =
  dimensionType && dimensionCode
    ? `&dimension_type=${encodeURIComponent(dimensionType)}&dimension_code=${encodeURIComponent(dimensionCode)}`
    : "";
```

- [ ] **Step 5: Display dimension tags in LedgerPanel**

In `LedgerPanel.tsx`, add a helper:

```tsx
function dimensionLabel(dimensions: Array<{ dimension_type: string; dimension_code: string; dimension_name: string }>) {
  return dimensions.length ? dimensions.map((dimension) => `${dimension.dimension_type}:${dimension.dimension_name}`).join(" / ") : "未挂维度";
}
```

In the detail ledger table, add a column:

```tsx
<th>辅助核算</th>
```

For each line:

```tsx
<td>{dimensionLabel(line.dimensions ?? [])}</td>
```

- [ ] **Step 6: Run frontend tests**

Run:

```powershell
cd frontend
npm test -- auxiliaryDimensionsApi
npm test -- ledgerPanel
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add frontend/src/types/accounting.ts frontend/src/types/ledger.ts frontend/src/services/dashboardApi.ts frontend/src/components/LedgerPanel.tsx frontend/tests/auxiliaryDimensionsApi.test.mjs frontend/tests/ledgerPanel.test.mjs
git commit -m "feat: show auxiliary dimensions in frontend"
```

## Task 6: 文档、验证与边界说明

**Files:**
- Modify: `README.md`
- Modify: `docs/01-mvp-design.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

- [ ] **Step 1: Update documentation**

Add to `README.md`:

```markdown
- 辅助核算维度三期：正式分录行支持客户、供应商、员工、部门、项目、资产、平台和 SKU 维度，明细账可展示并按维度过滤。
```

Add to `docs/01-mvp-design.md`:

```markdown
## 辅助核算维度三期边界

- 支持维护客户、供应商、员工、部门、项目、资产、平台和 SKU 辅助核算维度。
- 支持正式分录行挂载一个或多个辅助核算维度。
- 支持正式分录过账时校验维度主数据存在且启用。
- 支持明细账展示维度标签，并按维度过滤查询。
- 当前不实现完整应收应付账龄、项目成本归集、固定资产卡片联动、SKU 利润核算或部门预算控制。
```

Add to `docs/02-api-design.md`:

````markdown
## 辅助核算维度三期

```text
GET /api/v1/accounting/dimensions?account_set_id=default
GET /api/v1/accounting/dimensions?account_set_id=default&dimension_type=customer
POST /api/v1/accounting/dimensions
GET /api/v1/ledger/detail?period=2026-06&account_code=1122&dimension_type=customer&dimension_code=CUST-SH-001
```

正式分录行支持：

```json
{
  "dimensions": [
    { "dimension_type": "customer", "dimension_code": "CUST-SH-001" }
  ]
}
```

后端会校验维度主数据存在且启用，并在正式分录行中保存维度名称快照。
````

Add to `docs/03-frd-v1.0.md`:

```markdown
当前辅助核算接入状态：

- 已支持客户、供应商、员工、部门、项目、资产、平台和 SKU 维度主数据。
- 已支持正式分录行挂载辅助核算维度。
- 已支持明细账按辅助核算维度过滤。
- 应收应付账龄、项目成本、固定资产卡片、部门预算和 SKU 利润分析进入后续专业子模块。
```

- [ ] **Step 2: Run backend full tests**

Run:

```powershell
cd backend
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 3: Run frontend full tests**

Run:

```powershell
cd frontend
npm test
```

Expected: PASS.

- [ ] **Step 4: Run build check**

Run:

```powershell
cd frontend
npm run build
```

Expected: PASS with Vite build output.

- [ ] **Step 5: Commit docs**

```powershell
git add README.md docs/01-mvp-design.md docs/02-api-design.md docs/03-frd-v1.0.md
git commit -m "docs: document auxiliary dimensions phase three"
```

## Self-Review

- Spec coverage: Covers dimension master data, journal line dimensions, validation, dimension-filtered ledger queries, API, permissions, frontend display and docs.
- Placeholder scan: No unresolved placeholder text is used.
- Type consistency: Backend `AuxiliaryDimensionCreate`, `AuxiliaryDimensionRecord`, `JournalLineDimension`, `JournalLineDimensionRecord` map to frontend `AuxiliaryDimensionCreateRequest`, `AuxiliaryDimensionRecord`, `JournalLineDimension`.
- Scope check: Full accounts receivable/payable aging, project costing, fixed asset card linkage, departmental budget control and SKU profit accounting are intentionally left for later specialized modules.
