export type MoneyValue = number | string;

export interface LedgerAccountSummary {
  account_code: string;
  account_name: string;
  debit_total: MoneyValue;
  credit_total: MoneyValue;
  balance_direction: "借" | "贷" | "平" | string;
  balance_amount: MoneyValue;
  entry_count: number;
}

export interface LedgerDetailLine {
  voucher_id: string;
  voucher_number: string;
  voucher_date: string;
  summary: string;
  counterparty: string;
  account_code: string;
  account_name: string;
  direction: "借" | "贷" | string;
  explanation: string;
  currency: string;
  original_amount: MoneyValue;
  exchange_rate: MoneyValue;
  debit_amount: MoneyValue;
  credit_amount: MoneyValue;
  status: string;
}

export interface GeneralLedgerResponse {
  source: string;
  period: string;
  voucher_count: number;
  entry_count: number;
  total_debit: MoneyValue;
  total_credit: MoneyValue;
  balanced: boolean;
  accounts: LedgerAccountSummary[];
}

export interface DetailLedgerResponse {
  source: string;
  period: string;
  account_code: string;
  account_name: string;
  line_count: number;
  debit_total: MoneyValue;
  credit_total: MoneyValue;
  balance_direction: "借" | "贷" | "平" | string;
  balance_amount: MoneyValue;
  lines: LedgerDetailLine[];
}

export interface AccountBalanceTableResponse {
  source: string;
  period: string;
  account_count: number;
  total_debit: MoneyValue;
  total_credit: MoneyValue;
  balanced: boolean;
  accounts: LedgerAccountSummary[];
}

export interface AccountSetItem {
  id: string;
  name: string;
  base_currency: string;
  accounting_standard: string;
  is_default: boolean;
}

export interface AccountSetListResponse {
  account_sets: AccountSetItem[];
}

export interface AccountingPeriodItem {
  account_set_id: string;
  period: string;
  status: "open" | "closed" | string;
  closed_by: string | null;
  closed_at: string | null;
  voucher_count: number;
  posted_voucher_count: number;
}

export interface AccountingPeriodListResponse {
  account_set_id: string;
  periods: AccountingPeriodItem[];
}
