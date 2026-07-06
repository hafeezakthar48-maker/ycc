export type MoneyValue = number | string;
export type FixedAssetStatus = "active" | "disposed" | "sold" | string;
export type InventoryStatus = "unchecked" | "checked" | string;

export interface FixedAssetCreateRequest {
  account_set_id?: string;
  name: string;
  category: string;
  acquisition_date: string;
  original_cost: MoneyValue;
  salvage_value: MoneyValue;
  useful_life_months: number;
  depreciation_method?: "straight_line";
  location: string;
  custodian: string;
}

export interface FixedAssetRecord {
  id: string;
  account_set_id: string;
  asset_code: string;
  name: string;
  category: string;
  acquisition_date: string;
  original_cost: MoneyValue;
  salvage_value: MoneyValue;
  useful_life_months: number;
  depreciation_method: string;
  monthly_depreciation: MoneyValue;
  accumulated_depreciation: MoneyValue;
  net_book_value: MoneyValue;
  status: FixedAssetStatus;
  location: string;
  custodian: string;
  condition: string;
  inventory_status: InventoryStatus;
  last_inventory_date: string | null;
  last_inventory_by: string | null;
  inventory_note: string | null;
  last_depreciated_period: string | null;
  disposal_date: string | null;
  disposal_reason: string | null;
  disposed_by: string | null;
  sale_date: string | null;
  sale_amount: MoneyValue | null;
  sale_gain_or_loss: MoneyValue | null;
  sale_reason: string | null;
  sold_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface FixedAssetSummary {
  asset_count: number;
  active_count: number;
  disposed_count: number;
  sold_count: number;
  original_cost_total: MoneyValue;
  accumulated_depreciation_total: MoneyValue;
  net_book_value_total: MoneyValue;
  monthly_depreciation_total: MoneyValue;
}

export interface FixedAssetListResponse {
  account_set_id: string;
  summary: FixedAssetSummary;
  assets: FixedAssetRecord[];
}

export interface FixedAssetDepreciationRunRequest {
  account_set_id?: string;
  period: string;
  operator?: string;
}

export interface FixedAssetDepreciationRunResponse {
  account_set_id: string;
  period: string;
  operator: string;
  depreciated_count: number;
  total_depreciation: MoneyValue;
  assets: FixedAssetRecord[];
}

export interface FixedAssetInventoryRequest {
  inventory_date: string;
  location: string;
  custodian: string;
  condition: string;
  operator?: string;
  note?: string | null;
}

export interface FixedAssetDisposeRequest {
  disposal_date: string;
  reason: string;
  operator?: string;
}

export interface FixedAssetSaleRequest {
  sale_date: string;
  sale_amount: MoneyValue;
  reason: string;
  operator?: string;
}
