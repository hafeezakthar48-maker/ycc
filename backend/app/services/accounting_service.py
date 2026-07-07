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
    JournalLineDimensionRecord,
    JournalLineRecord,
    normalize_cash_flow_item_code,
)
from app.services.accounting_period_service import is_accounting_period_closed, validate_account_set


DEFAULT_ACCOUNTING_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "formal_accounting.sqlite3"
ACCOUNTING_DB_PATH_ENV = "FINANCE_AI_ACCOUNTING_DB_PATH"
TWO_PLACES = Decimal("0.01")


_BASE_ACCOUNTS: tuple[AccountItem, ...] = (
    AccountItem(account_set_id="default", account_code="1001", account_name="库存现金", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="1002", account_name="银行存款", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="1012", account_name="其他货币资金", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="1122", account_name="应收账款", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="1123", account_name="预付账款", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="1221", account_name="其他应收款", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="1231", account_name="坏账准备", account_type="asset", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="1405", account_name="库存商品", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="1471", account_name="存货跌价准备", account_type="asset", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="1601", account_name="固定资产", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="1602", account_name="累计折旧", account_type="asset", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="1603", account_name="固定资产减值准备", account_type="asset", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="1606", account_name="固定资产清理", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="1901", account_name="待处理财产损溢", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="2001", account_name="短期借款", account_type="liability", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="2202", account_name="应付账款", account_type="liability", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="2203", account_name="预收账款", account_type="liability", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="2211", account_name="应付职工薪酬", account_type="liability", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="2221", account_name="应交税费", account_type="liability", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="22210101", account_name="应交税费-应交增值税（进项税额）", account_type="liability", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="22210102", account_name="应交税费-应交增值税（销项税额）", account_type="liability", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="22210103", account_name="应交税费-应交增值税（转出未交增值税）", account_type="liability", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="22210104", account_name="应交税费-应交增值税（进项税额转出）", account_type="liability", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="222102", account_name="应交税费-未交增值税", account_type="liability", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="222103", account_name="应交税费-城建税及教育费附加", account_type="liability", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="222104", account_name="应交税费-企业所得税", account_type="liability", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="2241", account_name="其他应付款", account_type="liability", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="4001", account_name="实收资本", account_type="equity", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="4103", account_name="本年利润", account_type="equity", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="4104", account_name="利润分配-未分配利润", account_type="equity", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="6001", account_name="主营业务收入", account_type="revenue", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="6051", account_name="其他业务收入", account_type="revenue", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="6301", account_name="营业外收入", account_type="revenue", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="6401", account_name="主营业务成本", account_type="cost", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="6402", account_name="其他业务成本", account_type="cost", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="6403", account_name="税金及附加", account_type="cost", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="6601", account_name="销售费用", account_type="expense", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="6602", account_name="管理费用", account_type="expense", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="6603", account_name="财务费用", account_type="expense", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="6701", account_name="资产减值损失", account_type="expense", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="6711", account_name="营业外支出", account_type="expense", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="6901", account_name="所得税费用", account_type="expense", normal_balance="debit"),
)

_SUPPORTED_CURRENCIES: tuple[CurrencyItem, ...] = (
    CurrencyItem(currency_code="CNY", currency_name="人民币", decimal_places=2),
    CurrencyItem(currency_code="USD", currency_name="美元", decimal_places=2),
    CurrencyItem(currency_code="EUR", currency_name="欧元", decimal_places=2),
    CurrencyItem(currency_code="HKD", currency_name="港币", decimal_places=2),
)
SUPPORTED_DIMENSION_TYPES = (
    "customer",
    "supplier",
    "employee",
    "department",
    "project",
    "asset",
    "platform",
    "sku",
    "warehouse",
)


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


def list_counterparty_journal_lines(
    account_set_id: str,
    period_to: str,
    account_prefixes: list[str],
    dimension_type: str,
) -> list[dict]:
    validate_account_set(account_set_id)
    rows: list[dict] = []
    for entry in list_journal_entries(account_set_id).entries:
        if entry.status != "posted" or entry.entry_date[:7] > period_to:
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


def list_cash_journal_lines(account_set_id: str, period: str) -> list[dict]:
    validate_account_set(account_set_id)
    rows: list[dict] = []
    for entry in list_journal_entries(account_set_id, period).entries:
        if entry.status != "posted":
            continue
        for line in entry.lines:
            if not line.account_code.startswith(("1001", "1002", "1012")):
                continue
            rows.append(
                {
                    "entry_id": entry.id,
                    "line_id": line.id,
                    "entry_date": entry.entry_date,
                    "period": entry.period,
                    "source_type": entry.source_type,
                    "source_id": entry.source_id,
                    "account_code": line.account_code,
                    "account_name": line.account_name,
                    "direction": line.direction,
                    "cash_direction": "inflow" if line.direction == "debit" else "outflow",
                    "currency": line.currency,
                    "original_amount": line.original_amount,
                    "base_amount": line.base_amount,
                    "summary": line.description or entry.description,
                }
            )
    rows.sort(key=lambda row: (row["entry_date"], row["entry_id"], row["line_id"]))
    return rows


def get_foreign_currency_balances(account_set_id: str, period: str) -> list[dict]:
    validate_account_set(account_set_id)
    account_map = {account.account_code: account for account in get_chart_of_accounts(account_set_id).accounts}
    balances: dict[tuple[str, str, tuple[tuple[str, str, str], ...]], dict] = {}
    for entry in list_journal_entries(account_set_id).entries:
        if entry.status != "posted" or entry.period > period:
            continue
        for line in entry.lines:
            revaluation_currency = None
            if line.currency == entry.base_currency:
                revaluation_currency = _fx_revaluation_currency(entry.source_type, entry.source_id, line.account_code)
            if line.currency == entry.base_currency and revaluation_currency is None:
                continue
            account = account_map.get(line.account_code)
            if account is None or account.account_type not in {"asset", "liability"}:
                continue
            balance_currency = revaluation_currency or line.currency
            dimensions = tuple(
                sorted(
                    (dimension.dimension_type, dimension.dimension_code, dimension.dimension_name)
                    for dimension in line.dimensions
                )
            )
            key = (line.account_code, balance_currency, dimensions)
            row = balances.setdefault(
                key,
                {
                    "account_code": line.account_code,
                    "account_name": line.account_name,
                    "account_type": account.account_type,
                    "normal_balance": account.normal_balance,
                    "currency": balance_currency,
                    "original_balance": Decimal("0.00"),
                    "book_base_balance": Decimal("0.00"),
                    "dimension_values": [
                        {
                            "dimension_type": dimension_type,
                            "dimension_code": dimension_code,
                            "dimension_name": dimension_name,
                        }
                        for dimension_type, dimension_code, dimension_name in dimensions
                    ],
                },
            )
            sign = _balance_sign(account.normal_balance, line.direction)
            if revaluation_currency is None:
                row["original_balance"] += line.original_amount * sign
            row["book_base_balance"] += line.base_amount * sign

    rows = []
    for row in balances.values():
        row["original_balance"] = row["original_balance"].quantize(TWO_PLACES)
        row["book_base_balance"] = row["book_base_balance"].quantize(TWO_PLACES)
        if row["original_balance"] != Decimal("0.00") or row["book_base_balance"] != Decimal("0.00"):
            rows.append(row)
    rows.sort(key=lambda row: (row["account_code"], row["currency"], str(row["dimension_values"])))
    return rows


def get_profit_loss_balances(account_set_id: str, period: str) -> list[dict]:
    validate_account_set(account_set_id)
    profit_loss_codes = {"6001", "6051", "6301", "6401", "6402", "6403", "6601", "6602", "6603", "6701", "6711", "6901"}
    account_map = {account.account_code: account for account in get_chart_of_accounts(account_set_id).accounts}
    balances: dict[str, dict] = {}
    for entry in list_journal_entries(account_set_id, period).entries:
        if entry.status != "posted":
            continue
        for line in entry.lines:
            if line.account_code not in profit_loss_codes:
                continue
            account = account_map[line.account_code]
            row = balances.setdefault(
                line.account_code,
                {
                    "account_code": line.account_code,
                    "account_name": line.account_name,
                    "account_type": account.account_type,
                    "normal_balance": account.normal_balance,
                    "balance": Decimal("0.00"),
                },
            )
            row["balance"] += line.base_amount * _balance_sign(account.normal_balance, line.direction)

    rows = []
    for row in balances.values():
        row["balance"] = row["balance"].quantize(TWO_PLACES)
        if row["balance"] != Decimal("0.00"):
            rows.append(row)
    rows.sort(key=lambda row: row["account_code"])
    return rows


def list_period_journal_lines_for_reporting(account_set_id: str, period: str) -> list[dict]:
    validate_account_set(account_set_id)
    rows: list[dict] = []
    for entry in list_journal_entries(account_set_id, period).entries:
        if entry.status != "posted":
            continue
        for line in entry.lines:
            rows.append(
                {
                    "entry_id": entry.id,
                    "account_code": line.account_code,
                    "account_name": line.account_name,
                    "direction": line.direction,
                    "amount": line.base_amount,
                    "cash_flow_item_code": normalize_cash_flow_item_code(line.cash_flow_item_code),
                }
            )
    return rows


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
        dimensions=line.dimensions,
        cash_flow_item_code=line.cash_flow_item_code,
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


def _balance_sign(normal_balance: str, direction: str) -> Decimal:
    if normal_balance == "debit":
        return Decimal("1") if direction == "debit" else Decimal("-1")
    return Decimal("1") if direction == "credit" else Decimal("-1")


def _fx_revaluation_currency(source_type: str, source_id: str, account_code: str) -> str | None:
    if source_type != "fx_revaluation":
        return None
    parts = source_id.split(":")
    if len(parts) != 6:
        return None
    _prefix, _account_set_id, _period, source_account_code, source_currency, _dimension_hash = parts
    if source_account_code != account_code:
        return None
    return source_currency


def _build_entry(
    connection: sqlite3.Connection,
    request: JournalEntryCreate,
    period: str,
    reversal_of_entry_id: str | None,
) -> JournalEntryRecord:
    entry_id = f"je-{uuid4().hex[:12]}"
    entry_number = _next_entry_number(connection, period)
    posted_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    lines = []
    for index, line in enumerate(request.lines, start=1):
        hydrated_dimensions = _hydrate_line_dimensions(request.account_set_id, line.dimensions)
        lines.append(
            JournalLineRecord(
                id=f"jl-{uuid4().hex[:12]}",
                journal_entry_id=entry_id,
                line_no=index,
                **line.model_dump(exclude={"dimensions"}),
                dimensions=hydrated_dimensions,
            )
        )
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


def _hydrate_line_dimensions(account_set_id: str, dimensions) -> list[JournalLineDimensionRecord]:
    hydrated: list[JournalLineDimensionRecord] = []
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
            JournalLineDimensionRecord(
                dimension_type=record.dimension_type,
                dimension_code=record.dimension_code,
                dimension_name=record.dimension_name,
            )
        )
    return hydrated


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
