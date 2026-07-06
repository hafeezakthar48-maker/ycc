export type ArchiveStatus = "draft" | "indexed" | "archived" | "locked";
export type ArchiveStorageStatus = "metadata_only" | "stored";
export type ArchiveOcrStatus = "not_required" | "text_parsed" | "engine_required" | "failed";
export type ArchiveVerificationStatus = "not_required" | "pending_external" | "verified" | "failed";
export type ArchiveCaseType = "voucher" | "ledger" | "statement" | "mixed";

export interface ArchiveDocument {
  archive_document_id: string;
  account_set_id: string;
  period: string;
  source_type: string;
  source_id: string;
  document_type: string;
  filename: string;
  content_type: string;
  size: number;
  sha256_hash: string;
  storage_status: ArchiveStorageStatus;
  storage_uri?: string | null;
  archive_status: ArchiveStatus;
  ocr_status: ArchiveOcrStatus;
  verification_status: ArchiveVerificationStatus;
  retention_years: number;
  extracted_text?: string;
  uploaded_by: string;
  created_at: string;
}

export interface ArchiveDocumentListResponse {
  total: number;
  documents: ArchiveDocument[];
}

export interface ArchiveCaseCreateRequest {
  account_set_id: string;
  period: string;
  case_type: ArchiveCaseType;
  title: string;
  document_ids: string[];
  created_by: string;
}

export interface ArchiveCase {
  archive_case_id: string;
  account_set_id: string;
  period: string;
  case_type: ArchiveCaseType;
  title: string;
  document_ids: string[];
  document_count: number;
  archive_status: ArchiveStatus;
  retention_years: number;
  created_by: string;
  created_at: string;
}

export interface ArchivePackageDownload {
  blob: Blob;
  filename: string;
}
