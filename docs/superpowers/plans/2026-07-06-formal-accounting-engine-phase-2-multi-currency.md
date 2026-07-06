# Formal Accounting Engine Phase 2 Multi-Currency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在正式核算一期不可变分录基础上，补齐多币种核算、汇率表、外币分录、本位币折算和原币账簿展示。

**Architecture:** 依赖一期的 `accounting` 正式分录内核。新增币种与汇率服务；正式分录行保留交易币种金额、汇率和本位币金额；账簿支持按本位币汇总并展示原币明细；报表仍按账套本位币生成，外币重估和汇兑损益放到期末处理阶段。

**Tech Stack:** FastAPI、Pydantic、SQLite、Decimal、pytest、React、TypeScript、Vite、Node test runner。

---

## Prerequisite

必须先完成并验证：

- `docs/superpowers/plans/2026-07-06-formal-accounting-engine-phase-1.md`
- 后端已有 `backend/app/models/accounting.py`
- 后端已有 `backend/app/services/accounting_service.py`
- 后端已有 `/api/v1/accounting` 路由
- 正式分录行已有 `currency`、`original_amount`、`exchange_rate`、`base_amount`

如果一期尚未完成，先执行一期计划；不要把一期和二期混成一个提交。

## File Structure

- Modify: `backend/app/models/accounting.py`
  - 增加币种、汇率、外币账簿响应模型。
- Modify: `backend/app/services/accounting_service.py`
  - 增加币种清单、汇率表、汇率查询、外币分录校验和原币账簿聚合。
- Modify: `backend/app/api/accounting.py`
  - 增加币种、汇率和正式分录创建接口。
- Modify: `backend/app/services/system_admin_service.py`
  - 增加汇率维护和外币分录权限。
- Modify: `backend/app/services/module_registry_service.py`
  - 登记多币种 API 和审计事件。
- Modify: `backend/app/models/ledger.py`
  - 增加外币金额、币种和汇率字段，用于明细账展示。
- Modify: `backend/app/services/ledger_service.py`
  - 明细账展示原币金额和本位币金额；总账继续按本位币汇总。
- Modify: `backend/app/models/financial_statement.py`
  - 在报表摘要里显示账套本位币和外币分录数量。
- Modify: `backend/app/services/financial_statement_service.py`
  - 继续按本位币报表取数，并把外币折算摘要写入管理摘要。
- Create: `backend/tests/test_multi_currency_accounting_service.py`
- Create: `backend/tests/test_multi_currency_accounting_api.py`
- Modify: `backend/tests/test_ledger_service.py`
- Modify: `backend/tests/test_financial_statement_service.py`
- Modify: `frontend/src/types/accounting.ts`
- Modify: `frontend/src/types/ledger.ts`
- Modify: `frontend/src/types/financialStatement.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Modify: `frontend/src/components/LedgerPanel.tsx`
- Modify: `frontend/src/components/FinancialStatementPanel.tsx`
- Create: `frontend/tests/multiCurrencyAccountingApi.test.mjs`
- Modify: `frontend/tests/ledgerPanel.test.mjs`
- Modify: `frontend/tests/financialStatementPanel.test.mjs`
- Modify: `README.md`, `docs/01-mvp-design.md`, `docs/02-api-design.md`, `docs/03-frd-v1.0.md`

## Task 1: 币种与汇率领域模型

**Files:**
- Modify: `backend/app/models/accounting.py`
- Modify: `backend/app/services/accounting_service.py`
- Create: `backend/tests/test_multi_currency_accounting_service.py`

- [ ] **Step 1: Write failing currency and exchange-rate tests**

Create `backend/tests/test_multi_currency_accounting_service.py`:

```python
from decimal import Decimal

from app.models.accounting import ExchangeRateCreate
from app.services.accounting_service import (
    get_exchange_rate,
    list_currencies,
    reset_accounting_store,
    upsert_exchange_rate,
)


def setup_function():
    reset_accounting_store()


def test_list_currencies_contains_supported_mvp_currencies():
    currencies = list_currencies().currencies

    codes = {currency.currency_code for currency in currencies}
    assert {"CNY", "USD", "EUR", "HKD"}.issubset(codes)
    cny = next(currency for currency in currencies if currency.currency_code == "CNY")
    assert cny.currency_name == "人民币"
    assert cny.decimal_places == 2


def test_upsert_and_get_exchange_rate():
    created = upsert_exchange_rate(
        ExchangeRateCreate(
            account_set_id="default",
            rate_date="2026-06-18",
            source_currency="USD",
            target_currency="CNY",
            rate=Decimal("7.120000"),
            source="manual",
        )
    )

    loaded = get_exchange_rate("default", "2026-06-18", "USD", "CNY")

    assert created.rate == Decimal("7.120000")
    assert loaded.rate == Decimal("7.120000")
    assert loaded.source == "manual"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
python -m pytest tests/test_multi_currency_accounting_service.py -q
```

Expected: FAIL with missing `ExchangeRateCreate` or missing service functions.

- [ ] **Step 3: Add currency and exchange-rate models**

Modify `backend/app/models/accounting.py`:

```python
class CurrencyItem(BaseModel):
    currency_code: str = Field(min_length=3, max_length=3)
    currency_name: str
    decimal_places: int = Field(ge=0, le=6)
    is_active: bool = True


class CurrencyListResponse(BaseModel):
    currencies: list[CurrencyItem]


class ExchangeRateCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    rate_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    source_currency: str = Field(min_length=3, max_length=3)
    target_currency: str = Field(default="CNY", min_length=3, max_length=3)
    rate: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    source: str = Field(default="manual", min_length=1, max_length=40)


class ExchangeRateRecord(ExchangeRateCreate):
    id: str
    updated_at: str


class ExchangeRateListResponse(BaseModel):
    account_set_id: str
    rates: list[ExchangeRateRecord]
```

- [ ] **Step 4: Implement currency and exchange-rate service**

Modify `backend/app/services/accounting_service.py` imports:

```python
from app.models.accounting import (
    CurrencyItem,
    CurrencyListResponse,
    ExchangeRateCreate,
    ExchangeRateListResponse,
    ExchangeRateRecord,
)
```

Add constants:

```python
_SUPPORTED_CURRENCIES: tuple[CurrencyItem, ...] = (
    CurrencyItem(currency_code="CNY", currency_name="人民币", decimal_places=2),
    CurrencyItem(currency_code="USD", currency_name="美元", decimal_places=2),
    CurrencyItem(currency_code="EUR", currency_name="欧元", decimal_places=2),
    CurrencyItem(currency_code="HKD", currency_name="港币", decimal_places=2),
)
```

Add service functions:

```python
def list_currencies() -> CurrencyListResponse:
    return CurrencyListResponse(currencies=list(_SUPPORTED_CURRENCIES))


def upsert_exchange_rate(request: ExchangeRateCreate) -> ExchangeRateRecord:
    validate_account_set(request.account_set_id)
    _validate_currency(request.source_currency)
    _validate_currency(request.target_currency)
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    rate_id = f"{request.account_set_id}:{request.rate_date}:{request.source_currency}:{request.target_currency}"
    record = ExchangeRateRecord(id=rate_id, updated_at=now, **request.model_dump())
    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO exchange_rates (id, account_set_id, rate_date, source_currency, target_currency, payload_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                payload_json = excluded.payload_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                record.id,
                record.account_set_id,
                record.rate_date,
                record.source_currency,
                record.target_currency,
                record.model_dump_json(),
            ),
        )
    return record


def get_exchange_rate(account_set_id: str, rate_date: str, source_currency: str, target_currency: str = "CNY") -> ExchangeRateRecord:
    validate_account_set(account_set_id)
    _validate_currency(source_currency)
    _validate_currency(target_currency)
    if source_currency == target_currency:
        return ExchangeRateRecord(
            id=f"{account_set_id}:{rate_date}:{source_currency}:{target_currency}",
            account_set_id=account_set_id,
            rate_date=rate_date,
            source_currency=source_currency,
            target_currency=target_currency,
            rate=Decimal("1.000000"),
            source="identity",
            updated_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        )
    rate_id = f"{account_set_id}:{rate_date}:{source_currency}:{target_currency}"
    with _connection() as connection:
        row = connection.execute("SELECT payload_json FROM exchange_rates WHERE id = ?", (rate_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"缺少汇率：{source_currency}->{target_currency} {rate_date}")
    return ExchangeRateRecord.model_validate_json(row["payload_json"])
```

Add helpers and schema:

```python
def list_exchange_rates(account_set_id: str = "default") -> ExchangeRateListResponse:
    validate_account_set(account_set_id)
    with _connection() as connection:
        rows = connection.execute(
            "SELECT payload_json FROM exchange_rates WHERE account_set_id = ? ORDER BY rate_date DESC, source_currency",
            (account_set_id,),
        ).fetchall()
    return ExchangeRateListResponse(
        account_set_id=account_set_id,
        rates=[ExchangeRateRecord.model_validate_json(row["payload_json"]) for row in rows],
    )


def _validate_currency(currency_code: str) -> None:
    active_codes = {currency.currency_code for currency in _SUPPORTED_CURRENCIES if currency.is_active}
    if currency_code not in active_codes:
        raise HTTPException(status_code=422, detail=f"不支持的币种：{currency_code}")
```

Update `_ensure_schema`:

```python
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS exchange_rates (
            id TEXT PRIMARY KEY,
            account_set_id TEXT NOT NULL,
            rate_date TEXT NOT NULL,
            source_currency TEXT NOT NULL,
            target_currency TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_exchange_rates_account_set ON exchange_rates (account_set_id, rate_date)"
    )
```

Update `reset_accounting_store` to clear exchange rates:

```python
connection.execute("DELETE FROM exchange_rates")
```

- [ ] **Step 5: Run service tests**

Run:

```powershell
cd backend
python -m pytest tests/test_multi_currency_accounting_service.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/models/accounting.py backend/app/services/accounting_service.py backend/tests/test_multi_currency_accounting_service.py
git commit -m "feat: add currencies and exchange rates"
```

## Task 2: 外币正式分录创建与折算校验

**Files:**
- Modify: `backend/app/models/accounting.py`
- Modify: `backend/app/services/accounting_service.py`
- Modify: `backend/tests/test_multi_currency_accounting_service.py`

- [ ] **Step 1: Write failing multi-currency journal tests**

Append to `backend/tests/test_multi_currency_accounting_service.py`:

```python
from app.models.accounting import JournalEntryCreate, JournalLineCreate
from app.services.accounting_service import get_journal_entry, post_journal_entry


def test_post_foreign_currency_entry_keeps_original_and_base_amounts():
    upsert_exchange_rate(
        ExchangeRateCreate(
            account_set_id="default",
            rate_date="2026-06-18",
            source_currency="USD",
            target_currency="CNY",
            rate=Decimal("7.120000"),
        )
    )

    entry = post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-18",
            source_type="manual_adjustment",
            source_id="fx-sale-1",
            description="美元销售收入",
            base_currency="CNY",
            lines=[
                JournalLineCreate(
                    account_code="1122",
                    account_name="应收账款",
                    direction="debit",
                    currency="USD",
                    original_amount=Decimal("100.00"),
                    exchange_rate=Decimal("7.120000"),
                    base_amount=Decimal("712.00"),
                    description="美元应收",
                ),
                JournalLineCreate(
                    account_code="6001",
                    account_name="主营业务收入",
                    direction="credit",
                    currency="USD",
                    original_amount=Decimal("100.00"),
                    exchange_rate=Decimal("7.120000"),
                    base_amount=Decimal("712.00"),
                    description="美元收入",
                ),
            ],
        )
    )

    loaded = get_journal_entry(entry.id)
    assert loaded.lines[0].currency == "USD"
    assert loaded.lines[0].original_amount == Decimal("100.00")
    assert loaded.lines[0].base_amount == Decimal("712.00")


def test_post_foreign_currency_entry_rejects_wrong_base_amount():
    upsert_exchange_rate(
        ExchangeRateCreate(
            account_set_id="default",
            rate_date="2026-06-18",
            source_currency="USD",
            target_currency="CNY",
            rate=Decimal("7.120000"),
        )
    )

    request = JournalEntryCreate(
        account_set_id="default",
        entry_date="2026-06-18",
        source_type="manual_adjustment",
        source_id="fx-wrong-base",
        description="错误折算",
        base_currency="CNY",
        lines=[
            JournalLineCreate(account_code="1122", account_name="应收账款", direction="debit", currency="USD", original_amount=Decimal("100.00"), exchange_rate=Decimal("7.120000"), base_amount=Decimal("711.99")),
            JournalLineCreate(account_code="6001", account_name="主营业务收入", direction="credit", currency="USD", original_amount=Decimal("100.00"), exchange_rate=Decimal("7.120000"), base_amount=Decimal("711.99")),
        ],
    )

    with pytest.raises(HTTPException) as exc_info:
        post_journal_entry(request)

    assert exc_info.value.status_code == 422
    assert "折算金额" in exc_info.value.detail
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
cd backend
python -m pytest tests/test_multi_currency_accounting_service.py -q
```

Expected: FAIL because foreign currency conversion validation is not implemented.

- [ ] **Step 3: Add conversion validation**

Modify `backend/app/services/accounting_service.py` inside `post_journal_entry` before `_validate_balance`:

```python
    _validate_currency_lines(request)
```

Add helper:

```python
TWOPLACES = Decimal("0.01")


def _validate_currency_lines(request: JournalEntryCreate) -> None:
    for line in request.lines:
        _validate_currency(line.currency)
        expected = (line.original_amount * line.exchange_rate).quantize(TWOPLACES)
        if line.base_amount != expected:
            raise HTTPException(
                status_code=422,
                detail=f"折算金额不匹配：{line.account_code} {line.original_amount} {line.currency} * {line.exchange_rate} 应为 {expected}",
            )
        if line.currency != request.base_currency:
            rate = get_exchange_rate(request.account_set_id, request.entry_date, line.currency, request.base_currency)
            if line.exchange_rate != rate.rate:
                raise HTTPException(
                    status_code=422,
                    detail=f"汇率不匹配：{line.currency}->{request.base_currency} {request.entry_date} 应为 {rate.rate}",
                )
```

In `reverse_journal_entry`, keep original currency fields unchanged and only reverse direction. This preserves original currency evidence on reversal lines.

- [ ] **Step 4: Run service tests**

Run:

```powershell
cd backend
python -m pytest tests/test_multi_currency_accounting_service.py tests/test_accounting_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/models/accounting.py backend/app/services/accounting_service.py backend/tests/test_multi_currency_accounting_service.py
git commit -m "feat: validate foreign currency journal lines"
```

## Task 3: 多币种 Accounting API 与权限

**Files:**
- Modify: `backend/app/api/accounting.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Create: `backend/tests/test_multi_currency_accounting_api.py`

- [ ] **Step 1: Write failing API tests**

Create `backend/tests/test_multi_currency_accounting_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import app
from app.services.accounting_service import reset_accounting_store


client = TestClient(app)


def setup_function():
    reset_accounting_store()


def test_finance_manager_can_create_exchange_rate():
    response = client.post(
        "/api/v1/accounting/exchange-rates",
        json={
            "account_set_id": "default",
            "rate_date": "2026-06-18",
            "source_currency": "USD",
            "target_currency": "CNY",
            "rate": "7.120000",
            "source": "manual",
        },
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert response.status_code == 200
    assert response.json()["rate"] == "7.120000"


def test_finance_manager_can_create_foreign_currency_journal_entry():
    client.post(
        "/api/v1/accounting/exchange-rates",
        json={"account_set_id": "default", "rate_date": "2026-06-18", "source_currency": "USD", "target_currency": "CNY", "rate": "7.120000"},
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    response = client.post(
        "/api/v1/accounting/journal-entries",
        json={
            "account_set_id": "default",
            "entry_date": "2026-06-18",
            "source_type": "manual_adjustment",
            "source_id": "fx-api-1",
            "description": "美元收入",
            "base_currency": "CNY",
            "created_by": "财务主管",
            "posted_by": "财务主管",
            "lines": [
                {"account_code": "1122", "account_name": "应收账款", "direction": "debit", "currency": "USD", "original_amount": "100.00", "exchange_rate": "7.120000", "base_amount": "712.00", "description": "美元应收"},
                {"account_code": "6001", "account_name": "主营业务收入", "direction": "credit", "currency": "USD", "original_amount": "100.00", "exchange_rate": "7.120000", "base_amount": "712.00", "description": "美元收入"},
            ],
        },
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert response.status_code == 200
    assert response.json()["lines"][0]["currency"] == "USD"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
cd backend
python -m pytest tests/test_multi_currency_accounting_api.py -q
```

Expected: FAIL with 404 for new endpoints.

- [ ] **Step 3: Add API endpoints**

Modify `backend/app/api/accounting.py` imports:

```python
from app.models.accounting import ExchangeRateCreate, JournalEntryCreate
from app.services.accounting_service import (
    list_currencies,
    list_exchange_rates,
    post_journal_entry,
    upsert_exchange_rate,
)
```

Add endpoints:

```python
@router.get("/currencies")
def get_currencies(x_actor_id: str = Header(default="system")):
    _require_accounting_permission(x_actor_id, "accounting.account.read", "accounting.currency.read", "currencies", {})
    response = list_currencies()
    _record_accounting_audit(x_actor_id, "accounting.currency.read", "currencies", {"currency_count": len(response.currencies)})
    return response


@router.get("/exchange-rates")
def get_exchange_rates(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    x_actor_id: str = Header(default="system"),
):
    _require_accounting_permission(x_actor_id, "accounting.exchange_rate.read", "accounting.exchange_rate.read", f"exchange-rates:{account_set_id}", {"account_set_id": account_set_id})
    response = list_exchange_rates(account_set_id)
    _record_accounting_audit(x_actor_id, "accounting.exchange_rate.read", f"exchange-rates:{account_set_id}", {"account_set_id": account_set_id, "rate_count": len(response.rates)})
    return response


@router.post("/exchange-rates")
def create_exchange_rate(request: ExchangeRateCreate, x_actor_id: str = Header(default="system")):
    _require_accounting_permission(x_actor_id, "accounting.exchange_rate.write", "accounting.exchange_rate.write", f"exchange-rate:{request.account_set_id}:{request.rate_date}:{request.source_currency}", {"account_set_id": request.account_set_id, "rate_date": request.rate_date, "source_currency": request.source_currency})
    response = upsert_exchange_rate(request)
    _record_accounting_audit(x_actor_id, "accounting.exchange_rate.write", response.id, {"account_set_id": response.account_set_id, "rate_date": response.rate_date, "source_currency": response.source_currency, "target_currency": response.target_currency})
    return response


@router.post("/journal-entries")
def create_journal_entry(request: JournalEntryCreate, x_actor_id: str = Header(default="system")):
    _require_accounting_permission(x_actor_id, "accounting.entry.post", "accounting.entry.post", f"journal-entry-source:{request.source_type}:{request.source_id}", {"account_set_id": request.account_set_id, "source_type": request.source_type, "source_id": request.source_id})
    entry = post_journal_entry(request)
    _record_accounting_audit(x_actor_id, "accounting.entry.post", entry.id, {"account_set_id": entry.account_set_id, "period": entry.period, "entry_number": entry.entry_number})
    return entry
```

- [ ] **Step 4: Add permissions and module registry entries**

Modify `backend/app/services/system_admin_service.py` finance manager permissions:

```python
"accounting.currency.read",
"accounting.exchange_rate.read",
"accounting.exchange_rate.write",
```

Modify `backend/app/services/module_registry_service.py` audit events:

```python
"accounting.currency.read",
"accounting.exchange_rate.read",
"accounting.exchange_rate.write",
```

- [ ] **Step 5: Run API tests**

Run:

```powershell
cd backend
python -m pytest tests/test_multi_currency_accounting_api.py tests/test_accounting_api.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/api/accounting.py backend/app/services/system_admin_service.py backend/app/services/module_registry_service.py backend/tests/test_multi_currency_accounting_api.py
git commit -m "feat: expose multi currency accounting api"
```

## Task 4: 原币账簿与本位币汇总

**Files:**
- Modify: `backend/app/models/ledger.py`
- Modify: `backend/app/services/ledger_service.py`
- Modify: `backend/tests/test_ledger_service.py`

- [ ] **Step 1: Write failing ledger tests**

Append to `backend/tests/test_ledger_service.py`:

```python
def test_detail_ledger_shows_original_currency_and_base_amount():
    reset_accounting_store()
    upsert_exchange_rate(ExchangeRateCreate(account_set_id="default", rate_date="2026-06-18", source_currency="USD", target_currency="CNY", rate=Decimal("7.120000")))
    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-18",
            source_type="manual_adjustment",
            source_id="fx-ledger-1",
            description="美元收入",
            lines=[
                JournalLineCreate(account_code="1122", account_name="应收账款", direction="debit", currency="USD", original_amount=Decimal("100.00"), exchange_rate=Decimal("7.120000"), base_amount=Decimal("712.00")),
                JournalLineCreate(account_code="6001", account_name="主营业务收入", direction="credit", currency="USD", original_amount=Decimal("100.00"), exchange_rate=Decimal("7.120000"), base_amount=Decimal("712.00")),
            ],
        )
    )

    detail = build_detail_ledger("2026-06", "1122", "default")

    assert detail.source == "formal_journal_entries"
    assert detail.lines[0].currency == "USD"
    assert detail.lines[0].original_amount == Decimal("100.00")
    assert detail.lines[0].exchange_rate == Decimal("7.120000")
    assert detail.lines[0].debit_amount == Decimal("712.00")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
python -m pytest tests/test_ledger_service.py::test_detail_ledger_shows_original_currency_and_base_amount -q
```

Expected: FAIL because ledger detail lines do not expose currency fields.

- [ ] **Step 3: Add currency fields to ledger models**

Modify `backend/app/models/ledger.py` `LedgerDetailLine`:

```python
class LedgerDetailLine(BaseModel):
    voucher_id: str
    voucher_number: str
    voucher_date: str
    summary: str
    counterparty: str
    account_code: str
    account_name: str
    direction: str
    explanation: str
    currency: str = "CNY"
    original_amount: Decimal = Decimal("0.00")
    exchange_rate: Decimal = Decimal("1.000000")
    debit_amount: Decimal
    credit_amount: Decimal
    status: str
```

- [ ] **Step 4: Map formal journal lines into ledger detail currency fields**

Modify the formal journal branch in `backend/app/services/ledger_service.py`:

```python
LedgerDetailLine(
    voucher_id=entry.source_id,
    voucher_number=entry.entry_number,
    voucher_date=entry.entry_date,
    summary=entry.description,
    counterparty=entry.source_type,
    account_code=line.account_code,
    account_name=line.account_name,
    direction="借" if line.direction == "debit" else "贷",
    explanation=line.description,
    currency=line.currency,
    original_amount=line.original_amount,
    exchange_rate=line.exchange_rate,
    debit_amount=line.base_amount if line.direction == "debit" else ZERO,
    credit_amount=line.base_amount if line.direction == "credit" else ZERO,
    status=entry.status,
)
```

Keep total debit and credit in base currency.

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
git commit -m "feat: show original currency in ledgers"
```

## Task 5: 报表本位币摘要与外币分录提示

**Files:**
- Modify: `backend/app/models/financial_statement.py`
- Modify: `backend/app/services/financial_statement_service.py`
- Modify: `backend/tests/test_financial_statement_service.py`

- [ ] **Step 1: Write failing statement tests**

Append to `backend/tests/test_financial_statement_service.py`:

```python
def test_financial_statement_summary_reports_base_currency_and_foreign_line_count():
    reset_accounting_store()
    upsert_exchange_rate(ExchangeRateCreate(account_set_id="default", rate_date="2026-06-18", source_currency="USD", target_currency="CNY", rate=Decimal("7.120000")))
    post_journal_entry(
        JournalEntryCreate(
            account_set_id="default",
            entry_date="2026-06-18",
            source_type="manual_adjustment",
            source_id="fx-statement-1",
            description="美元收入",
            lines=[
                JournalLineCreate(account_code="1122", account_name="应收账款", direction="debit", currency="USD", original_amount=Decimal("100.00"), exchange_rate=Decimal("7.120000"), base_amount=Decimal("712.00")),
                JournalLineCreate(account_code="6001", account_name="主营业务收入", direction="credit", currency="USD", original_amount=Decimal("100.00"), exchange_rate=Decimal("7.120000"), base_amount=Decimal("712.00")),
            ],
        )
    )

    bundle = generate_financial_statements(FinancialStatementGenerateRequest(period="2026-06", account_set_id="default"))

    assert bundle.summary.base_currency == "CNY"
    assert bundle.summary.foreign_currency_line_count == 2
    assert any("外币分录 2 行" in item for item in bundle.management_summary.highlights)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
python -m pytest tests/test_financial_statement_service.py::test_financial_statement_summary_reports_base_currency_and_foreign_line_count -q
```

Expected: FAIL because summary has no currency fields.

- [ ] **Step 3: Extend financial statement summary model**

Modify `backend/app/models/financial_statement.py`:

```python
class FinancialStatementGenerationSummary(BaseModel):
    account_set_id: str
    period: str
    source: str
    reviewed_voucher_count: int
    asset_liability_balanced: bool
    generated_statement_count: int
    base_currency: str = "CNY"
    foreign_currency_line_count: int = 0
```

- [ ] **Step 4: Count foreign currency journal lines in statement service**

Modify `backend/app/services/financial_statement_service.py`:

```python
from app.services.accounting_service import list_journal_entries
```

Add helper:

```python
def _foreign_currency_line_count(account_set_id: str, period: str, base_currency: str = "CNY") -> int:
    entries = list_journal_entries(account_set_id, period).entries
    return sum(1 for entry in entries for line in entry.lines if line.currency != base_currency)
```

In `_bundle`, compute and set:

```python
foreign_currency_line_count = _foreign_currency_line_count(request.account_set_id, request.period)
```

Pass fields into `FinancialStatementGenerationSummary`:

```python
base_currency="CNY",
foreign_currency_line_count=foreign_currency_line_count,
```

Append management highlight when count is greater than zero:

```python
if foreign_currency_line_count:
    management_summary.highlights.append(f"本期包含外币分录 {foreign_currency_line_count} 行，报表金额按账套本位币 CNY 展示。")
```

- [ ] **Step 5: Run statement tests**

Run:

```powershell
cd backend
python -m pytest tests/test_financial_statement_service.py tests/test_financial_statement_api.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/models/financial_statement.py backend/app/services/financial_statement_service.py backend/tests/test_financial_statement_service.py
git commit -m "feat: summarize multi currency statements"
```

## Task 6: 前端多币种展示与 API helper

**Files:**
- Modify: `frontend/src/types/accounting.ts`
- Modify: `frontend/src/types/ledger.ts`
- Modify: `frontend/src/types/financialStatement.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Modify: `frontend/src/components/LedgerPanel.tsx`
- Modify: `frontend/src/components/FinancialStatementPanel.tsx`
- Create: `frontend/tests/multiCurrencyAccountingApi.test.mjs`
- Modify: `frontend/tests/ledgerPanel.test.mjs`
- Modify: `frontend/tests/financialStatementPanel.test.mjs`

- [ ] **Step 1: Write failing frontend API test**

Create `frontend/tests/multiCurrencyAccountingApi.test.mjs`:

```javascript
import assert from "node:assert/strict";
import test from "node:test";

import { fetchCurrencies, fetchExchangeRates, saveExchangeRate } from "../src/services/dashboardApi.ts";

test("fetchCurrencies calls accounting currencies endpoint", async () => {
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    return { ok: true, json: async () => ({ currencies: [] }) };
  };

  await fetchCurrencies("http://api.local", fetcher, "u-finance-manager");

  assert.equal(calls[0].url, "http://api.local/api/v1/accounting/currencies");
  assert.equal(calls[0].options.headers["X-Actor-Id"], "u-finance-manager");
});

test("saveExchangeRate posts exchange rate payload", async () => {
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    return { ok: true, json: async () => ({ id: "default:2026-06-18:USD:CNY", rate: "7.120000" }) };
  };

  await saveExchangeRate(
    { account_set_id: "default", rate_date: "2026-06-18", source_currency: "USD", target_currency: "CNY", rate: "7.120000", source: "manual" },
    "http://api.local",
    fetcher,
    "u-finance-manager"
  );

  assert.equal(calls[0].url, "http://api.local/api/v1/accounting/exchange-rates");
  assert.equal(JSON.parse(calls[0].options.body).source_currency, "USD");
});
```

- [ ] **Step 2: Run frontend test to verify it fails**

Run:

```powershell
cd frontend
npm test -- multiCurrencyAccountingApi
```

Expected: FAIL because helpers are not exported.

- [ ] **Step 3: Add frontend accounting types**

Modify `frontend/src/types/accounting.ts`:

```typescript
export interface CurrencyItem {
  currency_code: string;
  currency_name: string;
  decimal_places: number;
  is_active: boolean;
}

export interface CurrencyListResponse {
  currencies: CurrencyItem[];
}

export interface ExchangeRateRecord {
  id: string;
  account_set_id: string;
  rate_date: string;
  source_currency: string;
  target_currency: string;
  rate: MoneyValue;
  source: string;
  updated_at: string;
}

export interface ExchangeRateCreateRequest {
  account_set_id: string;
  rate_date: string;
  source_currency: string;
  target_currency: string;
  rate: MoneyValue;
  source?: string;
}

export interface ExchangeRateListResponse {
  account_set_id: string;
  rates: ExchangeRateRecord[];
}
```

Modify `frontend/src/types/ledger.ts` `LedgerDetailLine`:

```typescript
  currency: string;
  original_amount: MoneyValue;
  exchange_rate: MoneyValue;
```

Modify `frontend/src/types/financialStatement.ts` `FinancialStatementGenerationSummary`:

```typescript
  base_currency: string;
  foreign_currency_line_count: number;
```

- [ ] **Step 4: Add dashboard API helpers**

Modify `frontend/src/services/dashboardApi.ts` imports:

```typescript
import type {
  CurrencyListResponse,
  ExchangeRateCreateRequest,
  ExchangeRateListResponse,
  ExchangeRateRecord
} from "../types/accounting";
```

Add:

```typescript
export function fetchCurrencies(
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<CurrencyListResponse> {
  return requestLedgerJson<CurrencyListResponse>("/api/v1/accounting/currencies", apiBase, fetcher, actorId);
}

export function fetchExchangeRates(
  accountSetId = "default",
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<ExchangeRateListResponse> {
  return requestLedgerJson<ExchangeRateListResponse>(
    `/api/v1/accounting/exchange-rates?account_set_id=${encodeURIComponent(accountSetId)}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function saveExchangeRate(
  request: ExchangeRateCreateRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<ExchangeRateRecord> {
  return mutateLedgerJson<ExchangeRateRecord>("/api/v1/accounting/exchange-rates", request, apiBase, fetcher, actorId);
}
```

- [ ] **Step 5: Show original currency in frontend panels**

In `LedgerPanel.tsx`, show detail line amount as base amount plus original currency:

```tsx
<td>
  {money(line.debit_amount)}
  {line.currency !== "CNY" ? <small>{money(line.original_amount)} {line.currency} @ {line.exchange_rate}</small> : null}
</td>
```

Use the same treatment for credit amount.

In `FinancialStatementPanel.tsx`, show summary base currency:

```tsx
<article>
  <span>本位币</span>
  <strong>{bundle?.summary.base_currency ?? "CNY"}</strong>
</article>
<article>
  <span>外币分录</span>
  <strong>{bundle?.summary.foreign_currency_line_count ?? 0}</strong>
</article>
```

- [ ] **Step 6: Run frontend tests**

Run:

```powershell
cd frontend
npm test -- multiCurrencyAccountingApi
npm test -- ledgerPanel
npm test -- financialStatementPanel
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add frontend/src/types/accounting.ts frontend/src/types/ledger.ts frontend/src/types/financialStatement.ts frontend/src/services/dashboardApi.ts frontend/src/components/LedgerPanel.tsx frontend/src/components/FinancialStatementPanel.tsx frontend/tests/multiCurrencyAccountingApi.test.mjs frontend/tests/ledgerPanel.test.mjs frontend/tests/financialStatementPanel.test.mjs
git commit -m "feat: show multi currency accounting in frontend"
```

## Task 7: 文档、验证与边界说明

**Files:**
- Modify: `README.md`
- Modify: `docs/01-mvp-design.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

- [ ] **Step 1: Update documentation**

Add to `README.md`:

```markdown
- 多币种核算二期：支持币种清单、手工维护汇率、外币正式分录、本位币折算、原币明细账展示和本位币财务报表摘要。
```

Add to `docs/01-mvp-design.md`:

```markdown
## 多币种核算二期边界

- 支持 `CNY`、`USD`、`EUR`、`HKD` 币种清单。
- 支持按账套和日期维护外币兑本位币汇率。
- 支持正式分录行保存交易币种金额、汇率和本位币金额。
- 支持总账按本位币汇总，明细账展示原币金额、汇率和本位币金额。
- 财务报表仍按账套本位币生成。
- 当前不自动执行期末外币重估、汇兑损益结转或多本位币合并报表。
```

Add to `docs/02-api-design.md`:

````markdown
## 多币种核算二期

```text
GET /api/v1/accounting/currencies
GET /api/v1/accounting/exchange-rates?account_set_id=default
POST /api/v1/accounting/exchange-rates
POST /api/v1/accounting/journal-entries
```

外币分录行必须同时提交 `currency`、`original_amount`、`exchange_rate` 和 `base_amount`，后端会校验 `original_amount * exchange_rate == base_amount`。
````

Add to `docs/03-frd-v1.0.md`:

```markdown
当前多币种接入状态：

- 已支持外币正式分录和汇率表。
- 已支持原币明细账展示和本位币总账汇总。
- 已支持财务报表按账套本位币生成，并提示外币分录数量。
- 期末外币重估、汇兑损益和多币种合并报表放入后续期末处理阶段。
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
git commit -m "docs: document multi currency accounting phase two"
```

## Self-Review

- Spec coverage: Covers currencies, exchange rates, foreign-currency formal entries, conversion validation, original-currency ledger display, base-currency financial statements, API, permissions, frontend display and docs.
- Placeholder scan: No unresolved placeholder text is used.
- Type consistency: Backend `CurrencyItem`, `ExchangeRateCreate`, `ExchangeRateRecord`, `ExchangeRateListResponse` map to frontend `CurrencyItem`, `ExchangeRateCreateRequest`, `ExchangeRateRecord`, `ExchangeRateListResponse`.
- Scope check: Period-end revaluation, exchange gain or loss posting, auxiliary accounting dimensions and consolidated reporting are intentionally left for later accounting phases.
