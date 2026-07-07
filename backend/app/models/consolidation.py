from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
