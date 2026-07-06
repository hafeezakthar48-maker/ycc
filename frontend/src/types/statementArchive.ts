import type { FinancialStatementBundle } from "./financialStatement";

export type StatementArchiveStatus = "draft" | "locked" | "archived" | "demo_only";
export type StatementValidationStatus = "passed" | "warning" | "failed";
export type StatementExportFormat = "xlsx" | "pdf";

export interface StatementSnapshot {
  snapshot_id: string;
  account_set_id: string;
  period: string;
  company_name: string;
  version: number;
  mapping_set_id: string;
  source: string;
  content_hash: string;
  validation_status: StatementValidationStatus;
  archive_status: StatementArchiveStatus;
  locked: boolean;
  created_by: string;
  created_at: string;
  locked_by?: string | null;
  locked_at?: string | null;
  bundle: FinancialStatementBundle;
}

export interface StatementSnapshotListResponse {
  total: number;
  items: StatementSnapshot[];
}

export interface StatementSnapshotCreateRequest {
  period: string;
  account_set_id?: string;
  operator?: string;
  created_by?: string;
}

export interface StatementSnapshotLockRequest {
  locked_by: string;
}

export interface StatementExportDownload {
  blob: Blob;
  filename: string;
}
