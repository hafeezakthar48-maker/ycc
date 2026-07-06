from app.models.accounting import AccountItem, AccountListResponse
from app.services.accounting_period_service import validate_account_set


_BASE_ACCOUNTS: tuple[AccountItem, ...] = (
    AccountItem(account_set_id="default", account_code="1001", account_name="库存现金", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="1002", account_name="银行存款", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="1122", account_name="应收账款", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="1405", account_name="库存商品", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="1601", account_name="固定资产", account_type="asset", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="2001", account_name="短期借款", account_type="liability", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="2202", account_name="应付账款", account_type="liability", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="2221", account_name="应交税费", account_type="liability", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="4001", account_name="实收资本", account_type="equity", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="6001", account_name="主营业务收入", account_type="revenue", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="6051", account_name="其他业务收入", account_type="revenue", normal_balance="credit"),
    AccountItem(account_set_id="default", account_code="6401", account_name="主营业务成本", account_type="cost", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="6601", account_name="销售费用", account_type="expense", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="6602", account_name="管理费用", account_type="expense", normal_balance="debit"),
    AccountItem(account_set_id="default", account_code="6603", account_name="财务费用", account_type="expense", normal_balance="debit"),
)


def reset_accounting_store() -> None:
    return None


def get_chart_of_accounts(account_set_id: str = "default") -> AccountListResponse:
    validate_account_set(account_set_id)
    accounts = [account.model_copy(update={"account_set_id": account_set_id}) for account in _BASE_ACCOUNTS]
    return AccountListResponse(account_set_id=account_set_id, accounts=accounts)
