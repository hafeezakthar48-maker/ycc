from decimal import Decimal


def calculate_even_monthly_amount(total_amount: Decimal, months: int) -> list[Decimal]:
    base = (total_amount / Decimal(months)).quantize(Decimal("0.01"))
    amounts = [base for _ in range(months)]
    difference = total_amount - sum(amounts)
    amounts[-1] = (amounts[-1] + difference).quantize(Decimal("0.01"))
    return amounts
