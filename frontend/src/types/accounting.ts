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

export interface CurrencyItem {
  currency_code: string;
  currency_name: string;
  decimal_places: number;
  is_active: boolean;
}

export interface CurrencyListResponse {
  currencies: CurrencyItem[];
}

export interface ExchangeRateRecord {
  id: string;
  account_set_id: string;
  rate_date: string;
  source_currency: string;
  target_currency: string;
  rate: MoneyValue;
  source: string;
  updated_at: string;
}

export interface ExchangeRateCreateRequest {
  account_set_id: string;
  rate_date: string;
  source_currency: string;
  target_currency: string;
  rate: MoneyValue;
  source?: string;
}

export interface ExchangeRateListResponse {
  account_set_id: string;
  rates: ExchangeRateRecord[];
}

export type AuxiliaryDimensionType =
  | "customer"
  | "supplier"
  | "employee"
  | "department"
  | "project"
  | "asset"
  | "platform"
  | "sku";

export interface AuxiliaryDimensionRecord {
  id: string;
  account_set_id: string;
  dimension_type: AuxiliaryDimensionType | string;
  dimension_code: string;
  dimension_name: string;
  is_active: boolean;
  updated_at: string;
}

export interface AuxiliaryDimensionCreateRequest {
  account_set_id: string;
  dimension_type: AuxiliaryDimensionType | string;
  dimension_code: string;
  dimension_name: string;
  is_active?: boolean;
}

export interface AuxiliaryDimensionListResponse {
  account_set_id: string;
  dimension_type: string | null;
  supported_dimension_types: string[];
  total: number;
  dimensions: AuxiliaryDimensionRecord[];
}

export interface JournalLineDimension {
  dimension_type: AuxiliaryDimensionType | string;
  dimension_code: string;
  dimension_name: string;
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
  dimensions: JournalLineDimension[];
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
