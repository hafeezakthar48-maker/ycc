export type BankTransactionDirection = "inflow" | "outflow";
export type BankMatchStatus = "unmatched" | "suggested" | "matched" | "ignored";

export interface BankStatementLineCreate {
  account_set_id: string;
  bank_account_id: string;
  transaction_date: string;
  direction: BankTransactionDirection;
  amount: string | number;
  currency: string;
  counterparty_name: string;
  summary: string;
  bank_reference: string;
}

export interface BankStatementLine extends BankStatementLineCreate {
  statement_line_id: string;
  imported_at: string;
  match_status: BankMatchStatus;
}

export interface BankStatementImportRequest {
  account_set_id: string;
  lines: BankStatementLineCreate[];
}

export interface BankStatementImportResult {
  account_set_id: string;
  imported_count: number;
  duplicate_count: number;
  lines: BankStatementLine[];
}

export interface BankMatchCandidate {
  statement_line_id: string;
  journal_entry_id: string;
  journal_line_id: string;
  direction: BankTransactionDirection;
  score: number;
  reasons: string[];
  statement_date: string;
  journal_date: string;
  statement_amount: string | number;
  journal_amount: string | number;
  currency: string;
  counterparty_name: string;
  summary: string;
}

export interface BankMatchCandidateResponse {
  account_set_id: string;
  bank_account_id: string;
  period: string;
  minimum_score: number;
  candidates: BankMatchCandidate[];
}

export interface CashJournalLine {
  entry_id: string;
  line_id: string;
  entry_date: string;
  period: string;
  source_type: string;
  source_id: string;
  account_code: string;
  account_name: string;
  direction: "debit" | "credit";
  cash_direction: BankTransactionDirection;
  currency: string;
  original_amount: string | number;
  base_amount: string | number;
  summary: string;
}

export interface BankBalanceReconciliationStatement {
  account_set_id: string;
  bank_account_id: string;
  period: string;
  bank_balance: string | number;
  book_balance: string | number;
  bank_received_not_booked: string | number;
  bank_paid_not_booked: string | number;
  book_received_not_bank: string | number;
  book_paid_not_bank: string | number;
  adjusted_bank_balance: string | number;
  adjusted_book_balance: string | number;
  unmatched_statement_count: number;
  unmatched_journal_count: number;
  unmatched_statement_lines: BankStatementLine[];
  unmatched_journal_lines: CashJournalLine[];
}
