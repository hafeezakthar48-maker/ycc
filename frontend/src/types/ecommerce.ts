export interface ECommerceProfitRequest {
  period: string;
  platform: string;
  gmv: number;
  refund_amount: number;
  product_cost: number;
  platform_commission: number;
  payment_fee: number;
  advertising_spend: number;
  logistics_cost: number;
  packaging_cost: number;
  labor_cost: number;
  other_cost: number;
  order_count: number;
  visitor_count: number;
}

export interface ECommerceMetric {
  key: string;
  title: string;
  value: string;
  status: "normal" | "warning" | "danger";
}

export interface ECommerceChartPoint {
  name: string;
  value: number;
}

export interface ECommerceRiskItem {
  id: string;
  title: string;
  level: number;
  description: string;
  suggestion: string;
}

export interface ECommerceProfitResult {
  period: string;
  platform: string;
  net_sales: number;
  gross_profit: number;
  contribution_profit: number;
  net_profit: number;
  gross_margin: number;
  net_margin: number;
  ad_spend_rate: number;
  roi: number;
  refund_rate: number;
  average_order_value: number;
  conversion_rate: number;
  metrics: ECommerceMetric[];
  cost_breakdown: ECommerceChartPoint[];
  profit_bridge: ECommerceChartPoint[];
  risks: ECommerceRiskItem[];
  suggestions: string[];
}
