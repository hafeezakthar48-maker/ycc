import type {
  AuditLogEntry,
  AuditLogListResponse,
  PermissionItem,
  PermissionListResponse,
  RoleItem,
  RoleListResponse,
  UserItem,
  UserListResponse
} from "../types/systemAdmin";

const API_BASE = "http://127.0.0.1:8000";

type FetchLike = (url: string) => Promise<{
  ok: boolean;
  status?: number;
  json: () => Promise<unknown>;
}>;

async function requestSystemJson<T>(
  path: string,
  apiBase = API_BASE,
  fetcher: FetchLike = fetch
): Promise<T> {
  const normalizedBase = apiBase.replace(/\/$/, "");
  const response = await fetcher(`${normalizedBase}${path}`);
  if (!response.ok) {
    throw new Error(`系统管理接口请求失败：${response.status ?? "unknown"}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchPermissions(
  apiBase = API_BASE,
  fetcher: FetchLike = fetch
): Promise<PermissionItem[]> {
  const payload = await requestSystemJson<PermissionListResponse>(
    "/api/v1/system/permissions",
    apiBase,
    fetcher
  );
  return payload.permissions;
}

export async function fetchRoles(
  apiBase = API_BASE,
  fetcher: FetchLike = fetch
): Promise<RoleItem[]> {
  const payload = await requestSystemJson<RoleListResponse>(
    "/api/v1/system/roles",
    apiBase,
    fetcher
  );
  return payload.roles;
}

export async function fetchUsers(
  apiBase = API_BASE,
  fetcher: FetchLike = fetch
): Promise<UserItem[]> {
  const payload = await requestSystemJson<UserListResponse>(
    "/api/v1/system/users",
    apiBase,
    fetcher
  );
  return payload.users;
}

export async function fetchAuditLogs(
  moduleId: string | null = null,
  limit = 20,
  apiBase = API_BASE,
  fetcher: FetchLike = fetch
): Promise<AuditLogEntry[]> {
  const params = new URLSearchParams();
  if (moduleId) {
    params.set("module_id", moduleId);
  }
  params.set("limit", String(limit));
  const payload = await requestSystemJson<AuditLogListResponse>(
    `/api/v1/system/audit-logs?${params.toString()}`,
    apiBase,
    fetcher
  );
  return payload.logs;
}
