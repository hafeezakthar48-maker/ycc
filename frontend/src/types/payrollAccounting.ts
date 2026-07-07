import type { JournalEntryRecord } from "./accounting";
import type { MoneyValue } from "./payroll";

export type PayrollAccountingStatus = "calculated" | "accrued" | "paid" | "reversed";
export type PayrollLiabilityPaymentStatus = "pending" | "remitted";

export interface PayrollAccountingBatch {
  account_set_id: string;
  period: string;
  payroll_batch_id: string;
  gross_salary: MoneyValue;
  employee_social_security: MoneyValue;
  employee_housing_fund: MoneyValue;
  individual_income_tax: MoneyValue;
  net_salary: MoneyValue;
  employer_social_security: MoneyValue;
  employer_housing_fund: MoneyValue;
  status: PayrollAccountingStatus;
  accrual_journal_entry_id: string | null;
  payment_journal_entry_id: string | null;
  liability_payment_status: PayrollLiabilityPaymentStatus;
  liability_payment_journal_entry_id: string | null;
}

export interface PayrollAccountingBatchListResponse {
  account_set_id: string;
  period: string;
  total: number;
  batches: PayrollAccountingBatch[];
}

export interface PayrollAccountingPostRequest {
  account_set_id: string;
  period: string;
  payroll_batch_id: string;
}

export interface PayrollPaymentPostRequest extends PayrollAccountingPostRequest {
  bank_account_code: string;
}

export type PayrollLiabilityPaymentPostRequest = PayrollPaymentPostRequest;
export type PayrollAccountingEntryResponse = JournalEntryRecord;
