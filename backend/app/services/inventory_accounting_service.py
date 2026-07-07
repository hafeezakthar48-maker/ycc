from decimal import Decimal, ROUND_HALF_UP


MONEY_QUANT = Decimal("0.01")


def calculate_moving_average_cost(
    existing_quantity: Decimal,
    existing_amount: Decimal,
    receipt_quantity: Decimal,
    receipt_amount: Decimal,
) -> Decimal:
    total_quantity = Decimal(existing_quantity) + Decimal(receipt_quantity)
    if total_quantity <= Decimal("0"):
        return Decimal("0.00")
    return _money((Decimal(existing_amount) + Decimal(receipt_amount)) / total_quantity)


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
