export type MoneyValue = string | number;

export interface FinancialStatementGenerateRequest {
  period: string;
  account_set_id?: string;
  operator?: string;
  mapping_set_id?: string | null;
  include_trace?: boolean;
}

export interface StatementLineItem {
  code: string;
  name: string;
  amount: MoneyValue;
  formula: string;
}

export interface BalanceSheet {
  title: string;
  period: string;
  items: StatementLineItem[];
  total_assets: MoneyValue;
  total_liabilities: MoneyValue;
  total_equity: MoneyValue;
  total_liabilities_and_equity: MoneyValue;
  balanced: boolean;
}

export interface IncomeStatement {
  title: string;
  period: string;
  items: StatementLineItem[];
  total_revenue: MoneyValue;
  total_cost: MoneyValue;
  total_expense: MoneyValue;
  total_profit: MoneyValue;
  net_profit: MoneyValue;
}

export interface CashFlowStatement {
  title: string;
  period: string;
  items: StatementLineItem[];
  operating_cash_flow_net: MoneyValue;
  investing_cash_flow_net: MoneyValue;
  financing_cash_flow_net: MoneyValue;
  net_cash_flow: MoneyValue;
}

export interface EquityStatement {
  title: string;
  period: string;
  items: StatementLineItem[];
  opening_equity: MoneyValue;
  current_period_profit: MoneyValue;
  closing_equity: MoneyValue;
}

export interface ManagementStatementSummary {
  title: string;
  key_metrics: Record<string, string>;
  highlights: string[];
  risks: string[];
}

export interface StatementLineTrace {
  line_code: string;
  rule_id: string;
  source_type: string;
  source_account_codes: string[];
  cash_flow_item_codes: string[];
  formula: string;
  amount: MoneyValue;
  warnings: string[];
}

export interface StatementValidationItem {
  validation_code: string;
  validation_name: string;
  status: "passed" | "failed" | "warning";
  message: string;
  expected_amount?: MoneyValue | null;
  actual_amount?: MoneyValue | null;
}

export interface FinancialStatementGenerationSummary {
  account_set_id: string;
  period: string;
  source: string;
  reviewed_voucher_count: number;
  asset_liability_balanced: boolean;
  generated_statement_count: number;
  base_currency: string;
  foreign_currency_line_count: number;
}

export interface FinancialStatementBundle {
  account_set_id: string;
  period: string;
  company_name: string;
  source: string;
  mapping_set_id: string;
  trace_items: StatementLineTrace[];
  validation_items: StatementValidationItem[];
  summary: FinancialStatementGenerationSummary;
  balance_sheet: BalanceSheet;
  income_statement: IncomeStatement;
  cash_flow_statement: CashFlowStatement;
  equity_statement: EquityStatement;
  management_summary: ManagementStatementSummary;
}
