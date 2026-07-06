import type { MoneyValue } from "./ledger";

export interface AccountItem {
  account_set_id: string;
  account_code: string;
  account_name: string;
  account_type: "asset" | "liability" | "equity" | "revenue" | "cost" | "expense" | string;
  normal_balance: "debit" | "credit" | string;
  is_active: boolean;
}

export interface AccountListResponse {
  account_set_id: string;
  accounts: AccountItem[];
}

export interface JournalLineRecord {
  id: string;
  journal_entry_id: string;
  line_no: number;
  account_code: string;
  account_name: string;
  direction: "debit" | "credit" | string;
  currency: string;
  original_amount: MoneyValue;
  exchange_rate: MoneyValue;
  base_amount: MoneyValue;
  description: string;
}

export interface JournalEntryRecord {
  id: string;
  account_set_id: string;
  period: string;
  entry_date: string;
  entry_number: string;
  source_type: string;
  source_id: string;
  description: string;
  status: "posted" | "reversed" | string;
  base_currency: string;
  created_by: string;
  posted_by: string;
  posted_at: string;
  reversal_of_entry_id: string | null;
  lines: JournalLineRecord[];
}

export interface JournalEntryListResponse {
  account_set_id: string;
  period: string | null;
  total: number;
  entries: JournalEntryRecord[];
}
