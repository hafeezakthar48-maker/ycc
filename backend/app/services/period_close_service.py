from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException

from app.models.period_close import PeriodCloseRun, PeriodCloseRunCreate, PeriodCloseRunListResponse
from app.services.accounting_period_service import validate_account_set


_PERIOD_CLOSE_RUNS: dict[str, PeriodCloseRun] = {}


def reset_period_close_store() -> None:
    _PERIOD_CLOSE_RUNS.clear()


def start_period_close_run(payload: PeriodCloseRunCreate) -> PeriodCloseRun:
    validate_account_set(payload.account_set_id)
    now = _now_iso()
    run = PeriodCloseRun(
        run_id=f"pclose_{uuid4().hex}",
        account_set_id=payload.account_set_id,
        period=payload.period,
        close_type=payload.close_type,
        status="draft",
        requested_by=payload.requested_by,
        created_at=now,
        updated_at=now,
    )
    _PERIOD_CLOSE_RUNS[run.run_id] = run
    return run


def get_period_close_run(run_id: str) -> PeriodCloseRun:
    run = _PERIOD_CLOSE_RUNS.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="期间结账运行记录不存在。")
    return run


def list_period_close_runs(
    account_set_id: str = "default",
    period: str | None = None,
) -> PeriodCloseRunListResponse:
    validate_account_set(account_set_id)
    runs = [
        run
        for run in _PERIOD_CLOSE_RUNS.values()
        if run.account_set_id == account_set_id and (period is None or run.period == period)
    ]
    runs.sort(key=lambda run: (run.created_at, run.run_id), reverse=True)
    return PeriodCloseRunListResponse(
        account_set_id=account_set_id,
        period=period,
        total=len(runs),
        runs=runs,
    )


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
