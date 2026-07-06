export type SystemRiskLevel = "low" | "medium" | "high";
export type AuditResult = "success" | "denied" | "error";

export interface PermissionItem {
  code: string;
  name: string;
  module_id: string;
  action: string;
  description: string;
  risk_level: SystemRiskLevel;
}

export interface RoleItem {
  id: string;
  name: string;
  description: string;
  permission_codes: string[];
}

export interface UserItem {
  id: string;
  name: string;
  department: string;
  role_ids: string[];
  active: boolean;
}

export interface AuditLogEntry {
  id: string;
  actor_id: string;
  module_id: string;
  event: string;
  target_id: string;
  result: AuditResult;
  metadata: Record<string, string | number | boolean | null>;
  created_at: string;
}

export interface PermissionListResponse {
  permissions: PermissionItem[];
}

export interface RoleListResponse {
  roles: RoleItem[];
}

export interface UserListResponse {
  users: UserItem[];
}

export interface AuditLogListResponse {
  logs: AuditLogEntry[];
}
