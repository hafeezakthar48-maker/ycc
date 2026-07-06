import assert from "node:assert/strict";
import test from "node:test";

import {
  fetchModuleRegistry,
  mergeModuleRegistry,
  normalizeBackendModuleStatus
} from "../src/services/moduleRegistryApi.ts";

test("fetchModuleRegistry 从后端模块清单 API 读取十二模块元数据", async () => {
  const fetchCalls = [];
  const modules = [
    {
      id: "ai-home",
      label: "AI首页",
      status: "mvp",
      api_prefixes: ["/api/v1/home"],
      capabilities: ["经营概况", "利润总览", "AI提示"],
      requires_permission: true,
      audit_events: ["home.dashboard.read"],
      rate_limit_policy: "standard-read"
    }
  ];
  const fetcher = async (url) => {
    fetchCalls.push(url);
    return {
      ok: true,
      json: async () => ({ modules })
    };
  };

  const result = await fetchModuleRegistry("http://api.local", fetcher);

  assert.deepEqual(fetchCalls, ["http://api.local/api/v1/modules"]);
  assert.deepEqual(result, modules);
});

test("mergeModuleRegistry 保留本地导航入口并合并后端治理字段", () => {
  const localModules = [
    {
      id: "ai-home",
      label: "AI首页",
      status: "MVP",
      items: [{ label: "首页总览", anchor: "ai-home" }],
      roadmap: ["经营概况", "利润"],
      nextIntegration: "接入真实经营数据"
    },
    {
      id: "open-platform",
      label: "开放平台",
      status: "规划",
      items: [{ label: "API与集成", anchor: "open-platform" }],
      roadmap: ["REST API", "Webhook"],
      nextIntegration: "生成 OpenAPI 契约"
    }
  ];
  const backendModules = [
    {
      id: "ai-home",
      label: "AI首页",
      status: "mvp",
      api_prefixes: ["/api/v1/home"],
      capabilities: ["经营概况", "利润总览", "AI提示"],
      requires_permission: true,
      audit_events: ["home.dashboard.read"],
      rate_limit_policy: "standard-read"
    },
    {
      id: "open-platform",
      label: "开放平台（API）",
      status: "planned",
      api_prefixes: ["/api/v1/platform"],
      capabilities: ["REST API", "Webhook", "OAuth2", "限流", "版本管理"],
      requires_permission: true,
      audit_events: ["platform.client.create"],
      rate_limit_policy: "tenant-quota"
    }
  ];

  const merged = mergeModuleRegistry(localModules, backendModules);

  assert.deepEqual(
    merged.map((module) => module.id),
    ["ai-home", "open-platform"]
  );
  assert.equal(merged[0].status, "MVP");
  assert.equal(merged[1].label, "开放平台（API）");
  assert.equal(merged[1].status, "规划");
  assert.deepEqual(merged[1].apiPrefixes, ["/api/v1/platform"]);
  assert.equal(merged[1].requiresPermission, true);
  assert.deepEqual(merged[1].auditEvents, ["platform.client.create"]);
  assert.equal(merged[1].rateLimitPolicy, "tenant-quota");
});

test("normalizeBackendModuleStatus 将后端状态转换为前端标签", () => {
  assert.equal(normalizeBackendModuleStatus("mvp"), "MVP");
  assert.equal(normalizeBackendModuleStatus("planned"), "规划");
});
