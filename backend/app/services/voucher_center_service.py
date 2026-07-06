import csv
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from fastapi import HTTPException

from app.models.audit import AuditRequest, AuditVoucherLine
from app.models.voucher_center import (
    VoucherAttachment,
    VoucherCenterCreateRequest,
    VoucherCenterImportRequest,
    VoucherCenterImportResponse,
    VoucherCenterListResponse,
    VoucherCenterRecord,
)
from app.services.audit_service import review_audit_subject


DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "voucher_center.sqlite3"
DB_PATH_ENV = "FINANCE_AI_VOUCHER_DB_PATH"


def reset_voucher_store() -> None:
    with _connection() as connection:
        connection.execute("DELETE FROM voucher_center_records")
        connection.execute("DELETE FROM voucher_center_sequences")


def create_voucher(request: VoucherCenterCreateRequest) -> VoucherCenterRecord:
    from app.services.accounting_period_service import validate_account_set

    validate_account_set(request.account_set_id)
    with _connection() as connection:
        voucher = VoucherCenterRecord(
            id=f"voucher-{uuid4().hex[:12]}",
            account_set_id=request.account_set_id,
            voucher_number=_next_voucher_number(connection, request.voucher_date),
            voucher_date=request.voucher_date,
            summary=request.summary,
            counterparty=request.counterparty,
            invoice_number=request.invoice_number,
            amount=request.amount,
            tax_amount=request.tax_amount,
            total_amount_with_tax=request.total_amount_with_tax,
            lines=request.lines,
            status="draft",
            audit_result=_audit_request(request),
        )
        _save_voucher(connection, voucher)
    return voucher


def update_voucher(voucher_id: str, request: VoucherCenterCreateRequest) -> VoucherCenterRecord:
    from app.services.accounting_period_service import validate_account_set

    validate_account_set(request.account_set_id)
    current = _get_voucher(voucher_id)
    if current.status == "reviewed":
        raise HTTPException(status_code=409, detail="已审核凭证需先反审核后才能修改。")
    updated = current.model_copy(
        update={
            "voucher_date": request.voucher_date,
            "account_set_id": request.account_set_id,
            "summary": request.summary,
            "counterparty": request.counterparty,
            "invoice_number": request.invoice_number,
            "amount": request.amount,
            "tax_amount": request.tax_amount,
            "total_amount_with_tax": request.total_amount_with_tax,
            "lines": request.lines,
            "audit_result": _audit_request(request),
        }
    )
    with _connection() as connection:
        _save_voucher(connection, updated)
    return updated


def review_voucher(voucher_id: str, reviewer: str) -> VoucherCenterRecord:
    voucher = _get_voucher(voucher_id)
    updated = voucher.model_copy(update={"status": "reviewed", "reviewed_by": reviewer})
    with _connection() as connection:
        _save_voucher(connection, updated)
    return updated


def unreview_voucher(voucher_id: str) -> VoucherCenterRecord:
    voucher = _get_voucher(voucher_id)
    if voucher.posting_status == "posted":
        raise HTTPException(status_code=409, detail="已过账凭证需先反过账后才能反审核。")
    updated = voucher.model_copy(update={"status": "draft", "reviewed_by": None})
    with _connection() as connection:
        _save_voucher(connection, updated)
    return updated


def post_voucher(voucher_id: str, operator: str) -> VoucherCenterRecord:
    voucher = _get_voucher(voucher_id)
    if voucher.status != "reviewed":
        raise HTTPException(status_code=409, detail="凭证需先审核后才能过账。")
    if voucher.posting_status == "posted":
        raise HTTPException(status_code=409, detail="凭证已过账。")
    from app.services.accounting_period_service import is_accounting_period_closed

    if is_accounting_period_closed(voucher.voucher_date[:7], voucher.account_set_id):
        raise HTTPException(status_code=409, detail="会计期间已关闭，不能过账。")
    updated = voucher.model_copy(
        update={
            "posting_status": "posted",
            "posted_by": operator,
            "posted_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
    )
    with _connection() as connection:
        _save_voucher(connection, updated)
    return updated


def unpost_voucher(voucher_id: str) -> VoucherCenterRecord:
    voucher = _get_voucher(voucher_id)
    if voucher.posting_status != "posted":
        raise HTTPException(status_code=409, detail="未过账凭证不能反过账。")
    updated = voucher.model_copy(
        update={
            "posting_status": "unposted",
            "posted_by": None,
            "posted_at": None,
        }
    )
    with _connection() as connection:
        _save_voucher(connection, updated)
    return updated


def list_vouchers(account_set_id: str | None = None) -> VoucherCenterListResponse:
    with _connection() as connection:
        rows = connection.execute(
            "SELECT payload_json FROM voucher_center_records ORDER BY voucher_number"
        ).fetchall()
    vouchers = [_row_to_voucher(row) for row in rows]
    if account_set_id is not None:
        vouchers = [voucher for voucher in vouchers if voucher.account_set_id == account_set_id]
    return VoucherCenterListResponse(total=len(vouchers), vouchers=vouchers)


def import_vouchers(request: VoucherCenterImportRequest) -> VoucherCenterImportResponse:
    vouchers = [create_voucher(voucher_request) for voucher_request in request.vouchers]
    return VoucherCenterImportResponse(imported_count=len(vouchers), vouchers=vouchers)


def attach_voucher_file(voucher_id: str, filename: str, content_type: str, size: int) -> VoucherCenterRecord:
    voucher = _get_voucher(voucher_id)
    attachment = VoucherAttachment(
        id=f"attachment-{uuid4().hex[:12]}",
        filename=filename,
        content_type=content_type,
        size=size,
        ocr_status="text_supported" if filename.lower().endswith(".txt") or content_type.startswith("text/") else "ocr_engine_required",
    )
    updated = voucher.model_copy(update={"attachments": [*voucher.attachments, attachment]})
    with _connection() as connection:
        _save_voucher(connection, updated)
    return updated


def export_vouchers_csv() -> str:
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["voucher_number", "status", "voucher_date", "summary", "counterparty", "amount", "tax_amount", "total_amount_with_tax"])
    for voucher in list_vouchers().vouchers:
        writer.writerow(
            [
                voucher.voucher_number,
                voucher.status,
                voucher.voucher_date,
                voucher.summary,
                voucher.counterparty,
                f"{voucher.amount:.2f}",
                f"{voucher.tax_amount:.2f}",
                f"{voucher.total_amount_with_tax:.2f}",
            ]
        )
    return output.getvalue()


def _next_voucher_number(connection: sqlite3.Connection, voucher_date: str) -> str:
    month = voucher_date[:7].replace("-", "")
    row = connection.execute(
        "SELECT last_sequence FROM voucher_center_sequences WHERE voucher_month = ?",
        (month,),
    ).fetchone()
    sequence = int(row["last_sequence"]) + 1 if row else 1
    connection.execute(
        """
        INSERT INTO voucher_center_sequences (voucher_month, last_sequence)
        VALUES (?, ?)
        ON CONFLICT(voucher_month) DO UPDATE SET last_sequence = excluded.last_sequence
        """,
        (month, sequence),
    )
    return f"记-{month}-{sequence:04d}"


def _get_voucher(voucher_id: str) -> VoucherCenterRecord:
    with _connection() as connection:
        row = connection.execute(
            "SELECT payload_json FROM voucher_center_records WHERE id = ?",
            (voucher_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="未找到凭证。")
    return _row_to_voucher(row)


def _save_voucher(connection: sqlite3.Connection, voucher: VoucherCenterRecord) -> None:
    voucher_month = voucher.voucher_date[:7].replace("-", "")
    connection.execute(
        """
        INSERT INTO voucher_center_records (
            id,
            voucher_number,
            voucher_date,
            voucher_month,
            payload_json,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            voucher_number = excluded.voucher_number,
            voucher_date = excluded.voucher_date,
            voucher_month = excluded.voucher_month,
            payload_json = excluded.payload_json,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            voucher.id,
            voucher.voucher_number,
            voucher.voucher_date,
            voucher_month,
            voucher.model_dump_json(),
        ),
    )


def _row_to_voucher(row: sqlite3.Row) -> VoucherCenterRecord:
    return VoucherCenterRecord.model_validate_json(row["payload_json"])


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    db_path = _voucher_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        _ensure_schema(connection)
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _voucher_db_path() -> Path:
    return Path(os.environ.get(DB_PATH_ENV, DEFAULT_DB_PATH))


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS voucher_center_records (
            id TEXT PRIMARY KEY,
            voucher_number TEXT NOT NULL UNIQUE,
            voucher_date TEXT NOT NULL,
            voucher_month TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS voucher_center_sequences (
            voucher_month TEXT PRIMARY KEY,
            last_sequence INTEGER NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_voucher_center_records_month
        ON voucher_center_records (voucher_month)
        """
    )


def _audit_request(request: VoucherCenterCreateRequest):
    return review_audit_subject(
        AuditRequest(
            audit_subject="voucher",
            voucher_date=request.voucher_date,
            summary=request.summary,
            counterparty=request.counterparty,
            invoice_number=request.invoice_number,
            amount=request.amount,
            tax_amount=request.tax_amount,
            total_amount_with_tax=request.total_amount_with_tax,
            lines=[
                AuditVoucherLine(
                    account_code=line.account_code,
                    account_name=line.account_name,
                    direction=line.direction,
                    amount=line.amount,
                    explanation=line.explanation,
                )
                for line in request.lines
            ],
        )
    )
