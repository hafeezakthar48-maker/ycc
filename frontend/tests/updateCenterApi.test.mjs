import assert from "node:assert/strict";
import test from "node:test";

import {
  checkApplicationUpdateNow,
  checkUpdateCenterNow,
  fetchUpdateCenterStatus
} from "../src/services/dashboardApi.ts";

function createFetcher(routes) {
  const calls = [];
  const fetcher = async (url, init = {}) => {
    calls.push({ url, init });
    const parsed = new URL(url);
    const payload = routes[`${parsed.pathname}${parsed.search}`];
    return {
      ok: Boolean(payload),
      status: payload ? 200 : 404,
      json: async () => payload ?? { detail: "not found" }
    };
  };
  fetcher.calls = calls;
  return fetcher;
}

test("联网更新中心 API helper 读取月度自动更新状态", async () => {
  const fetcher = createFetcher({
    "/api/v1/update-center/status": {
      config: {
        provider: "codex",
        auto_update_enabled: true,
        schedule_day: 1,
        update_channel: "stable",
        manifest_url: "",
        proxy_url: null
      },
      online_status: "not_configured",
      current_policy_version: "local-bundled",
      current_policy_package_path: null,
      last_checked_at: null,
      last_successful_update_at: null,
      last_scheduled_check_at: null,
      last_scheduled_check_month: null,
      next_scheduled_check: "2026-08-01T09:00:00",
      last_error: null,
      events: []
    }
  });

  const status = await fetchUpdateCenterStatus("http://api.local", fetcher);

  assert.equal(fetcher.calls[0].url, "http://api.local/api/v1/update-center/status");
  assert.equal(status.config.provider, "codex");
  assert.equal(status.config.schedule_day, 1);
});

test("联网更新中心 API helper 支持手动检查更新", async () => {
  const fetcher = createFetcher({
    "/api/v1/update-center/check": {
      status: "not_configured",
      message: "未配置联网更新清单地址",
      current_policy_version: "local-bundled",
      checked_at: "2026-08-01T09:00:00",
      manifest_version: null
    }
  });

  const result = await checkUpdateCenterNow("http://api.local", fetcher);

  assert.equal(fetcher.calls[0].url, "http://api.local/api/v1/update-center/check");
  assert.equal(fetcher.calls[0].init.method, "POST");
  assert.equal(result.status, "not_configured");
});

test("联网更新中心 API helper 支持检查软件本体更新", async () => {
  const fetcher = createFetcher({
    "/api/v1/update-center/application/check": {
      status: "not_configured",
      message: "未配置软件本体更新清单地址",
      current_app_version: "0.1.0",
      checked_at: "2026-08-01T09:00:00",
      available_app_version: null,
      update_package_path: null,
      mandatory: false
    }
  });

  const result = await checkApplicationUpdateNow("http://api.local", fetcher);

  assert.equal(fetcher.calls[0].url, "http://api.local/api/v1/update-center/application/check");
  assert.equal(fetcher.calls[0].init.method, "POST");
  assert.equal(result.current_app_version, "0.1.0");
});
