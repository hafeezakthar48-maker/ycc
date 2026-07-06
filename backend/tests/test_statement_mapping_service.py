from decimal import Decimal

from app.services.statement_mapping_service import (
    calculate_statement_lines,
    get_default_statement_mapping_set,
    infer_cash_flow_amounts,
    list_statement_mapping_rules,
    reset_statement_mapping_store,
)


def setup_function():
    reset_statement_mapping_store()


def test_default_mapping_set_contains_four_statements():
    mapping_set = get_default_statement_mapping_set(account_set_id="default")
    rules = list_statement_mapping_rules(mapping_set.mapping_set_id)

    statement_types = {rule.statement_type for rule in rules}

    assert mapping_set.account_set_id == "default"
    assert mapping_set.mapping_set_name == "中国企业会计准则通用报表映射"
    assert statement_types == {
        "balance_sheet",
        "income_statement",
        "cash_flow_statement",
        "equity_statement",
    }
    assert any(rule.line_code == "BS-CASH" for rule in rules)
    assert any(rule.line_code == "IS-NET-PROFIT" for rule in rules)
    assert any(rule.line_code == "CF-OPERATING-NET" for rule in rules)
    assert any(rule.line_code == "EQ-CLOSING" for rule in rules)


def test_calculate_balance_sheet_lines_from_account_balances():
    mapping_set = get_default_statement_mapping_set("default")
    balances = [
        {"account_code": "1002", "account_name": "银行存款", "debit_total": Decimal("1500.00"), "credit_total": Decimal("200.00")},
        {"account_code": "1122", "account_name": "应收账款", "debit_total": Decimal("800.00"), "credit_total": Decimal("100.00")},
        {"account_code": "2202", "account_name": "应付账款", "debit_total": Decimal("50.00"), "credit_total": Decimal("450.00")},
        {"account_code": "4001", "account_name": "实收资本", "debit_total": Decimal("0.00"), "credit_total": Decimal("1600.00")},
    ]

    result = calculate_statement_lines(
        mapping_set_id=mapping_set.mapping_set_id,
        statement_type="balance_sheet",
        account_balances=balances,
        account_activities=[],
        cash_flow_amounts={},
        period_close_amounts={},
    )

    amount_by_code = {line.code: line.amount for line in result.lines}

    assert amount_by_code["BS-CASH"] == Decimal("1300.00")
    assert amount_by_code["BS-AR"] == Decimal("700.00")
    assert amount_by_code["BS-AP"] == Decimal("400.00")
    assert amount_by_code["BS-TOTAL-ASSETS"] == Decimal("2000.00")
    assert result.trace_items[0].line_code == "BS-CASH"


def test_infer_cash_flow_amounts_from_cash_and_counterpart_accounts():
    journal_lines = [
        {
            "entry_id": "je_1",
            "account_code": "1002",
            "direction": "debit",
            "amount": Decimal("500.00"),
            "cash_flow_item_code": "CFO-SALES-CASH",
        },
        {
            "entry_id": "je_1",
            "account_code": "6001",
            "direction": "credit",
            "amount": Decimal("500.00"),
            "cash_flow_item_code": "",
        },
        {
            "entry_id": "je_2",
            "account_code": "1002",
            "direction": "credit",
            "amount": Decimal("120.00"),
            "cash_flow_item_code": "",
        },
        {
            "entry_id": "je_2",
            "account_code": "2211",
            "direction": "debit",
            "amount": Decimal("120.00"),
            "cash_flow_item_code": "",
        },
    ]

    amounts, warnings = infer_cash_flow_amounts(journal_lines)

    assert amounts["CFO-SALES-CASH"] == Decimal("500.00")
    assert amounts["CFO-PAYROLL-CASH"] == Decimal("-120.00")
    assert warnings == ["je_2 使用对方科目推断现金流项目 CFO-PAYROLL-CASH"]
