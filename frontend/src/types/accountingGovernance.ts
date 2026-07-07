export type IntegrityStatus = "pass" | "fail" | "warning";
export type MigrationItemStatus = "ready" | "already_migrated" | "blocked";
export type GoLiveGateStatus = "pass" | "warning" | "blocked";

export interface AccountingIntegrityCheck {
  check_code: string;
  check_name: string;
  status: IntegrityStatus;
  severity: "blocking" | "warning" | "info";
  message: string;
  affected_count: number;
  evidence: string[];
}

export interface AccountingIntegrityReport {
  account_set_id: string;
  period: string;
  overall_status: IntegrityStatus;
  generated_at: string;
  checks: AccountingIntegrityCheck[];
}

export interface AccountingMigrationItem {
  voucher_id: string;
  voucher_number: string;
  voucher_date: string;
  summary: string;
  status: MigrationItemStatus;
  reason_code: string | null;
  reason: string;
  debit_total: string;
  credit_total: string;
  difference: string;
  formal_journal_entry_id: string | null;
}

export interface AccountingMigrationPreview {
  account_set_id: string;
  period: string;
  mode: "dry_run";
  actor_id: string;
  migration_type: "mvp_voucher_to_formal_journal";
  generated_at: string;
  total_count: number;
  ready_count: number;
  migrated_count: number;
  blocked_count: number;
  proposed_entry_count: number;
  blockers: string[];
  warnings: string[];
  items: AccountingMigrationItem[];
}

export interface AccountingBackupManifest {
  backup_manifest_id: string;
  account_set_id: string;
  period: string;
  actor_id: string;
  created_at: string;
  datasets: string[];
  dataset_row_counts: Record<string, number>;
  dataset_checksums: Record<string, string>;
}

export interface RestoreRehearsalResult {
  restore_rehearsal_id: string;
  backup_manifest_id: string;
  account_set_id: string;
  period: string;
  actor_id: string;
  target_database_path: string;
  started_at: string;
  completed_at: string;
  status: "passed" | "failed";
  row_counts: Record<string, number>;
  integrity_status: IntegrityStatus;
  messages: string[];
}

export interface FormalAccountingPermissionMatrix {
  required_permissions: string[];
  available_permissions: string[];
  missing_permissions: string[];
  critical_missing_permissions: string[];
  role_coverage: Record<string, string[]>;
  segregation_rules: string[];
}

export interface GoLiveGateCheck {
  gate_code: string;
  gate_name: string;
  status: GoLiveGateStatus;
  message: string;
}

export interface FormalAccountingGoLiveGate {
  account_set_id: string;
  period: string;
  status: GoLiveGateStatus;
  generated_at: string;
  checks: GoLiveGateCheck[];
  blockers: string[];
  warnings: string[];
  regression_results: Record<string, string>;
}

export interface AccountingGovernanceScopeRequest {
  account_set_id: string;
  period: string;
  actor_id?: string;
}

export interface AccountingMigrationApplyRequest extends AccountingGovernanceScopeRequest {
  backup_manifest_id: string;
}

export interface RestoreRehearsalRequest {
  backup_manifest_id: string;
  target_database_path: string;
  actor_id?: string;
}
