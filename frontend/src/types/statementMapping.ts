export type StatementType =
  | "balance_sheet"
  | "income_statement"
  | "cash_flow_statement"
  | "equity_statement";

export type StatementRuleSource =
  | "account_balance"
  | "account_activity"
  | "formula"
  | "cash_flow_item"
  | "period_close_result";

export interface StatementMappingSet {
  mapping_set_id: string;
  account_set_id: string;
  mapping_set_name: string;
  base_currency: string;
  is_default: boolean;
  enabled: boolean;
  updated_by: string;
  updated_at: string;
}

export interface StatementMappingRule {
  rule_id: string;
  mapping_set_id: string;
  statement_type: StatementType;
  line_code: string;
  line_name: string;
  display_order: number;
  source_type: StatementRuleSource;
  normal_side: "debit" | "credit" | "none";
  account_prefixes: string[];
  cash_flow_item_codes: string[];
  formula: string;
  sign: number;
  enabled: boolean;
}

export interface StatementMappingSetResponse {
  mapping_set: StatementMappingSet;
  rules: StatementMappingRule[];
}
