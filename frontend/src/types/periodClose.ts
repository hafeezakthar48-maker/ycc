import type { AccountingPeriodItem } from "./ledger";

export type MoneyValue = number | string;

export type PeriodCloseStatus =
  | "draft"
  | "checking"
  | "ready"
  | "generated"
  | "closed"
  | "reopened"
  | "failed";

export type PeriodCloseType = "month" | "year";

export type PeriodCloseActionType =
  | "fixed_asset_depreciation"
  | "payroll_accrual"
  | "tax_accrual"
  | "fx_revaluation"
  | "profit_loss_carryforward"
  | "inventory_cost_rollforward"
  | "year_end_profit_distribution"
  | "bad_debt_provision";

export interface PeriodCloseRun {
  run_id: string;
  account_set_id: string;
  period: string;
  close_type: PeriodCloseType;
  status: PeriodCloseStatus;
  requested_by: string;
  created_at: string;
  updated_at: string;
  closed_at?: string | null;
  reopened_at?: string | null;
}

export interface PeriodCloseCheckRequest {
  account_set_id: string;
  period: string;
}

export interface PeriodCloseCheckItem {
  check_code: string;
  check_name: string;
  status: "passed" | "failed" | "warning";
  severity: "blocker" | "warning";
  message: string;
  evidence?: Record<string, string | number>;
}

export interface PeriodCloseCheckResponse {
  items: PeriodCloseCheckItem[];
}

export interface PeriodCloseGenerateRequest extends PeriodCloseCheckRequest {
  actions: PeriodCloseActionType[];
  generated_by: string;
  force_regenerate?: boolean;
}

export interface PeriodCloseActionResult {
  action_type: PeriodCloseActionType;
  status: "skipped" | "generated" | "existing" | "failed";
  journal_entry_ids: string[];
  amount: MoneyValue;
  message: string;
}

export interface PeriodCloseGenerateResponse {
  results: PeriodCloseActionResult[];
}

export interface PeriodClosePeriodRequest extends PeriodCloseCheckRequest {
  operator: string;
}

export type PeriodClosePeriodResponse = AccountingPeriodItem;
