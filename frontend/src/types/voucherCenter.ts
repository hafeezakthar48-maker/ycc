import type { AuditResponse } from "./audit";

export interface VoucherCenterLine {
  account_code: string;
  account_name: string;
  direction: string;
  amount: number;
  explanation: string;
}

export interface VoucherCenterCreateRequest {
  account_set_id?: string;
  voucher_date: string;
  summary: string;
  counterparty: string;
  invoice_number: string;
  amount: number;
  tax_amount: number;
  total_amount_with_tax: number;
  lines: VoucherCenterLine[];
}

export interface VoucherAttachment {
  id: string;
  filename: string;
  content_type: string;
  size: number;
  ocr_status: string;
}

export interface VoucherCenterRecord extends VoucherCenterCreateRequest {
  id: string;
  voucher_number: string;
  status: "draft" | "reviewed" | string;
  reviewed_by: string | null;
  posting_status: "unposted" | "posted" | string;
  posted_by: string | null;
  posted_at: string | null;
  journal_entry_id: string | null;
  journal_reversal_entry_id: string | null;
  audit_result: AuditResponse | null;
  attachments: VoucherAttachment[];
}

export interface VoucherCenterListResponse {
  total: number;
  vouchers: VoucherCenterRecord[];
}

export interface VoucherCenterImportResponse {
  imported_count: number;
  vouchers: VoucherCenterRecord[];
}
