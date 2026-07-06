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


def build_counterparty_balances(
    account_set_id: str,
    period: str,
    open_item_type: str,
) -> CounterpartyBalanceResponse:
    open_items = [
        item
        for item in build_counterparty_open_items(account_set_id, period, open_item_type)
        if item.open_base_amount > ZERO
    ]
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
