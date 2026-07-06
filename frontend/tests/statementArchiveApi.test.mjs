import assert from "node:assert/strict";
import test from "node:test";

import {
  createStatementSnapshot,
  exportStatementSnapshot,
  listStatementSnapshots,
  lockStatementSnapshot
} from "../src/services/dashboardApi.ts";

function createJsonFetcher(payload) {
  const calls = [];
  const fetcher = async (url, init = {}) => {
    calls.push({ url, init });
    return {
      ok: true,
      status: 200,
      json: async () => payload
    };
  };
  fetcher.calls = calls;
  return fetcher;
}

function createBlobFetcher() {
  const calls = [];
  const fetcher = async (url, init = {}) => {
    calls.push({ url, init });
    return {
      ok: true,
      status: 200,
      blob: async () => new Blob(["xlsx"], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }),
      headers: {
        get: (name) => name.toLowerCase() === "content-disposition"
          ? 'attachment; filename="financial-statements-default-2026-06-v1.xlsx"'
          : null
      }
    };
  };
  fetcher.calls = calls;
  return fetcher;
}

test("报表归档 API helper 创建、查询和锁定快照", async () => {
  const snapshot = {
    snapshot_id: "stmt_snapshot_default_2026-06_v1",
    account_set_id: "default",
    period: "2026-06",
    company_name: "示例公司",
    version: 1,
    mapping_set_id: "stmtmap_default_default",
    source: "formal_journal_entries",
    content_hash: "hash",
    validation_status: "passed",
    archive_status: "draft",
    locked: false,
    created_by: "finance-user",
    created_at: "2026-07-06T00:00:00Z",
    bundle: {}
  };
  const createFetcher = createJsonFetcher(snapshot);

  await createStatementSnapshot(
    { period: "2026-06", account_set_id: "default", created_by: "finance-user" },
    "http://api.local",
    createFetcher
  );

  assert.equal(createFetcher.calls[0].url, "http://api.local/api/v1/financial-statements/snapshots");
  assert.equal(createFetcher.calls[0].init.method, "POST");
  assert.equal(createFetcher.calls[0].init.headers["X-Actor-Id"], "u-finance-manager");
  assert.equal(JSON.parse(createFetcher.calls[0].init.body).period, "2026-06");

  const listFetcher = createJsonFetcher({ total: 1, items: [snapshot] });
  const listResult = await listStatementSnapshots("default", "2026-06", "http://api.local", listFetcher);
  assert.equal(listResult.total, 1);
  assert.equal(
    listFetcher.calls[0].url,
    "http://api.local/api/v1/financial-statements/snapshots?account_set_id=default&period=2026-06"
  );

  const lockFetcher = createJsonFetcher({ ...snapshot, locked: true, archive_status: "archived" });
  const locked = await lockStatementSnapshot(
    "stmt_snapshot_default_2026-06_v1",
    { locked_by: "finance-manager" },
    "http://api.local",
    lockFetcher
  );
  assert.equal(locked.locked, true);
  assert.equal(
    lockFetcher.calls[0].url,
    "http://api.local/api/v1/financial-statements/snapshots/stmt_snapshot_default_2026-06_v1/lock"
  );
});

test("报表归档 API helper 导出快照文件", async () => {
  const fetcher = createBlobFetcher();

  const result = await exportStatementSnapshot(
    "stmt_snapshot_default_2026-06_v1",
    "xlsx",
    "http://api.local",
    fetcher
  );

  assert.equal(
    fetcher.calls[0].url,
    "http://api.local/api/v1/financial-statements/snapshots/stmt_snapshot_default_2026-06_v1/export/xlsx"
  );
  assert.equal(fetcher.calls[0].init.headers["X-Actor-Id"], "u-finance-manager");
  assert.equal(result.filename, "financial-statements-default-2026-06-v1.xlsx");
});
