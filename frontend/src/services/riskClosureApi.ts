import type {
  RiskAssignRequest,
  RiskClosureItem,
  RiskClosureListResponse,
  RiskClosureStatus,
  RiskProcessRecordRequest,
  RiskReviewRecordRequest
} from "../types/riskClosure";

const API_BASE = "http://127.0.0.1:8000";

type FetchLike = (url: string, init?: RequestInit) => Promise<{
  ok: boolean;
  status?: number;
  json: () => Promise<unknown>;
}>;

async function requestRiskJson<T>(
  path: string,
  init: RequestInit = {},
  apiBase = API_BASE,
  fetcher: FetchLike = fetch
): Promise<T> {
  const normalizedBase = apiBase.replace(/\/$/, "");
  const response = await fetcher(`${normalizedBase}${path}`, init);
  if (!response.ok) {
    throw new Error(`风险闭环接口请求失败：${response.status ?? "unknown"}`);
  }
  return response.json() as Promise<T>;
}

export function fetchRiskClosures(
  period: string,
  status: RiskClosureStatus | null = null,
  apiBase = API_BASE,
  fetcher: FetchLike = fetch
): Promise<RiskClosureListResponse> {
  const params = new URLSearchParams({ period });
  if (status) {
    params.set("status", status);
  }
  return requestRiskJson<RiskClosureListResponse>(
    `/api/v1/risks/closures?${params.toString()}`,
    {},
    apiBase,
    fetcher
  );
}

export function assignRiskOwner(
  riskId: string,
  request: RiskAssignRequest,
  apiBase = API_BASE,
  fetcher: FetchLike = fetch
): Promise<RiskClosureItem> {
  return postRiskClosure(riskId, "assign", request, apiBase, fetcher);
}

export function addRiskProcessRecord(
  riskId: string,
  request: RiskProcessRecordRequest,
  apiBase = API_BASE,
  fetcher: FetchLike = fetch
): Promise<RiskClosureItem> {
  return postRiskClosure(riskId, "process-records", request, apiBase, fetcher);
}

export function addRiskReviewRecord(
  riskId: string,
  request: RiskReviewRecordRequest,
  apiBase = API_BASE,
  fetcher: FetchLike = fetch
): Promise<RiskClosureItem> {
  return postRiskClosure(riskId, "review-records", request, apiBase, fetcher);
}

function postRiskClosure<TRequest extends object>(
  riskId: string,
  action: string,
  request: TRequest,
  apiBase: string,
  fetcher: FetchLike
): Promise<RiskClosureItem> {
  return requestRiskJson<RiskClosureItem>(
    `/api/v1/risks/closures/${riskId}/${action}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request)
    },
    apiBase,
    fetcher
  );
}
