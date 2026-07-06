import type { FinanceCitation } from "./financeQa";

export interface InvoiceField {
  key: string;
  label: string;
  value: string | null;
  confidence: number;
}

export interface InvoiceRiskItem {
  id: string;
  title: string;
  level: number;
  description: string;
  suggestion: string;
}

export interface InvoiceOcrResponse {
  engine_status: "text_parsed" | "missing" | string;
  invoice_type: string | null;
  fields: InvoiceField[];
  risks: InvoiceRiskItem[];
  warnings: string[];
  citations: FinanceCitation[];
}
