import assert from "node:assert/strict";
import test from "node:test";

import {
  fetchAuditLogs,
  fetchPermissions,
  fetchRoles,
  fetchUsers
} from "../src/services/systemAdminApi.ts";

function createFetcher(routes) {
  const calls = [];
  const fetcher = async (url) => {
    calls.push(url);
    const path = new URL(url).pathname + new URL(url).search;
    const payload = routes[path];
    return {
      ok: Boolean(payload),
      status: payload ? 200 : 404,
      json: async () => payload ?? { detail: "not found" }
    };
  };
  fetcher.calls = calls;
  return fetcher;
}

test("fetchPermissions 读取系统权限点", async () => {
  const fetcher = createFetcher({
    "/api/v1/system/permissions": {
      permissions: [
        {
          code: "voucher.review",
          name: "审核凭证",
          module_id: "finance-center",
          action: "approve",
          description: "审核会计凭证",
          risk_level: "high"
        }
      ]
    }
  });

  const permissions = await fetchPermissions("http://api.local", fetcher);

  assert.equal(fetcher.calls[0], "http://api.local/api/v1/system/permissions");
  assert.equal(permissions[0].code, "voucher.review");
});

test("fetchRoles 和 fetchUsers 读取角色与用户", async () => {
  const fetcher = createFetcher({
    "/api/v1/system/roles": {
      roles: [
        {
          id: "finance_manager",
          name: "财务主管",
          description: "负责凭证审核",
          permission_codes: ["voucher.review"]
        }
      ]
    },
    "/api/v1/system/users": {
      users: [
        {
          id: "u-finance-manager",
          name: "财务主管",
          department: "财务部",
          role_ids: ["finance_manager"],
          active: true
        }
      ]
    }
  });

  const roles = await fetchRoles("http://api.local", fetcher);
  const users = await fetchUsers("http://api.local", fetcher);

  assert.equal(roles[0].permission_codes[0], "voucher.review");
  assert.deepEqual(users[0].role_ids, ["finance_manager"]);
});

test("fetchAuditLogs 支持模块过滤和 limit 参数", async () => {
  const fetcher = createFetcher({
    "/api/v1/system/audit-logs?module_id=finance-center&limit=5": {
      logs: [
        {
          id: "audit-000001",
          actor_id: "u-finance-manager",
          module_id: "finance-center",
          event: "voucher.review",
          target_id: "voucher-1",
          result: "success",
          metadata: {},
          created_at: "2026-07-05T00:00:00Z"
        }
      ]
    }
  });

  const logs = await fetchAuditLogs("finance-center", 5, "http://api.local", fetcher);

  assert.equal(logs[0].event, "voucher.review");
  assert.equal(fetcher.calls[0], "http://api.local/api/v1/system/audit-logs?module_id=finance-center&limit=5");
});
