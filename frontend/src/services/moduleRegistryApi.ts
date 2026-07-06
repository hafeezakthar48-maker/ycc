import type {
  BackendModuleStatus,
  BackendOsModule,
  ModuleRegistryResponse,
  ModuleStatusLabel,
  NavigationOsModule
} from "../types/moduleRegistry";

const API_BASE = "http://127.0.0.1:8000";

type FetchLike = (url: string) => Promise<{
  ok: boolean;
  status?: number;
  json: () => Promise<unknown>;
}>;

export async function fetchModuleRegistry(
  apiBase = API_BASE,
  fetcher: FetchLike = fetch
): Promise<BackendOsModule[]> {
  const normalizedBase = apiBase.replace(/\/$/, "");
  const response = await fetcher(`${normalizedBase}/api/v1/modules`);
  if (!response.ok) {
    throw new Error(`模块清单加载失败：${response.status ?? "unknown"}`);
  }

  const payload = await response.json() as ModuleRegistryResponse;
  return payload.modules;
}

export function normalizeBackendModuleStatus(status: BackendModuleStatus): ModuleStatusLabel {
  return status === "mvp" ? "MVP" : "规划";
}

export function mergeModuleRegistry(
  localModules: NavigationOsModule[],
  backendModules: BackendOsModule[]
): NavigationOsModule[] {
  const backendById = new Map(backendModules.map((module) => [module.id, module]));

  return localModules.map((localModule) => {
    const backendModule = backendById.get(localModule.id);
    if (!backendModule) {
      return localModule;
    }

    return {
      ...localModule,
      label: backendModule.label,
      status: normalizeBackendModuleStatus(backendModule.status),
      apiPrefixes: backendModule.api_prefixes,
      capabilities: backendModule.capabilities,
      requiresPermission: backendModule.requires_permission,
      auditEvents: backendModule.audit_events,
      rateLimitPolicy: backendModule.rate_limit_policy
    };
  });
}
