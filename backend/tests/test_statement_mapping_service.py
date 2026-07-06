from app.services.statement_mapping_service import (
    get_default_statement_mapping_set,
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
