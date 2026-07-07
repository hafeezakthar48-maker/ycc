import type { JournalEntryRecord } from "./accounting";

export type MoneyValue = number | string;

export type ScheduleType = "prepaid_amortization" | "accrued_expense" | "deferred_revenue" | "loan_interest";
export type ScheduleStatus = "active" | "paused" | "completed" | "terminated";

export interface AccountingScheduleCreateRequest {
  account_set_id: string;
  schedule_code: string;
  schedule_type: ScheduleType;
  start_period: string;
  end_period: string;
  total_amount: MoneyValue;
  debit_account_code: string;
  credit_account_code: string;
  department_id?: string | null;
  project_id?: string | null;
}

export interface AccountingSchedule extends AccountingScheduleCreateRequest {
  status: ScheduleStatus;
  posted_periods: string[];
}

export interface LoanSchedule {
  account_set_id: string;
  loan_code: string;
  principal: MoneyValue;
  annual_rate: MoneyValue;
  start_period: string;
  end_period: string;
  loan_account_code: string;
  interest_expense_account_code: string;
  interest_payable_account_code: string;
  status: ScheduleStatus;
  interest_posted_periods: string[];
}

export interface AccrualAmortizationScheduleListResponse {
  account_set_id: string;
  total_schedules: number;
  total_loans: number;
  schedules: AccountingSchedule[];
  loan_schedules: LoanSchedule[];
}

export interface SchedulePostRequest {
  account_set_id: string;
  period: string;
}

export interface LoanInterestPostRequest {
  account_set_id: string;
  loan_code: string;
  period: string;
  principal: MoneyValue;
  annual_rate: MoneyValue;
  start_period: string;
  end_period: string;
  loan_account_code?: string;
  interest_expense_account_code?: string;
  interest_payable_account_code?: string;
}

export type AccrualAmortizationEntryResponse = JournalEntryRecord;
