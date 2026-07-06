export type BackendModuleStatus = "mvp" | "planned";
export type ModuleStatusLabel = "MVP" | "规划";

export interface BackendOsModule {
  id: string;
  label: string;
  status: BackendModuleStatus;
  api_prefixes: string[];
  capabilities: string[];
  requires_permission: boolean;
  audit_events: string[];
  rate_limit_policy: string;
}

export interface ModuleRegistryResponse {
  modules: BackendOsModule[];
}

export interface OsModuleItem {
  label: string;
  anchor: string;
}

export interface NavigationOsModule {
  id: string;
  label: string;
  status: ModuleStatusLabel;
  items: OsModuleItem[];
  roadmap: string[];
  nextIntegration: string;
  apiPrefixes?: string[];
  capabilities?: string[];
  requiresPermission?: boolean;
  auditEvents?: string[];
  rateLimitPolicy?: string;
}
