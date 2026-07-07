import type { JournalEntryRecord } from "./accounting";

export type MoneyValue = number | string;
export type VatDirection = "input" | "output" | "input_transfer_out";

export interface VatLedgerLine {
  account_set_id: string;
  period: string;
  tax_direction: VatDirection;
  invoice_no: string;
  tax_base: MoneyValue;
  tax_amount: MoneyValue;
  counterparty_id?: string | null;
  source_journal_entry_id: string;
}

export interface VatLedgerLineListResponse {
  account_set_id: string;
  period: string;
  total: number;
  lines: VatLedgerLine[];
}

export interface TaxFilingWorksheet {
  account_set_id: string;
  period: string;
  output_vat: MoneyValue;
  input_vat: MoneyValue;
  input_transfer_out: MoneyValue;
  vat_payable: MoneyValue;
  surtax_payable: MoneyValue;
  income_tax_payable: MoneyValue;
}

export interface TaxAmountPostRequest {
  account_set_id: string;
  period: string;
  amount: MoneyValue;
}

export interface SurtaxAccrualRequest {
  account_set_id: string;
  period: string;
  vat_payable: MoneyValue;
  urban_maintenance_rate?: MoneyValue;
  education_rate?: MoneyValue;
  local_education_rate?: MoneyValue;
}

export interface TaxPaymentPostRequest {
  account_set_id: string;
  period: string;
  tax_account_code: string;
  amount: MoneyValue;
  bank_account_code: string;
}

export type TaxAccountingEntryResponse = JournalEntryRecord;
