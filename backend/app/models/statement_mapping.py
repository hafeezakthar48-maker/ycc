from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


StatementType = Literal[
    "balance_sheet",
    "income_statement",
    "cash_flow_statement",
    "equity_statement",
]
StatementRuleSource = Literal[
    "account_balance",
    "account_activity",
    "formula",
    "cash_flow_item",
    "period_close_result",
]
StatementNormalSide = Literal["debit", "credit", "none"]


class StatementMappingSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mapping_set_id: str
    account_set_id: str = "default"
    mapping_set_name: str
    base_currency: str = "CNY"
    is_default: bool = True
    enabled: bool = True
    updated_by: str = "system"
    updated_at: str


class StatementMappingRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    mapping_set_id: str
    statement_type: StatementType
    line_code: str
    line_name: str
    display_order: int
    source_type: StatementRuleSource
    normal_side: StatementNormalSide = "none"
    account_prefixes: list[str] = Field(default_factory=list)
    cash_flow_item_codes: list[str] = Field(default_factory=list)
    formula: str = ""
    sign: int = Field(default=1, ge=-1, le=1)
    enabled: bool = True


class CashFlowItemMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_code: str
    item_name: str
    activity_type: Literal["operating", "investing", "financing"]
    cash_account_prefixes: list[str]
    counterpart_account_prefixes: list[str]
    direction: Literal["inflow", "outflow"]


class StatementLineTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_code: str
    rule_id: str
    source_type: StatementRuleSource
    source_account_codes: list[str] = Field(default_factory=list)
    cash_flow_item_codes: list[str] = Field(default_factory=list)
    formula: str
    amount: Decimal
    warnings: list[str] = Field(default_factory=list)


class StatementValidationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    validation_code: str
    validation_name: str
    status: Literal["passed", "failed", "warning"]
    message: str
    expected_amount: Decimal | None = None
    actual_amount: Decimal | None = None
