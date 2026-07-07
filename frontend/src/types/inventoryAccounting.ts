import type { JournalEntryRecord } from "./accounting";

export type MoneyValue = number | string;
export type QuantityValue = number | string;

export type InventoryMovementType =
  | "purchase_receipt"
  | "sales_issue"
  | "sales_return"
  | "purchase_return"
  | "adjustment_in"
  | "adjustment_out";

export interface InventoryMovement {
  account_set_id: string;
  sku_id: string;
  warehouse_id: string;
  movement_date: string;
  movement_type: InventoryMovementType;
  quantity: QuantityValue;
  amount: MoneyValue;
  source_id: string;
  movement_id: string;
  unit_cost: MoneyValue;
  journal_entry_id?: string | null;
}

export interface InventoryBalance {
  account_set_id: string;
  sku_id: string;
  warehouse_id: string;
  quantity: QuantityValue;
  amount: MoneyValue;
  moving_average_cost: MoneyValue;
}

export interface InventoryAccountingSummary {
  account_set_id: string;
  total_balances: number;
  total_movements: number;
  balances: InventoryBalance[];
  movements: InventoryMovement[];
}

export interface InventoryPurchaseReceiptRequest {
  account_set_id: string;
  sku_id: string;
  warehouse_id: string;
  period: string;
  quantity: QuantityValue;
  amount: MoneyValue;
  supplier_id: string;
}

export interface InventorySalesIssueRequest {
  account_set_id: string;
  sku_id: string;
  warehouse_id: string;
  period: string;
  quantity: QuantityValue;
}

export interface InventorySalesIssueResult {
  account_set_id: string;
  sku_id: string;
  warehouse_id: string;
  period: string;
  movement_id: string;
  source_id: string;
  quantity: QuantityValue;
  cost_amount: MoneyValue;
  unit_cost: MoneyValue;
  cogs_account_code: string;
  inventory_account_code: string;
  journal_entry_id: string;
}

export interface InventoryImpairmentRequest {
  account_set_id: string;
  sku_id: string;
  period: string;
  amount: MoneyValue;
}

export interface InventoryCountVarianceRequest {
  account_set_id: string;
  sku_id: string;
  warehouse_id: string;
  period: string;
  actual_quantity: QuantityValue;
  approved_by: string;
  approved_at: string;
}

export interface InventoryCountVarianceResult {
  account_set_id: string;
  sku_id: string;
  warehouse_id: string;
  period: string;
  variance_type: "gain" | "loss" | "none";
  book_quantity: QuantityValue;
  actual_quantity: QuantityValue;
  variance_quantity: QuantityValue;
  variance_amount: MoneyValue;
  source_id: string;
  approved_by: string;
  approved_at: string;
  journal_entry_id?: string | null;
}

export type InventoryImpairmentResult = JournalEntryRecord;
