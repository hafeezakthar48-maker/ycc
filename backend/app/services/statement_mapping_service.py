from __future__ import annotations

from datetime import datetime, timezone

from app.models.statement_mapping import (
    CashFlowItemMapping,
    StatementMappingRule,
    StatementMappingSet,
)


_MAPPING_SETS: dict[str, StatementMappingSet] = {}
_MAPPING_RULES: dict[str, list[StatementMappingRule]] = {}
_CASH_FLOW_ITEMS: dict[str, CashFlowItemMapping] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def reset_statement_mapping_store() -> None:
    _MAPPING_SETS.clear()
    _MAPPING_RULES.clear()
    _CASH_FLOW_ITEMS.clear()


def get_default_statement_mapping_set(account_set_id: str = "default") -> StatementMappingSet:
    mapping_set_id = f"stmtmap_{account_set_id}_default"
    if mapping_set_id not in _MAPPING_SETS:
        _MAPPING_SETS[mapping_set_id] = StatementMappingSet(
            mapping_set_id=mapping_set_id,
            account_set_id=account_set_id,
            mapping_set_name="中国企业会计准则通用报表映射",
            updated_at=_now_iso(),
        )
        _MAPPING_RULES[mapping_set_id] = _default_rules(mapping_set_id)
        for item in _default_cash_flow_items():
            _CASH_FLOW_ITEMS[item.item_code] = item
    return _MAPPING_SETS[mapping_set_id]


def list_statement_mapping_rules(mapping_set_id: str) -> list[StatementMappingRule]:
    return list(_MAPPING_RULES.get(mapping_set_id, []))


def _rule(
    mapping_set_id: str,
    statement_type: str,
    line_code: str,
    line_name: str,
    display_order: int,
    source_type: str,
    normal_side: str = "none",
    account_prefixes: list[str] | None = None,
    cash_flow_item_codes: list[str] | None = None,
    formula: str = "",
    sign: int = 1,
) -> StatementMappingRule:
    return StatementMappingRule(
        rule_id=f"{mapping_set_id}:{line_code}",
        mapping_set_id=mapping_set_id,
        statement_type=statement_type,
        line_code=line_code,
        line_name=line_name,
        display_order=display_order,
        source_type=source_type,
        normal_side=normal_side,
        account_prefixes=account_prefixes or [],
        cash_flow_item_codes=cash_flow_item_codes or [],
        formula=formula,
        sign=sign,
    )


def _default_rules(mapping_set_id: str) -> list[StatementMappingRule]:
    return [
        _rule(mapping_set_id, "balance_sheet", "BS-CASH", "货币资金", 10, "account_balance", "debit", ["1001", "1002"]),
        _rule(mapping_set_id, "balance_sheet", "BS-AR", "应收账款", 20, "account_balance", "debit", ["1122"]),
        _rule(
            mapping_set_id,
            "balance_sheet",
            "BS-INVENTORY",
            "存货",
            30,
            "account_balance",
            "debit",
            ["1401", "1403", "1405"],
        ),
        _rule(mapping_set_id, "balance_sheet", "BS-FA-NET", "固定资产净额", 40, "formula", formula="BS-FA-COST - BS-ACC-DEPR"),
        _rule(mapping_set_id, "balance_sheet", "BS-FA-COST", "固定资产原值", 41, "account_balance", "debit", ["1601"]),
        _rule(mapping_set_id, "balance_sheet", "BS-ACC-DEPR", "累计折旧", 42, "account_balance", "credit", ["1602"]),
        _rule(mapping_set_id, "balance_sheet", "BS-AP", "应付账款", 110, "account_balance", "credit", ["2202"]),
        _rule(mapping_set_id, "balance_sheet", "BS-TAX", "应交税费", 120, "account_balance", "credit", ["2221"]),
        _rule(mapping_set_id, "balance_sheet", "BS-EQUITY", "所有者权益", 210, "account_balance", "credit", ["4001", "4103", "4104"]),
        _rule(
            mapping_set_id,
            "balance_sheet",
            "BS-TOTAL-ASSETS",
            "资产合计",
            900,
            "formula",
            formula="BS-CASH + BS-AR + BS-INVENTORY + BS-FA-NET",
        ),
        _rule(
            mapping_set_id,
            "balance_sheet",
            "BS-TOTAL-LIAB-EQUITY",
            "负债和所有者权益合计",
            910,
            "formula",
            formula="BS-AP + BS-TAX + BS-EQUITY",
        ),
        _rule(mapping_set_id, "income_statement", "IS-REVENUE", "营业收入", 10, "account_activity", "credit", ["6001", "6051"]),
        _rule(mapping_set_id, "income_statement", "IS-COST", "营业成本", 20, "account_activity", "debit", ["6401"]),
        _rule(mapping_set_id, "income_statement", "IS-TAX-SURCHARGE", "税金及附加", 30, "account_activity", "debit", ["6403"]),
        _rule(mapping_set_id, "income_statement", "IS-EXPENSE", "期间费用", 40, "account_activity", "debit", ["6601", "6602", "6603"]),
        _rule(
            mapping_set_id,
            "income_statement",
            "IS-NET-PROFIT",
            "净利润",
            900,
            "formula",
            formula="IS-REVENUE - IS-COST - IS-TAX-SURCHARGE - IS-EXPENSE",
        ),
        _rule(
            mapping_set_id,
            "cash_flow_statement",
            "CF-OPERATING-NET",
            "经营活动现金流量净额",
            10,
            "cash_flow_item",
            cash_flow_item_codes=["CFO-SALES-CASH", "CFO-PURCHASE-CASH", "CFO-PAYROLL-CASH", "CFO-TAX-CASH"],
        ),
        _rule(
            mapping_set_id,
            "cash_flow_statement",
            "CF-INVESTING-NET",
            "投资活动现金流量净额",
            20,
            "cash_flow_item",
            cash_flow_item_codes=["CFI-ASSET-PURCHASE", "CFI-ASSET-DISPOSAL"],
        ),
        _rule(
            mapping_set_id,
            "cash_flow_statement",
            "CF-FINANCING-NET",
            "筹资活动现金流量净额",
            30,
            "cash_flow_item",
            cash_flow_item_codes=["CFF-LOAN-IN", "CFF-LOAN-REPAY"],
        ),
        _rule(
            mapping_set_id,
            "cash_flow_statement",
            "CF-NET-INCREASE",
            "现金及现金等价物净增加额",
            900,
            "formula",
            formula="CF-OPERATING-NET + CF-INVESTING-NET + CF-FINANCING-NET",
        ),
        _rule(mapping_set_id, "equity_statement", "EQ-OPENING", "期初所有者权益", 10, "account_balance", "credit", ["4001", "4103", "4104"]),
        _rule(mapping_set_id, "equity_statement", "EQ-PROFIT", "本期净利润", 20, "formula", formula="IS-NET-PROFIT"),
        _rule(mapping_set_id, "equity_statement", "EQ-DISTRIBUTION", "利润分配", 30, "period_close_result", "debit", ["4104"]),
        _rule(mapping_set_id, "equity_statement", "EQ-CLOSING", "期末所有者权益", 900, "formula", formula="EQ-OPENING + EQ-PROFIT - EQ-DISTRIBUTION"),
    ]


def _default_cash_flow_items() -> list[CashFlowItemMapping]:
    return [
        CashFlowItemMapping(
            item_code="CFO-SALES-CASH",
            item_name="销售商品、提供劳务收到的现金",
            activity_type="operating",
            cash_account_prefixes=["1001", "1002"],
            counterpart_account_prefixes=["1122", "6001", "6051"],
            direction="inflow",
        ),
        CashFlowItemMapping(
            item_code="CFO-PURCHASE-CASH",
            item_name="购买商品、接受劳务支付的现金",
            activity_type="operating",
            cash_account_prefixes=["1001", "1002"],
            counterpart_account_prefixes=["1401", "1403", "1405", "2202"],
            direction="outflow",
        ),
        CashFlowItemMapping(
            item_code="CFO-PAYROLL-CASH",
            item_name="支付给职工以及为职工支付的现金",
            activity_type="operating",
            cash_account_prefixes=["1001", "1002"],
            counterpart_account_prefixes=["2211"],
            direction="outflow",
        ),
        CashFlowItemMapping(
            item_code="CFO-TAX-CASH",
            item_name="支付的各项税费",
            activity_type="operating",
            cash_account_prefixes=["1001", "1002"],
            counterpart_account_prefixes=["2221"],
            direction="outflow",
        ),
        CashFlowItemMapping(
            item_code="CFI-ASSET-PURCHASE",
            item_name="购建固定资产支付的现金",
            activity_type="investing",
            cash_account_prefixes=["1001", "1002"],
            counterpart_account_prefixes=["1601"],
            direction="outflow",
        ),
        CashFlowItemMapping(
            item_code="CFI-ASSET-DISPOSAL",
            item_name="处置固定资产收到的现金",
            activity_type="investing",
            cash_account_prefixes=["1001", "1002"],
            counterpart_account_prefixes=["1606"],
            direction="inflow",
        ),
        CashFlowItemMapping(
            item_code="CFF-LOAN-IN",
            item_name="取得借款收到的现金",
            activity_type="financing",
            cash_account_prefixes=["1001", "1002"],
            counterpart_account_prefixes=["2001", "2501"],
            direction="inflow",
        ),
        CashFlowItemMapping(
            item_code="CFF-LOAN-REPAY",
            item_name="偿还债务支付的现金",
            activity_type="financing",
            cash_account_prefixes=["1001", "1002"],
            counterpart_account_prefixes=["2001", "2501"],
            direction="outflow",
        ),
    ]
