from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


VatDirection = Literal["input", "output", "input_transfer_out"]


class VatLedgerLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    tax_direction: VatDirection
    invoice_no: str = Field(min_length=1, max_length=80)
    tax_base: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=2)
    tax_amount: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=2)
    counterparty_id: str | None = Field(default=None, max_length=64)
    source_journal_entry_id: str = Field(min_length=1, max_length=80)


class SurtaxCalculationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    urban: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=2)
    education: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=2)
    local: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=2)
    total: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=2)


class IncomeTaxCalculationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accounting_profit: Decimal = Field(max_digits=16, decimal_places=2)
    taxable_increase: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=2)
    taxable_decrease: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=2)
    taxable_income: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=2)
    tax_rate: Decimal = Field(ge=Decimal("0"), le=Decimal("1"), max_digits=8, decimal_places=6)
    income_tax_payable: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=2)


class TaxFilingWorksheet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str
    period: str
    output_vat: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=2)
    input_vat: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=2)
    input_transfer_out: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=2)
    vat_payable: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=2)
    surtax_payable: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=2)
    income_tax_payable: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=2)


class VatLedgerLineListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str
    period: str
    total: int
    lines: list[VatLedgerLine]


class TaxAmountPostRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    amount: Decimal = Field(gt=Decimal("0"), max_digits=16, decimal_places=2)


class SurtaxAccrualRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    vat_payable: Decimal = Field(gt=Decimal("0"), max_digits=16, decimal_places=2)
    urban_maintenance_rate: Decimal = Field(default=Decimal("0.07"), ge=Decimal("0"), max_digits=8, decimal_places=6)
    education_rate: Decimal = Field(default=Decimal("0.03"), ge=Decimal("0"), max_digits=8, decimal_places=6)
    local_education_rate: Decimal = Field(default=Decimal("0.02"), ge=Decimal("0"), max_digits=8, decimal_places=6)


class TaxPaymentPostRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(default="default", min_length=1, max_length=64)
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    tax_account_code: str = Field(min_length=1, max_length=32)
    amount: Decimal = Field(gt=Decimal("0"), max_digits=16, decimal_places=2)
    bank_account_code: str = Field(default="1002", min_length=1, max_length=32)
