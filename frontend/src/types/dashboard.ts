export interface MetricCard {
  key: string;
  title: string;
  value: string;
  change: string;
  status: "normal" | "warning" | "danger";
}

export interface ChartPoint {
  period: string;
  value: number;
}

export interface TrendChartSeries {
  name: string;
  data: ChartPoint[];
}

export interface MonthlyFinanceRecord {
  period: string;
  revenue: number;
  cost: number;
  sales_expense: number;
  admin_expense: number;
  rd_expense: number;
  finance_expense: number;
  total_profit: number;
  net_profit: number;
  cash: number;
  accounts_receivable: number;
  inventory: number;
  fixed_assets: number;
  total_assets: number;
  short_term_loans: number;
  accounts_payable: number;
  total_liabilities: number;
  owner_equity: number;
  operating_cash_inflow: number;
  operating_cash_outflow: number;
  operating_cash_flow_net: number;
  investing_cash_flow_net: number;
  financing_cash_flow_net: number;
  customer_collection: number;
  sales_orders: number;
  purchase_amount: number;
  inventory_turnover_days: number;
  tax_burden_rate: number;
}

export interface RiskItem {
  id: string;
  title: string;
  level: number;
  level_label: string;
  description: string;
  trigger_reason: string;
  suggested_checks: string[];
  compliance_note: string;
}

export interface DashboardOverview {
  period: string;
  company_name: string;
  metrics: MetricCard[];
  trend_series: TrendChartSeries[];
  expense_structure: ChartPoint[];
  cash_flow_series: TrendChartSeries[];
  profit_waterfall: ChartPoint[];
  risk_heatmap: number[][];
  risks: RiskItem[];
  ai_summary: string;
}

export interface ManagementReport {
  period: string;
  company_name: string;
  title: string;
  sections: Array<{ title: string; content: string }>;
}

export interface AnalyzeResponse {
  overview: DashboardOverview;
  report: ManagementReport;
}

export interface FieldMapping {
  field: string;
  label: string;
  source_header: string | null;
  required: boolean;
  matched: boolean;
  status: "matched" | "missing_required" | "missing_optional";
}

export interface ImportPreview {
  sheet_name: string;
  records: MonthlyFinanceRecord[];
  matched_fields: string[];
  field_mappings: FieldMapping[];
  warnings: string[];
}
