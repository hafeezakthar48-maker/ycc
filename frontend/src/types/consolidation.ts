import type {
  BalanceSheet,
  CashFlowStatement,
  IncomeStatement
} from "./financialStatement";

export type ConsolidationMethod = "full" | "proportionate" | "equity_method";
export type ConsolidationEliminationType =
  | "intercompany_balance"
  | "intercompany_revenue_cost"
  | "investment_equity"
  | "unrealized_profit";

export interface ConsolidationEntity {
  consolidation_group_id: string;
  account_set_id: string;
  entity_name: string;
  ownership_percentage: string;
  consolidation_method: ConsolidationMethod;
}

export interface ConsolidationGroupCreateRequest {
  group_id: string;
  group_name: string;
  entities: ConsolidationEntity[];
}

export interface ConsolidationGroup extends ConsolidationGroupCreateRequest {
  status: "active" | "archived";
}

export interface ConsolidationGroupListResponse {
  total_groups: number;
  groups: ConsolidationGroup[];
}

export interface ConsolidationReportingPackage {
  account_set_id: string;
  period: string;
  balance_sheet: BalanceSheet;
  income_statement: IncomeStatement;
  cash_flow_statement: CashFlowStatement;
}

export interface ConsolidationEliminationEntry {
  elimination_id: string;
  group_id: string;
  period: string;
  elimination_type: ConsolidationEliminationType;
  debit_account_code: string;
  credit_account_code: string;
  amount: string;
  explanation: string;
}

export interface ConsolidationEliminationListResponse {
  group_id: string;
  period: string;
  total_eliminations: number;
  eliminations: ConsolidationEliminationEntry[];
}

export interface ConsolidationEliminationRebuildRequest {
  group_id: string;
  period: string;
  intercompany_balance_amount?: string;
  intercompany_revenue_amount?: string;
  intercompany_cost_amount?: string;
  ending_internal_inventory_amount?: string;
  internal_gross_margin_rate?: string;
  investment_amount?: string;
  subsidiary_equity_amount?: string;
  ownership_percentage?: string;
}

export interface ConsolidatedStatementResponse {
  group_id: string;
  period: string;
  balance_sheet: BalanceSheet;
  income_statement: IncomeStatement;
  cash_flow_statement: CashFlowStatement;
  minority_interest: string;
  minority_profit: string;
  elimination_count: number;
}
