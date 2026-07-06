import type { FinanceCitation } from "./financeQa";

export interface AuditVoucherLine {
  account_code: string;
  account_name: string;
  direction: string;
  amount: number;
  explanation: string;
}

export interface AuditRequest {
  audit_subject: string;
  voucher_date: string;
  summary: string;
  counterparty: string;
  invoice_number: string;
  amount: number;
  tax_amount: number;
  total_amount_with_tax: number;
  lines: AuditVoucherLine[];
}

export interface AuditCheck {
  id: string;
  title: string;
  status: "pass" | "warn" | "fail" | string;
  evidence: string;
}

export interface AuditFinding {
  id: string;
  title: string;
  category: string;
  severity: number;
  description: string;
  evidence: string;
  suggestion: string;
}

export interface AuditResponse {
  rating: string;
  score: number;
  checks: AuditCheck[];
  findings: AuditFinding[];
  suggestions: string[];
  citations: FinanceCitation[];
  requires_human_review: boolean;
}
