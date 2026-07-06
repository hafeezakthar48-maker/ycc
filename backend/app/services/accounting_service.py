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
    AccountItem,
    AccountListResponse,
    AuxiliaryDimensionCreate,
    AuxiliaryDimensionListResponse,
    AuxiliaryDimensionRecord,
    CurrencyItem,
    CurrencyListResponse,
    ExchangeRateCreate,
    ExchangeRateListResponse,
    ExchangeRateRecord,
    JournalEntryCreate,
    JournalEntryListResponse,
    JournalEntryRecord,
    JournalLineCreate,
    JournalLineRecord,
)
from app.services.accounting_period_service import is_accounting_period_closed, validate_account_set


DEFAULT_ACCOUNTING_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "formal_accounting.sqlite3"
ACCOUNTING_DB_PATH_ENV = "FINANCE_AI_ACCOUNTING_DB_PATH"
TWO_PLACES = Decimal("0.01")


_BASE_ACCOUNTS: tuple[AccountItem, ...] = (
    AccountItem(account_set_id="default", account_code="1001", account_name="库存现金", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="1002", account_name="银行存款", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="1122", account_name="应收账款", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="1405", account_name="库存商品", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="1601", account_name="固定资产", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="2001", account_name="短期借款", account_type="liability", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="2202", account_name="应付账款", account_type="liability", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="2221", account_name="应交税费", account_type="liability", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="22210101", account_name="应交税费-应交增值税（进项税额）", account_type="liability", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="22210102", account_name="应交税费-应交增值税（销项税额）", account_type="liability", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="4001", account_name="实收资本", account_type="equity", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="6001", account_name="主营业务收入", account_type="revenue", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="6051", account_name="其他业务收入", account_type="revenue", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="6401", account_name="主营业务成本", account_type="cost", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="6601", account_name="销售费用", account_type="expense", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="6602", account_name="管理费用", account_type="expense", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="6603", account_name="财务费用", account_type="expense", normal_balance="debit"),
)

_SUPPORTED_CURRENCIES: tuple[CurrencyItem, ...] = (
    CurrencyItem(currency_code="CNY", currency_name="人民币", decimal_places=2),
    CurrencyItem(currency_code="USD", currency_name="美元", decimal_places=2),
    CurrencyItem(currency_code="EUR", currency_name="欧元", decimal_places=2),
    CurrencyItem(currency_code="HKD", currency_name="港币", decimal_places=2),
)
SUPPORTED_DIMENSION_TYPES = ("customer", "supplier", "employee", "department", "project", "asset", "platform", "sku")


def reset_accounting_store() -> None:
    with _connection() as connection:
        connection.execute("DELETE FROM journal_entries")
        connection.execute("DELETE FROM journal_sequences")
        connection.execute("DELETE FROM exchange_rates")
        connection.execute("DELETE FROM auxiliary_dimensions")


def get_chart_of_accounts(account_set_id: str = "default") -> AccountListResponse:
    validate_account_set(account_set_id)
    accounts = [account.model_copy(update={"account_set_id": account_set_id}) for account in _BASE_ACCOUNTS]
    return AccountListResponse(account_set_id=account_set_id, accounts=accounts)


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
            INSERT INTO exchange_rates (
                id, account_set_id, rate_date, source_currency, target_currency, payload_json, updated_at
            )
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


def get_exchange_rate(
    account_set_id: str,
    rate_date: str,
    source_currency: str,
    target_currency: str = "CNY",
) -> ExchangeRateRecord:
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


def list_auxiliary_dimensions(
    account_set_id: str = "default",
    dimension_type: str | None = None,
) -> AuxiliaryDimensionListResponse:
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


def post_journal_entry(request: JournalEntryCreate) -> JournalEntryRecord:
    validate_account_set(request.account_set_id)
    period = request.entry_date[:7]
    if is_accounting_period_closed(period, request.account_set_id):
        raise HTTPException(status_code=409, detail="会计期间已关闭，不能正式过账。")
    _validate_accounts(request.account_set_id, request.lines)
    _validate_balance(request.lines)
    _validate_currency_lines(request)

    with _connection() as connection:
        existing = connection.execute(
            """
            SELECT id FROM journal_entries
            WHERE account_set_id = ?
              AND source_type = ?
              AND source_id = ?
              AND status = 'posted'
            """,
            (request.account_set_id, request.source_type, request.source_id),
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
        lines=[_reverse_line(line) for line in original.lines],
    )
    with _connection() as connection:
        reversal = _build_entry(connection, request, original.period, reversal_of_entry_id=original.id)
        _insert_entry(connection, reversal)
        reversed_original = original.model_copy(update={"status": "reversed"})
        connection.execute(
            "UPDATE journal_entries SET status = ?, payload_json = ? WHERE id = ?",
            ("reversed", reversed_original.model_dump_json(), original.id),
        )
    return reversal


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


def _reverse_line(line: JournalLineRecord) -> JournalLineCreate:
    return JournalLineCreate(
        account_code=line.account_code,
        account_name=line.account_name,
        direction="credit" if line.direction == "debit" else "debit",
        currency=line.currency,
        original_amount=line.original_amount,
        exchange_rate=line.exchange_rate,
        base_amount=line.base_amount,
        description=line.description,
    )


def _validate_accounts(account_set_id: str, lines: list[JournalLineCreate]) -> None:
    active_codes = {account.account_code for account in get_chart_of_accounts(account_set_id).accounts if account.is_active}
    for line in lines:
        if line.account_code not in active_codes:
            raise HTTPException(status_code=422, detail=f"科目不存在或未启用：{line.account_code}")


def _validate_currency(currency_code: str) -> None:
    active_codes = {currency.currency_code for currency in _SUPPORTED_CURRENCIES if currency.is_active}
    if currency_code not in active_codes:
        raise HTTPException(status_code=422, detail=f"不支持的币种：{currency_code}")


def _validate_currency_lines(request: JournalEntryCreate) -> None:
    _validate_currency(request.base_currency)
    for line in request.lines:
        _validate_currency(line.currency)
        expected = (line.original_amount * line.exchange_rate).quantize(TWO_PLACES)
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


def _validate_balance(lines: list[JournalLineCreate]) -> None:
    debit_total = sum((line.base_amount for line in lines if line.direction == "debit"), Decimal("0.00"))
    credit_total = sum((line.base_amount for line in lines if line.direction == "credit"), Decimal("0.00"))
    if debit_total != credit_total:
        raise HTTPException(status_code=422, detail="正式分录借贷不平衡。")


def _build_entry(
    connection: sqlite3.Connection,
    request: JournalEntryCreate,
    period: str,
    reversal_of_entry_id: str | None,
) -> JournalEntryRecord:
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
    connection.execute("CREATE INDEX IF NOT EXISTS idx_journal_entries_source ON journal_entries (account_set_id, source_type, source_id)")
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
