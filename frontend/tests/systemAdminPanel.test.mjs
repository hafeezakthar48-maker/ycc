import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("系统管理模块接入专用权限审计面板", async () => {
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");
  const panel = await readFile(resolve("src/components/SystemAdminPanel.tsx"), "utf8");

  assert.match(layout, /SystemAdminPanel/);
  assert.match(panel, /fetchPermissions/);
  assert.match(panel, /fetchRoles/);
  assert.match(panel, /fetchUsers/);
  assert.match(panel, /fetchAuditLogs/);
});
