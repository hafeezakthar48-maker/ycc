import type { FinanceCitation } from "./financeQa";

export interface VoucherDraftRequest {
  business_type: string;
  voucher_date: string;
  counterparty: string;
  amount: number;
  tax_amount: number;
  total_amount_with_tax: number;
  payment_status: string;
  memo: string;
}

export interface VoucherLine {
  account_code: string;
  account_name: string;
  direction: "借" | "贷" | string;
  amount: number | string;
  explanation: string;
}

export interface VoucherRiskItem {
  id: string;
  title: string;
  level: number;
  description: string;
  suggestion: string;
}

export interface VoucherDraftResponse {
  scenario_label: string;
  voucher_date: string;
  summary: string;
  lines: VoucherLine[];
  debit_total: number | string;
  credit_total: number | string;
  balanced: boolean;
  risks: VoucherRiskItem[];
  suggestions: string[];
  citations: FinanceCitation[];
  requires_human_review: boolean;
}
