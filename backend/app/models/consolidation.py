from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.financial_statement import BalanceSheet, CashFlowStatement, IncomeStatement


ConsolidationMethod = Literal["full", "proportionate", "equity_method"]
EliminationType = Literal[
    "intercompany_balance",
    "intercompany_revenue_cost",
    "investment_equity",
    "unrealized_profit",
]


class ConsolidationEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consolidation_group_id: str = Field(min_length=1, max_length=80)
    account_set_id: str = Field(min_length=1, max_length=64)
    entity_name: str = Field(min_length=1, max_length=120)
    ownership_percentage: Decimal = Field(gt=Decimal("0"), le=Decimal("1"), max_digits=8, decimal_places=6)
    consolidation_method: ConsolidationMethod = "full"


class ConsolidationGroupCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_id: str = Field(min_length=1, max_length=80)
    group_name: str = Field(min_length=1, max_length=160)
    entities: list[ConsolidationEntity] = Field(min_length=1)


class ConsolidationGroup(ConsolidationGroupCreate):
    status: Literal["active", "archived"] = "active"


class ConsolidationEliminationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    elimination_id: str = Field(min_length=1, max_length=120)
    group_id: str = Field(min_length=1, max_length=80)
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    elimination_type: EliminationType
    debit_account_code: str = Field(min_length=1, max_length=32)
    credit_account_code: str = Field(min_length=1, max_length=32)
    amount: Decimal = Field(gt=Decimal("0"), max_digits=16, decimal_places=2)
    explanation: str = Field(min_length=1, max_length=240)


class ConsolidationReportingPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = Field(min_length=1, max_length=64)
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    balance_sheet: BalanceSheet
    income_statement: IncomeStatement
    cash_flow_statement: CashFlowStatement


class ConsolidationGroupListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_groups: int
    groups: list[ConsolidationGroup]


class ConsolidationEliminationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_id: str
    period: str
    total_eliminations: int
    eliminations: list[ConsolidationEliminationEntry]


class ConsolidationEliminationRebuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_id: str = Field(min_length=1, max_length=80)
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    intercompany_balance_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"), max_digits=16, decimal_places=2)
    intercompany_revenue_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"), max_digits=16, decimal_places=2)
    intercompany_cost_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"), max_digits=16, decimal_places=2)
    ending_internal_inventory_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"), max_digits=16, decimal_places=2)
    internal_gross_margin_rate: Decimal = Field(default=Decimal("0.000000"), ge=Decimal("0"), le=Decimal("1"), max_digits=8, decimal_places=6)
    investment_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"), max_digits=16, decimal_places=2)
    subsidiary_equity_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"), max_digits=16, decimal_places=2)
    ownership_percentage: Decimal = Field(default=Decimal("1.000000"), gt=Decimal("0"), le=Decimal("1"), max_digits=8, decimal_places=6)


class ConsolidatedStatementResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_id: str
    period: str
    balance_sheet: BalanceSheet
    income_statement: IncomeStatement
    cash_flow_statement: CashFlowStatement
    minority_interest: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=2)
    minority_profit: Decimal = Field(ge=Decimal("0"), max_digits=16, decimal_places=2)
    elimination_count: int
