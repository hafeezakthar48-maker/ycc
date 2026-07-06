# Formal Accounting Engine Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立正式会计核算引擎一期，让已审核凭证正式过账为不可变分录，并让账簿、报表和前端展示优先读取正式分录来源。

**Architecture:** 新增并行正式核算内核，不推翻现有凭证中心。后端新增 `accounting` 模型、服务和 API；凭证中心过账调用正式分录服务；账簿和报表优先读取正式分录，无正式分录时保留现有 MVP 回退。

**Tech Stack:** FastAPI、Pydantic、SQLite、pytest、React、TypeScript、Vite、Node test runner。

---

## File Structure

- Create: `backend/app/models/accounting.py`
  - 定义科目、正式分录、分录行、列表响应和数据来源类型。
- Create: `backend/app/services/accounting_service.py`
  - 管理正式核算 SQLite 表、内置科目、正式过账、冲销、查询和测试重置。
- Create: `backend/app/api/accounting.py`
  - 暴露正式科目和正式分录读取 API。
- Modify: `backend/app/api/router_registry.py`
  - 注册 `accounting` 路由。
- Modify: `backend/app/models/voucher_center.py`
  - 为凭证记录增加 `journal_entry_id`、`journal_reversal_entry_id`。
- Modify: `backend/app/services/voucher_center_service.py`
  - 将 `post_voucher` / `unpost_voucher` 升级为正式过账和正式冲销。
- Modify: `backend/app/services/accounting_period_service.py`
  - 关闭期间时继续检查未过账凭证，并让正式过账服务阻止已关闭期间新增分录。
- Modify: `backend/app/models/ledger.py`
  - 为账簿响应增加 `source` 字段，标识 `formal_journal_entries` 或 `mvp_voucher_workflow`。
- Modify: `backend/app/services/ledger_service.py`
  - 优先从正式分录构建总账、明细账和科目余额表；无正式分录时回退现有凭证工作流。
- Modify: `backend/app/services/financial_statement_service.py`
  - 通过账簿服务优先读取正式分录，并把报表来源传递到响应。
- Modify: `backend/app/services/system_admin_service.py`
  - 增加正式核算权限到财务经理角色。
- Modify: `backend/app/services/module_registry_service.py`
  - 为 AI 财务中心登记 `/api/v1/accounting` 和正式核算事件。
- Modify: `frontend/src/types/ledger.ts`
  - 为账簿响应增加 `source`。
- Create: `frontend/src/types/accounting.ts`
  - 定义前端正式科目和正式分录类型。
- Modify: `frontend/src/types/voucherCenter.ts`
  - 增加正式分录 ID 字段。
- Modify: `frontend/src/services/dashboardApi.ts`
  - 增加正式分录读取 API，保留现有凭证和账簿调用。
- Modify: `frontend/src/components/VoucherCenterPanel.tsx`
  - 显示正式分录号和冲销分录号。
- Modify: `frontend/src/components/LedgerPanel.tsx`
  - 显示账簿数据来源。
- Modify: `frontend/src/components/FinancialStatementPanel.tsx`
  - 显示正式分录来源。
- Modify: `README.md`, `docs/01-mvp-design.md`, `docs/02-api-design.md`, `docs/03-frd-v1.0.md`
  - 记录正式核算一期边界。
- Test: `backend/tests/test_accounting_service.py`
- Test: `backend/tests/test_accounting_api.py`
- Test: `backend/tests/test_voucher_formal_posting_api.py`
- Modify: `backend/tests/test_ledger_service.py`
- Modify: `backend/tests/test_financial_statement_service.py`
- Test: `frontend/tests/accountingApi.test.mjs`
- Modify: `frontend/tests/voucherPostingPanel.test.mjs`
- Modify: `frontend/tests/ledgerPanel.test.mjs`
- Modify: `frontend/tests/financialStatementPanel.test.mjs`

## Task 1: 正式核算模型与内置科目

**Files:**
- Create: `backend/app/models/accounting.py`
- Create: `backend/app/services/accounting_service.py`
- Create: `backend/tests/test_accounting_service.py`

- [ ] **Step 1: Write the failing model/service tests**

Add to `backend/tests/test_accounting_service.py`:

```python
from decimal import Decimal

from app.services.accounting_service import (
    get_chart_of_accounts,
    reset_accounting_store,
)


def setup_function():
    reset_accounting_store()


def test_chart_of_accounts_contains_required_mvp_accounts():
    accounts = get_chart_of_accounts("default").accounts

    account_codes = {account.account_code for account in accounts}
    assert {"1001", "1122", "2202", "6001", "6602"}.issubset(account_codes)
    cash = next(account for account in accounts if account.account_code == "1001")
    assert cash.account_name == "库存现金"
    assert cash.account_type == "asset"
    assert cash.normal_balance == "debit"
    assert cash.is_active is True
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
python -m pytest tests/test_accounting_service.py::test_chart_of_accounts_contains_required_mvp_accounts -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.accounting_service'`.

- [ ] **Step 3: Create accounting models**

Create `backend/app/models/accounting.py`:

```python
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AccountType = Literal["asset", "liability", "equity", "revenue", "cost", "expense"]
NormalBalance = Literal["debit", "credit"]
JournalDirection = Literal["debit", "credit"]
JournalStatus = Literal["posted", "reversed"]
LedgerSource = Literal["formal_journal_entries", "mvp_voucher_workflow", "sample_finance_data"]


class AccountItem(BaseModel):
    account_set_id: str
    account_code: str
    account_name: str
    account_type: AccountType
    normal_balance: NormalBalance
    is_active: bool = True


class AccountListResponse(BaseModel):
    account_set_id: str
    accounts: list[AccountItem]


class JournalLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_code: str = Field(min_length=1, max_length=32)
    account_name: str = Field(min_length=1, max_length=80)
    direction: JournalDirection
    currency: str = Field(default="CNY", min_length=3, max_length=3)
    original_amount: Decimal = Field(gt=0, max_digits=16, decimal_places=2)
    exchange_rate: Decimal = Field(default=Decimal("1.000000"), gt=0, max_digits=18, decimal_places=6)
    base_amount: Decimal = Field(gt=0, max_digits=16, decimal_places=2)
    description: str = Field(default="", max_length=200)


class JournalEntryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    entry_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    source_type: str = Field(min_length=1, max_length=40)
    source_id: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=200)
    base_currency: str = Field(default="CNY", min_length=3, max_length=3)
    created_by: str = Field(default="system", min_length=1, max_length=60)
    posted_by: str = Field(default="system", min_length=1, max_length=60)
    lines: list[JournalLineCreate] = Field(min_length=2, max_length=100)


class JournalLineRecord(JournalLineCreate):
    id: str
    journal_entry_id: str
    line_no: int


class JournalEntryRecord(BaseModel):
    id: str
    account_set_id: str
    period: str
    entry_date: str
    entry_number: str
    source_type: str
    source_id: str
    description: str
    status: JournalStatus
    base_currency: str
    created_by: str
    posted_by: str
    posted_at: str
    reversal_of_entry_id: str | None = None
    lines: list[JournalLineRecord]


class JournalEntryListResponse(BaseModel):
    account_set_id: str
    period: str | None = None
    total: int
    entries: list[JournalEntryRecord]
```

- [ ] **Step 4: Create minimal accounting service with chart of accounts**

Create `backend/app/services/accounting_service.py` with the initial account registry:

```python
from app.models.accounting import AccountItem, AccountListResponse
from app.services.accounting_period_service import validate_account_set


_BASE_ACCOUNTS: tuple[AccountItem, ...] = (
    AccountItem(account_set_id="default", account_code="1001", account_name="库存现金", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="1002", account_name="银行存款", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="1122", account_name="应收账款", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="1405", account_name="库存商品", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="1601", account_name="固定资产", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="2001", account_name="短期借款", account_type="liability", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="2202", account_name="应付账款", account_type="liability", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="2221", account_name="应交税费", account_type="liability", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="4001", account_name="实收资本", account_type="equity", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="6001", account_name="主营业务收入", account_type="revenue", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="6051", account_name="其他业务收入", account_type="revenue", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="6401", account_name="主营业务成本", account_type="cost", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="6601", account_name="销售费用", account_type="expense", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="6602", account_name="管理费用", account_type="expense", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="6603", account_name="财务费用", account_type="expense", normal_balance="debit"),
)


def reset_accounting_store() -> None:
    return None


def get_chart_of_accounts(account_set_id: str = "default") -> AccountListResponse:
    validate_account_set(account_set_id)
    accounts = [account.model_copy(update={"account_set_id": account_set_id}) for account in _BASE_ACCOUNTS]
    return AccountListResponse(account_set_id=account_set_id, accounts=accounts)
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```powershell
cd backend
python -m pytest tests/test_accounting_service.py::test_chart_of_accounts_contains_required_mvp_accounts -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/models/accounting.py backend/app/services/accounting_service.py backend/tests/test_accounting_service.py
git commit -m "feat: add accounting domain accounts"
```

## Task 2: 正式分录持久化、过账与冲销

**Files:**
- Modify: `backend/app/services/accounting_service.py`
- Modify: `backend/tests/test_accounting_service.py`

- [ ] **Step 1: Write failing journal posting tests**

Append to `backend/tests/test_accounting_service.py`:

```python
import pytest
from fastapi import HTTPException

from app.models.accounting import JournalEntryCreate, JournalLineCreate
from app.services.accounting_service import (
    get_journal_entry,
    list_journal_entries,
    post_journal_entry,
    reverse_journal_entry,
)


def _balanced_entry(source_id="voucher-1"):
    return JournalEntryCreate(
        account_set_id="default",
        entry_date="2026-06-18",
        source_type="voucher_center",
        source_id=source_id,
        description="费用采购正式过账",
        created_by="财务主管",
        posted_by="财务主管",
        lines=[
            JournalLineCreate(
                account_code="6602",
                account_name="管理费用",
                direction="debit",
                original_amount=Decimal("100.00"),
                base_amount=Decimal("100.00"),
                description="费用",
            ),
            JournalLineCreate(
                account_code="2202",
                account_name="应付账款",
                direction="credit",
                original_amount=Decimal("100.00"),
                base_amount=Decimal("100.00"),
                description="应付",
            ),
        ],
    )


def test_post_journal_entry_persists_immutable_entry():
    entry = post_journal_entry(_balanced_entry())

    loaded = get_journal_entry(entry.id)
    assert loaded.entry_number == "JE-202606-0001"
    assert loaded.period == "2026-06"
    assert loaded.status == "posted"
    assert loaded.lines[0].line_no == 1
    assert list_journal_entries("default", "2026-06").total == 1


def test_post_journal_entry_rejects_unbalanced_base_amounts():
    request = _balanced_entry("voucher-unbalanced")
    request.lines[1].base_amount = Decimal("99.99")

    with pytest.raises(HTTPException) as exc_info:
        post_journal_entry(request)

    assert exc_info.value.status_code == 422
    assert "借贷不平衡" in exc_info.value.detail


def test_reverse_journal_entry_creates_reversal_without_deleting_original():
    entry = post_journal_entry(_balanced_entry())

    reversal = reverse_journal_entry(entry.id, operator="财务主管")

    original = get_journal_entry(entry.id)
    assert original.status == "reversed"
    assert reversal.reversal_of_entry_id == entry.id
    assert reversal.lines[0].direction == "credit"
    assert reversal.lines[1].direction == "debit"
    assert list_journal_entries("default", "2026-06").total == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
cd backend
python -m pytest tests/test_accounting_service.py -q
```

Expected: FAIL with missing `post_journal_entry`, `get_journal_entry`, `list_journal_entries`, `reverse_journal_entry`.

- [ ] **Step 3: Implement SQLite-backed journal store**

Modify `backend/app/services/accounting_service.py` to add:

```python
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from fastapi import HTTPException

from app.models.accounting import (
    JournalEntryCreate,
    JournalEntryListResponse,
    JournalEntryRecord,
    JournalLineRecord,
)
from app.services.accounting_period_service import is_accounting_period_closed


DEFAULT_ACCOUNTING_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "formal_accounting.sqlite3"
ACCOUNTING_DB_PATH_ENV = "FINANCE_AI_ACCOUNTING_DB_PATH"


def post_journal_entry(request: JournalEntryCreate) -> JournalEntryRecord:
    validate_account_set(request.account_set_id)
    period = request.entry_date[:7]
    if is_accounting_period_closed(period, request.account_set_id):
        raise HTTPException(status_code=409, detail="会计期间已关闭，不能正式过账。")
    _validate_accounts(request.account_set_id, request.lines)
    _validate_balance(request.lines)
    with _connection() as connection:
        existing = connection.execute(
            "SELECT id FROM journal_entries WHERE source_type = ? AND source_id = ? AND status = 'posted'",
            (request.source_type, request.source_id),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="来源凭证已正式过账。")
        entry = _build_entry(connection, request, period, reversal_of_entry_id=None)
        _insert_entry(connection, entry)
    return entry


def reverse_journal_entry(entry_id: str, operator: str) -> JournalEntryRecord:
    original = get_journal_entry(entry_id)
    if original.status == "reversed":
        raise HTTPException(status_code=409, detail="正式分录已冲销。")
    if is_accounting_period_closed(original.period, original.account_set_id):
        raise HTTPException(status_code=409, detail="会计期间已关闭，不能反过账。")
    request = JournalEntryCreate(
        account_set_id=original.account_set_id,
        entry_date=original.entry_date,
        source_type="journal_reversal",
        source_id=original.id,
        description=f"冲销：{original.description}",
        base_currency=original.base_currency,
        created_by=operator,
        posted_by=operator,
        lines=[
            line.model_copy(update={"direction": "credit" if line.direction == "debit" else "debit"})
            for line in original.lines
        ],
    )
    with _connection() as connection:
        reversal = _build_entry(connection, request, original.period, reversal_of_entry_id=original.id)
        _insert_entry(connection, reversal)
        connection.execute("UPDATE journal_entries SET status = 'reversed' WHERE id = ?", (original.id,))
    return reversal
```

Add helper functions in the same file:

```python
def list_journal_entries(account_set_id: str = "default", period: str | None = None) -> JournalEntryListResponse:
    validate_account_set(account_set_id)
    query = "SELECT payload_json FROM journal_entries WHERE account_set_id = ?"
    params: list[str] = [account_set_id]
    if period:
        query += " AND period = ?"
        params.append(period)
    query += " ORDER BY entry_number"
    with _connection() as connection:
        rows = connection.execute(query, params).fetchall()
    entries = [JournalEntryRecord.model_validate_json(row["payload_json"]) for row in rows]
    return JournalEntryListResponse(account_set_id=account_set_id, period=period, total=len(entries), entries=entries)


def get_journal_entry(entry_id: str) -> JournalEntryRecord:
    with _connection() as connection:
        row = connection.execute("SELECT payload_json FROM journal_entries WHERE id = ?", (entry_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="正式分录不存在。")
    return JournalEntryRecord.model_validate_json(row["payload_json"])


def reset_accounting_store() -> None:
    with _connection() as connection:
        connection.execute("DELETE FROM journal_entries")
        connection.execute("DELETE FROM journal_sequences")
```

Implement schema and validation:

```python
def _validate_accounts(account_set_id: str, lines) -> None:
    active_codes = {account.account_code for account in get_chart_of_accounts(account_set_id).accounts if account.is_active}
    for line in lines:
        if line.account_code not in active_codes:
            raise HTTPException(status_code=422, detail=f"科目不存在或未启用：{line.account_code}")


def _validate_balance(lines) -> None:
    debit_total = sum((line.base_amount for line in lines if line.direction == "debit"), Decimal("0.00"))
    credit_total = sum((line.base_amount for line in lines if line.direction == "credit"), Decimal("0.00"))
    if debit_total != credit_total:
        raise HTTPException(status_code=422, detail="正式分录借贷不平衡。")


def _build_entry(connection: sqlite3.Connection, request: JournalEntryCreate, period: str, reversal_of_entry_id: str | None) -> JournalEntryRecord:
    entry_id = f"je-{uuid4().hex[:12]}"
    entry_number = _next_entry_number(connection, period)
    posted_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    lines = [
        JournalLineRecord(
            id=f"jl-{uuid4().hex[:12]}",
            journal_entry_id=entry_id,
            line_no=index,
            **line.model_dump(),
        )
        for index, line in enumerate(request.lines, start=1)
    ]
    return JournalEntryRecord(
        id=entry_id,
        account_set_id=request.account_set_id,
        period=period,
        entry_date=request.entry_date,
        entry_number=entry_number,
        source_type=request.source_type,
        source_id=request.source_id,
        description=request.description,
        status="posted",
        base_currency=request.base_currency,
        created_by=request.created_by,
        posted_by=request.posted_by,
        posted_at=posted_at,
        reversal_of_entry_id=reversal_of_entry_id,
        lines=lines,
    )


def _insert_entry(connection: sqlite3.Connection, entry: JournalEntryRecord) -> None:
    connection.execute(
        """
        INSERT INTO journal_entries (
            id, account_set_id, period, entry_date, entry_number,
            source_type, source_id, status, payload_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            entry.id,
            entry.account_set_id,
            entry.period,
            entry.entry_date,
            entry.entry_number,
            entry.source_type,
            entry.source_id,
            entry.status,
            entry.model_dump_json(),
        ),
    )
```

Add connection helpers:

```python
def _next_entry_number(connection: sqlite3.Connection, period: str) -> str:
    sequence_key = period.replace("-", "")
    row = connection.execute(
        "SELECT last_sequence FROM journal_sequences WHERE period_key = ?",
        (sequence_key,),
    ).fetchone()
    sequence = int(row["last_sequence"]) + 1 if row else 1
    connection.execute(
        """
        INSERT INTO journal_sequences (period_key, last_sequence)
        VALUES (?, ?)
        ON CONFLICT(period_key) DO UPDATE SET last_sequence = excluded.last_sequence
        """,
        (sequence_key, sequence),
    )
    return f"JE-{sequence_key}-{sequence:04d}"


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    db_path = Path(os.environ.get(ACCOUNTING_DB_PATH_ENV, DEFAULT_ACCOUNTING_DB_PATH))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        _ensure_schema(connection)
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS journal_entries (
            id TEXT PRIMARY KEY,
            account_set_id TEXT NOT NULL,
            period TEXT NOT NULL,
            entry_date TEXT NOT NULL,
            entry_number TEXT NOT NULL UNIQUE,
            source_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            status TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS journal_sequences (
            period_key TEXT PRIMARY KEY,
            last_sequence INTEGER NOT NULL
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_journal_entries_period ON journal_entries (account_set_id, period)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_journal_entries_source ON journal_entries (source_type, source_id)")
```

- [ ] **Step 4: Run service tests**

Run:

```powershell
cd backend
python -m pytest tests/test_accounting_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/accounting_service.py backend/tests/test_accounting_service.py
git commit -m "feat: persist formal journal entries"
```

## Task 3: 凭证中心正式过账集成

**Files:**
- Modify: `backend/app/models/voucher_center.py`
- Modify: `backend/app/services/voucher_center_service.py`
- Create: `backend/tests/test_voucher_formal_posting_api.py`

- [ ] **Step 1: Write failing API tests for formal posting**

Create `backend/tests/test_voucher_formal_posting_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import app
from app.services.accounting_period_service import reset_accounting_period_store
from app.services.accounting_service import list_journal_entries, reset_accounting_store
from app.services.voucher_center_service import reset_voucher_store


client = TestClient(app)


def setup_function():
    reset_voucher_store()
    reset_accounting_period_store()
    reset_accounting_store()


def _create_reviewed_voucher():
    response = client.post(
        "/api/v1/vouchers/center",
        json={
            "account_set_id": "default",
            "voucher_date": "2026-06-18",
            "summary": "费用采购",
            "counterparty": "上海服务商",
            "invoice_number": "INV-001",
            "amount": "100.00",
            "tax_amount": "0.00",
            "total_amount_with_tax": "100.00",
            "lines": [
                {"account_code": "6602", "account_name": "管理费用", "direction": "借", "amount": "100.00", "explanation": "费用"},
                {"account_code": "2202", "account_name": "应付账款", "direction": "贷", "amount": "100.00", "explanation": "应付"},
            ],
        },
        headers={"X-Actor-Id": "u-finance-manager"},
    )
    voucher_id = response.json()["id"]
    client.post(f"/api/v1/vouchers/center/{voucher_id}/review", json={"reviewer": "财务主管"}, headers={"X-Actor-Id": "u-finance-manager"})
    return voucher_id


def test_post_voucher_creates_formal_journal_entry():
    voucher_id = _create_reviewed_voucher()

    response = client.post(
        f"/api/v1/vouchers/center/{voucher_id}/post",
        json={"operator": "财务主管"},
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["posting_status"] == "posted"
    assert payload["journal_entry_id"].startswith("je-")
    entries = list_journal_entries("default", "2026-06").entries
    assert entries[0].source_id == voucher_id
    assert entries[0].entry_number == "JE-202606-0001"


def test_unpost_voucher_creates_reversal_journal_entry():
    voucher_id = _create_reviewed_voucher()
    posted = client.post(
        f"/api/v1/vouchers/center/{voucher_id}/post",
        json={"operator": "财务主管"},
        headers={"X-Actor-Id": "u-finance-manager"},
    ).json()

    response = client.post(
        f"/api/v1/vouchers/center/{voucher_id}/unpost",
        json={"operator": "财务主管"},
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["posting_status"] == "unposted"
    assert payload["journal_reversal_entry_id"].startswith("je-")
    entries = list_journal_entries("default", "2026-06").entries
    assert len(entries) == 2
    assert entries[1].reversal_of_entry_id == posted["journal_entry_id"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
cd backend
python -m pytest tests/test_voucher_formal_posting_api.py -q
```

Expected: FAIL because `journal_entry_id` is missing from voucher response.

- [ ] **Step 3: Extend voucher model**

Modify `backend/app/models/voucher_center.py` `VoucherCenterRecord`:

```python
class VoucherCenterRecord(BaseModel):
    id: str
    account_set_id: str = "default"
    voucher_number: str
    voucher_date: str
    summary: str
    counterparty: str
    invoice_number: str | None = None
    amount: Decimal
    tax_amount: Decimal
    total_amount_with_tax: Decimal
    lines: list[VoucherCenterLine]
    status: str
    reviewed_by: str | None = None
    posting_status: Literal["unposted", "posted"] = "unposted"
    posted_by: str | None = None
    posted_at: str | None = None
    journal_entry_id: str | None = None
    journal_reversal_entry_id: str | None = None
    audit_result: AuditResponse | None = None
    attachments: list[VoucherAttachment] = Field(default_factory=list)
```

- [ ] **Step 4: Modify posting service to call accounting service**

Modify `backend/app/services/voucher_center_service.py` imports:

```python
from app.models.accounting import JournalEntryCreate, JournalLineCreate
from app.services.accounting_service import post_journal_entry, reverse_journal_entry
```

In `post_voucher`, replace status-only update with formal posting:

```python
    journal_entry = post_journal_entry(
        JournalEntryCreate(
            account_set_id=voucher.account_set_id,
            entry_date=voucher.voucher_date,
            source_type="voucher_center",
            source_id=voucher.id,
            description=voucher.summary,
            base_currency="CNY",
            created_by=operator,
            posted_by=operator,
            lines=[
                JournalLineCreate(
                    account_code=line.account_code,
                    account_name=line.account_name,
                    direction="debit" if line.direction == "借" else "credit",
                    currency="CNY",
                    original_amount=line.amount,
                    exchange_rate=Decimal("1.000000"),
                    base_amount=line.amount,
                    description=line.explanation,
                )
                for line in voucher.lines
            ],
        )
    )
    updated = voucher.model_copy(
        update={
            "posting_status": "posted",
            "posted_by": operator,
            "posted_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "journal_entry_id": journal_entry.id,
        }
    )
```

In `unpost_voucher`, create reversal:

```python
    if not voucher.journal_entry_id:
        raise HTTPException(status_code=409, detail="凭证缺少正式分录，不能正式反过账。")
    reversal = reverse_journal_entry(voucher.journal_entry_id, operator="财务主管")
    updated = voucher.model_copy(
        update={
            "posting_status": "unposted",
            "posted_by": None,
            "posted_at": None,
            "journal_reversal_entry_id": reversal.id,
        }
    )
```

- [ ] **Step 5: Run voucher formal posting tests**

Run:

```powershell
cd backend
python -m pytest tests/test_voucher_formal_posting_api.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/models/voucher_center.py backend/app/services/voucher_center_service.py backend/tests/test_voucher_formal_posting_api.py
git commit -m "feat: post vouchers to formal journal"
```

## Task 4: 正式核算 API、权限与模块注册

**Files:**
- Create: `backend/app/api/accounting.py`
- Modify: `backend/app/api/router_registry.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Create: `backend/tests/test_accounting_api.py`

- [ ] **Step 1: Write failing API tests**

Create `backend/tests/test_accounting_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import app
from app.services.accounting_service import reset_accounting_store


client = TestClient(app)


def setup_function():
    reset_accounting_store()


def test_get_accounting_accounts_requires_accounting_permission():
    response = client.get("/api/v1/accounting/accounts?account_set_id=default", headers={"X-Actor-Id": "u-auditor"})

    assert response.status_code == 403


def test_finance_manager_can_read_accounting_accounts():
    response = client.get("/api/v1/accounting/accounts?account_set_id=default", headers={"X-Actor-Id": "u-finance-manager"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["account_set_id"] == "default"
    assert any(account["account_code"] == "1001" for account in payload["accounts"])


def test_finance_center_registry_includes_accounting_api():
    response = client.get("/api/v1/modules/finance-center")

    assert response.status_code == 200
    module = response.json()
    assert "/api/v1/accounting" in module["api_prefixes"]
    assert "accounting.entry.post" in module["audit_events"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
cd backend
python -m pytest tests/test_accounting_api.py -q
```

Expected: FAIL with 404 for `/api/v1/accounting/accounts`.

- [ ] **Step 3: Create accounting router**

Create `backend/app/api/accounting.py`:

```python
from fastapi import APIRouter, Header, HTTPException, Query

from app.models.system_admin import AuditLogCreateRequest
from app.services.accounting_service import get_chart_of_accounts, get_journal_entry, list_journal_entries
from app.services.system_admin_service import authorize, record_audit_log


router = APIRouter(prefix="/api/v1/accounting", tags=["accounting"])


@router.get("/accounts")
def get_accounts(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    x_actor_id: str = Header(default="system"),
):
    _require_accounting_permission(x_actor_id, "accounting.account.read", "accounting.account.read", f"accounts:{account_set_id}", {"account_set_id": account_set_id})
    response = get_chart_of_accounts(account_set_id)
    _record_accounting_audit(x_actor_id, "accounting.account.read", f"accounts:{account_set_id}", {"account_set_id": account_set_id, "account_count": len(response.accounts)})
    return response


@router.get("/journal-entries")
def get_journal_entries(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    period: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    x_actor_id: str = Header(default="system"),
):
    _require_accounting_permission(x_actor_id, "accounting.entry.read", "accounting.entry.read", f"journal-entries:{account_set_id}:{period or 'all'}", {"account_set_id": account_set_id, "period": period})
    response = list_journal_entries(account_set_id, period)
    _record_accounting_audit(x_actor_id, "accounting.entry.read", f"journal-entries:{account_set_id}:{period or 'all'}", {"account_set_id": account_set_id, "period": period, "entry_count": response.total})
    return response


@router.get("/journal-entries/{entry_id}")
def get_journal_entry_detail(entry_id: str, x_actor_id: str = Header(default="system")):
    _require_accounting_permission(x_actor_id, "accounting.entry.read", "accounting.entry.read", f"journal-entry:{entry_id}", {"entry_id": entry_id})
    entry = get_journal_entry(entry_id)
    _record_accounting_audit(x_actor_id, "accounting.entry.read", f"journal-entry:{entry_id}", {"entry_id": entry_id, "account_set_id": entry.account_set_id, "period": entry.period})
    return entry


def _record_accounting_audit(actor_id: str, event: str, target_id: str, metadata: dict[str, str | int | float | bool | None], result: str = "success") -> None:
    record_audit_log(AuditLogCreateRequest(actor_id=actor_id, module_id="finance-center", event=event, target_id=target_id, result=result, metadata=metadata))


def _require_accounting_permission(actor_id: str, permission_code: str, event: str, target_id: str, metadata: dict[str, str | int | float | bool | None]) -> None:
    if actor_id == "system":
        return
    decision = authorize(actor_id, permission_code)
    if decision.allowed:
        return
    _record_accounting_audit(actor_id, event, target_id, {**metadata, "permission_code": permission_code, "reason": decision.reason}, result="denied")
    raise HTTPException(status_code=403, detail=decision.reason)
```

- [ ] **Step 4: Register router and permissions**

Modify `backend/app/api/router_registry.py`:

```python
from app.api.accounting import router as accounting_router
```

Inside `include_api_routers`:

```python
    app.include_router(accounting_router)
```

Modify `backend/app/services/system_admin_service.py` finance manager permissions to include:

```python
"accounting.account.read",
"accounting.entry.read",
"accounting.entry.post",
"accounting.entry.reverse",
```

Modify `backend/app/services/module_registry_service.py` finance center registration to include:

```python
"/api/v1/accounting",
```

and audit events:

```python
"accounting.account.read",
"accounting.entry.read",
"accounting.entry.post",
"accounting.entry.reverse",
```

- [ ] **Step 5: Run API tests**

Run:

```powershell
cd backend
python -m pytest tests/test_accounting_api.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/api/accounting.py backend/app/api/router_registry.py backend/app/services/system_admin_service.py backend/app/services/module_registry_service.py backend/tests/test_accounting_api.py
git commit -m "feat: expose formal accounting api"
```

## Task 5: 账簿读模型迁移到正式分录

**Files:**
- Modify: `backend/app/models/ledger.py`
- Modify: `backend/app/services/ledger_service.py`
- Modify: `backend/tests/test_ledger_service.py`

- [ ] **Step 1: Write failing ledger source tests**

Append to `backend/tests/test_ledger_service.py`:

```python
from app.models.accounting import JournalEntryCreate, JournalLineCreate
from app.services.accounting_service import post_journal_entry, reset_accounting_store


def test_general_ledger_prefers_formal_journal_entries():
    reset_accounting_store()
    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-18",
            source_type="manual_adjustment",
            source_id="manual-1",
            description="正式分录测试",
            lines=[
                JournalLineCreate(account_code="6602", account_name="管理费用", direction="debit", original_amount=Decimal("100.00"), base_amount=Decimal("100.00")),
                JournalLineCreate(account_code="2202", account_name="应付账款", direction="credit", original_amount=Decimal("100.00"), base_amount=Decimal("100.00")),
            ],
        )
    )

    ledger = build_general_ledger("2026-06", "default")

    assert ledger.source == "formal_journal_entries"
    assert ledger.entry_count == 2
    assert ledger.total_debit == Decimal("100.00")
    assert ledger.total_credit == Decimal("100.00")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
python -m pytest tests/test_ledger_service.py::test_general_ledger_prefers_formal_journal_entries -q
```

Expected: FAIL because `GeneralLedgerResponse` has no `source`.

- [ ] **Step 3: Add source to ledger models**

Modify `backend/app/models/ledger.py` response models:

```python
class GeneralLedgerResponse(BaseModel):
    source: str = "mvp_voucher_workflow"
    period: str
    voucher_count: int
    entry_count: int
    total_debit: Decimal
    total_credit: Decimal
    balanced: bool
    accounts: list[LedgerAccountSummary]
```

Add the same `source: str = "mvp_voucher_workflow"` field to `DetailLedgerResponse` and `AccountBalanceTableResponse`.

- [ ] **Step 4: Implement formal journal ledger builder**

Modify `backend/app/services/ledger_service.py`:

```python
from app.services.accounting_service import list_journal_entries
```

At the beginning of `build_general_ledger`:

```python
    formal_entries = list_journal_entries(account_set_id, period).entries
    if formal_entries:
        accounts = _build_account_summaries_from_journal_entries(formal_entries)
        total_debit = sum((account.debit_total for account in accounts), ZERO)
        total_credit = sum((account.credit_total for account in accounts), ZERO)
        return GeneralLedgerResponse(
            source="formal_journal_entries",
            period=period,
            voucher_count=len({entry.source_id for entry in formal_entries if entry.source_type == "voucher_center"}),
            entry_count=sum(account.entry_count for account in accounts),
            total_debit=total_debit,
            total_credit=total_credit,
            balanced=total_debit == total_credit,
            accounts=accounts,
        )
```

Add helper:

```python
def _build_account_summaries_from_journal_entries(entries) -> list[LedgerAccountSummary]:
    accounts: dict[str, _AccountAccumulator] = {}
    for entry in entries:
        for line in entry.lines:
            account = accounts.setdefault(line.account_code, _AccountAccumulator(account_code=line.account_code, account_name=line.account_name))
            if line.direction == "debit":
                account.debit_total += line.base_amount
            else:
                account.credit_total += line.base_amount
            account.entry_count += 1
    summaries = []
    for account in sorted(accounts.values(), key=lambda item: item.account_code):
        balance_direction, balance_amount = _balance(account.debit_total, account.credit_total)
        summaries.append(
            LedgerAccountSummary(
                account_code=account.account_code,
                account_name=account.account_name,
                debit_total=account.debit_total,
                credit_total=account.credit_total,
                balance_direction=balance_direction,
                balance_amount=balance_amount,
                entry_count=account.entry_count,
            )
        )
    return summaries
```

Update detail ledger similarly: if formal entries exist, flatten lines for `account_code`, mapping `entry.entry_number` into `voucher_number` and `entry.description` into `summary`.

- [ ] **Step 5: Run ledger tests**

Run:

```powershell
cd backend
python -m pytest tests/test_ledger_service.py tests/test_ledger_api.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/models/ledger.py backend/app/services/ledger_service.py backend/tests/test_ledger_service.py
git commit -m "feat: read ledgers from formal journal"
```

## Task 6: 财务报表优先读取正式分录

**Files:**
- Modify: `backend/app/services/financial_statement_service.py`
- Modify: `backend/tests/test_financial_statement_service.py`

- [ ] **Step 1: Write failing statement source test**

Append to `backend/tests/test_financial_statement_service.py`:

```python
from app.models.accounting import JournalEntryCreate, JournalLineCreate
from app.services.accounting_service import post_journal_entry, reset_accounting_store


def test_financial_statements_prefer_formal_journal_entries():
    reset_accounting_store()
    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-18",
            source_type="manual_adjustment",
            source_id="revenue-1",
            description="正式收入分录",
            lines=[
                JournalLineCreate(account_code="1122", account_name="应收账款", direction="debit", original_amount=Decimal("1000.00"), base_amount=Decimal("1000.00")),
                JournalLineCreate(account_code="6001", account_name="主营业务收入", direction="credit", original_amount=Decimal("1000.00"), base_amount=Decimal("1000.00")),
            ],
        )
    )

    bundle = generate_financial_statements(FinancialStatementGenerateRequest(period="2026-06", account_set_id="default"))

    assert bundle.source == "formal_journal_entries"
    assert bundle.income_statement.total_revenue == Decimal("1000.00")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
python -m pytest tests/test_financial_statement_service.py::test_financial_statements_prefer_formal_journal_entries -q
```

Expected: FAIL because the service still returns `reviewed_vouchers`.

- [ ] **Step 3: Pass ledger source through statement generation**

Modify `backend/app/services/financial_statement_service.py`:

```python
def generate_financial_statements(
    request: FinancialStatementGenerateRequest,
) -> FinancialStatementBundle:
    ledger = build_general_ledger(request.period, request.account_set_id)
    if ledger.accounts:
        source = "formal_journal_entries" if getattr(ledger, "source", "") == "formal_journal_entries" else "reviewed_vouchers"
        return _bundle_from_ledger(request, ledger.voucher_count, ledger.accounts, source)
    return _bundle_from_sample(request)
```

Change `_bundle_from_ledger` signature:

```python
def _bundle_from_ledger(
    request: FinancialStatementGenerateRequest,
    reviewed_voucher_count: int,
    accounts: list[LedgerAccountSummary],
    source: str = "reviewed_vouchers",
) -> FinancialStatementBundle:
```

In `_bundle_from_ledger`, pass `source=source` to `_bundle`.

- [ ] **Step 4: Run statement tests**

Run:

```powershell
cd backend
python -m pytest tests/test_financial_statement_service.py tests/test_financial_statement_api.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/financial_statement_service.py backend/tests/test_financial_statement_service.py
git commit -m "feat: generate statements from formal journal"
```

## Task 7: 前端正式核算来源展示

**Files:**
- Create: `frontend/src/types/accounting.ts`
- Modify: `frontend/src/types/ledger.ts`
- Modify: `frontend/src/types/voucherCenter.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Modify: `frontend/src/components/VoucherCenterPanel.tsx`
- Modify: `frontend/src/components/LedgerPanel.tsx`
- Modify: `frontend/src/components/FinancialStatementPanel.tsx`
- Create: `frontend/tests/accountingApi.test.mjs`
- Modify: `frontend/tests/voucherPostingPanel.test.mjs`
- Modify: `frontend/tests/ledgerPanel.test.mjs`
- Modify: `frontend/tests/financialStatementPanel.test.mjs`

- [ ] **Step 1: Write failing frontend API test**

Create `frontend/tests/accountingApi.test.mjs`:

```javascript
import assert from "node:assert/strict";
import test from "node:test";

import { fetchAccountingAccounts, fetchJournalEntries } from "../src/services/dashboardApi.ts";

test("fetchAccountingAccounts calls accounting account endpoint", async () => {
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    return {
      ok: true,
      json: async () => ({ account_set_id: "default", accounts: [] })
    };
  };

  await fetchAccountingAccounts("default", "http://api.local", fetcher, "u-finance-manager");

  assert.equal(calls[0].url, "http://api.local/api/v1/accounting/accounts?account_set_id=default");
  assert.equal(calls[0].options.headers["X-Actor-Id"], "u-finance-manager");
});

test("fetchJournalEntries passes account set and period", async () => {
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    return {
      ok: true,
      json: async () => ({ account_set_id: "default", period: "2026-06", total: 0, entries: [] })
    };
  };

  await fetchJournalEntries("default", "2026-06", "http://api.local", fetcher, "u-finance-manager");

  assert.equal(calls[0].url, "http://api.local/api/v1/accounting/journal-entries?account_set_id=default&period=2026-06");
});
```

- [ ] **Step 2: Run frontend test to verify it fails**

Run:

```powershell
cd frontend
npm test -- accountingApi
```

Expected: FAIL because `fetchAccountingAccounts` is not exported.

- [ ] **Step 3: Add accounting frontend types**

Create `frontend/src/types/accounting.ts`:

```typescript
import type { MoneyValue } from "./ledger";

export interface AccountItem {
  account_set_id: string;
  account_code: string;
  account_name: string;
  account_type: "asset" | "liability" | "equity" | "revenue" | "cost" | "expense" | string;
  normal_balance: "debit" | "credit" | string;
  is_active: boolean;
}

export interface AccountListResponse {
  account_set_id: string;
  accounts: AccountItem[];
}

export interface JournalLineRecord {
  id: string;
  journal_entry_id: string;
  line_no: number;
  account_code: string;
  account_name: string;
  direction: "debit" | "credit" | string;
  currency: string;
  original_amount: MoneyValue;
  exchange_rate: MoneyValue;
  base_amount: MoneyValue;
  description: string;
}

export interface JournalEntryRecord {
  id: string;
  account_set_id: string;
  period: string;
  entry_date: string;
  entry_number: string;
  source_type: string;
  source_id: string;
  description: string;
  status: "posted" | "reversed" | string;
  base_currency: string;
  posted_by: string;
  posted_at: string;
  reversal_of_entry_id: string | null;
  lines: JournalLineRecord[];
}

export interface JournalEntryListResponse {
  account_set_id: string;
  period: string | null;
  total: number;
  entries: JournalEntryRecord[];
}
```

Modify `frontend/src/types/ledger.ts`:

```typescript
export interface GeneralLedgerResponse {
  source: string;
  period: string;
  voucher_count: number;
  entry_count: number;
  total_debit: MoneyValue;
  total_credit: MoneyValue;
  balanced: boolean;
  accounts: LedgerAccountSummary[];
}
```

Add `source: string;` to `DetailLedgerResponse` and `AccountBalanceTableResponse`.

Modify `frontend/src/types/voucherCenter.ts`:

```typescript
  journal_entry_id: string | null;
  journal_reversal_entry_id: string | null;
```

- [ ] **Step 4: Add dashboard API helpers**

Modify `frontend/src/services/dashboardApi.ts` imports:

```typescript
import type { AccountListResponse, JournalEntryListResponse } from "../types/accounting";
```

Add helpers:

```typescript
export function fetchAccountingAccounts(
  accountSetId = "default",
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<AccountListResponse> {
  return requestLedgerJson<AccountListResponse>(
    `/api/v1/accounting/accounts?account_set_id=${encodeURIComponent(accountSetId)}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchJournalEntries(
  accountSetId = "default",
  period: string | null = null,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<JournalEntryListResponse> {
  const periodQuery = period ? `&period=${encodeURIComponent(period)}` : "";
  return requestLedgerJson<JournalEntryListResponse>(
    `/api/v1/accounting/journal-entries?account_set_id=${encodeURIComponent(accountSetId)}${periodQuery}`,
    apiBase,
    fetcher,
    actorId
  );
}
```

- [ ] **Step 5: Display formal source in panels**

In `VoucherCenterPanel.tsx`, add a compact field in the voucher table row:

```tsx
<td>{voucher.journal_entry_id ? `正式分录 ${voucher.journal_entry_id}` : "未正式过账"}</td>
```

In `LedgerPanel.tsx`, add source label near the section heading:

```tsx
<span className="source-pill">
  {generalLedger?.source === "formal_journal_entries" ? "正式分录" : "MVP凭证工作流"}
</span>
```

In `FinancialStatementPanel.tsx`, update `sourceLabel`:

```typescript
function sourceLabel(source: string) {
  if (source === "formal_journal_entries") {
    return "正式分录";
  }
  return source === "reviewed_vouchers" ? "已审核凭证" : "样例经营数据";
}
```

- [ ] **Step 6: Run frontend tests**

Run:

```powershell
cd frontend
npm test -- accountingApi
npm test -- voucherPostingPanel
npm test -- ledgerPanel
npm test -- financialStatementPanel
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add frontend/src/types/accounting.ts frontend/src/types/ledger.ts frontend/src/types/voucherCenter.ts frontend/src/services/dashboardApi.ts frontend/src/components/VoucherCenterPanel.tsx frontend/src/components/LedgerPanel.tsx frontend/src/components/FinancialStatementPanel.tsx frontend/tests/accountingApi.test.mjs frontend/tests/voucherPostingPanel.test.mjs frontend/tests/ledgerPanel.test.mjs frontend/tests/financialStatementPanel.test.mjs
git commit -m "feat: show formal accounting source in frontend"
```

## Task 8: 文档、全量验证与收尾

**Files:**
- Modify: `README.md`
- Modify: `docs/01-mvp-design.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

- [ ] **Step 1: Update documentation**

Add to `README.md` under the financial center capability list:

```markdown
- 正式会计核算引擎一期：已审核凭证可正式过账为不可变会计分录，账簿和财务报表优先读取正式分录来源，反过账通过冲销分录保留审计轨迹。
```

Add to `docs/01-mvp-design.md`:

```markdown
## 正式会计核算引擎一期边界

- 支持已审核凭证正式过账为 `journal_entry` / `journal_line`。
- 支持正式分录借贷平衡、科目启用和期间状态校验。
- 支持反过账生成冲销分录，不删除原正式分录。
- 支持总账、明细账、科目余额表和财务报表优先读取正式分录。
- 当前不实现完整外币期末重估、辅助核算、损益结转、现金流量表自动拆分或电子会计档案归档。
```

Add to `docs/02-api-design.md`:

````markdown
## 正式会计核算引擎一期

```text
GET /api/v1/accounting/accounts?account_set_id=default
GET /api/v1/accounting/journal-entries?account_set_id=default&period=2026-06
GET /api/v1/accounting/journal-entries/{entry_id}
```

正式过账继续使用：

```text
POST /api/v1/vouchers/center/{voucher_id}/post
POST /api/v1/vouchers/center/{voucher_id}/unpost
```

`post` 会生成正式分录，`unpost` 会生成冲销分录。已关闭期间拒绝正式过账和反过账。
````

Add to `docs/03-frd-v1.0.md` under AI 财务中心:

```markdown
当前正式核算接入状态：

- 已建设正式核算一期底座，凭证中心已审核凭证可生成不可变正式分录。
- 总账、明细账、科目余额表和财务报表优先读取正式分录来源。
- 反过账采用冲销分录，保留来源凭证、操作人、账套、期间和审计日志。
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

- [ ] **Step 4: Run build checks**

Run:

```powershell
cd frontend
npm run build
```

Expected: PASS with Vite build output.

- [ ] **Step 5: Commit docs**

```powershell
git add README.md docs/01-mvp-design.md docs/02-api-design.md docs/03-frd-v1.0.md
git commit -m "docs: document formal accounting phase one"
```

## Self-Review

- Spec coverage: Tasks cover formal journal model, posting, reversal, ledger source, statement source, API, permissions, module registry, frontend source display, tests and docs.
- Placeholder scan: No unresolved placeholders are used in task steps.
- Type consistency: Backend uses `JournalEntryRecord`, `JournalLineRecord`, `AccountListResponse`, `JournalEntryListResponse`; frontend mirrors these names in `frontend/src/types/accounting.ts`.
- Scope check: Full multi-currency revaluation, auxiliary accounting dimensions, period-end closing and electronic archive workflows remain outside this phase and are documented as later phases.
