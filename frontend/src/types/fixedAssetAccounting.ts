import type { JournalEntryRecord } from "./accounting";
import type { MoneyValue } from "./fixedAsset";

export type FormalAssetAccountingStatus =
  | "not_capitalized"
  | "capitalized"
  | "depreciating"
  | "impaired"
  | "disposed"
  | "sold"
  | string;

export interface FormalAssetAccountingCard {
  account_set_id: string;
  asset_id: string;
  asset_code: string;
  asset_name: string;
  category: string;
  acquisition_date: string;
  original_cost: MoneyValue;
  salvage_value: MoneyValue;
  useful_life_months: number;
  monthly_depreciation: MoneyValue;
  accumulated_depreciation: MoneyValue;
  impairment_amount: MoneyValue;
  net_book_value: MoneyValue;
  asset_status: string;
  formal_accounting_status: FormalAssetAccountingStatus;
  capitalization_entry_id: string | null;
  last_depreciation_entry_id: string | null;
  last_depreciated_period: string | null;
  impairment_entry_ids: string[];
  disposal_entry_ids: string[];
}

export interface FormalAssetAccountingCardListResponse {
  account_set_id: string;
  cards: FormalAssetAccountingCard[];
}

export interface FixedAssetCapitalizationRequest {
  account_set_id?: string;
  asset_id: string;
  period: string;
  credit_account_code?: string;
}

export interface FixedAssetDepreciationPostRequest {
  account_set_id?: string;
  period: string;
}

export interface FixedAssetImpairmentPostRequest {
  account_set_id?: string;
  asset_id: string;
  period: string;
  amount: MoneyValue;
}

export interface FixedAssetDisposalPostRequest {
  account_set_id?: string;
  asset_id: string;
  period: string;
  proceeds_amount: MoneyValue;
  disposal_date?: string | null;
  proceeds_account_code?: string;
  reason?: string;
}

export interface FixedAssetAccountingEntryBatch {
  account_set_id: string;
  period: string;
  status: "generated" | "existing" | "skipped" | string;
  depreciated_count: number;
  total_depreciation: MoneyValue;
  entries: JournalEntryRecord[];
}

export interface FixedAssetDisposalAccountingResult {
  account_set_id: string;
  period: string;
  asset_id: string;
  asset_code: string;
  asset_status: string;
  clearing_account_code: string;
  disposal_gain_or_loss: MoneyValue;
  entries: JournalEntryRecord[];
}
