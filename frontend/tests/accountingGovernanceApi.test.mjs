import assert from "node:assert/strict";
import test from "node:test";

import {
  createAccountingBackup,
  fetchAccountingGoLiveGate,
  fetchAccountingIntegrityChecks,
  fetchAccountingPermissionMatrix,
  previewAccountingMigration,
  rehearseAccountingRestore
} from "../src/services/dashboardApi.ts";

function createFetcher(payloads) {
  const calls = [];
  const fetcher = async (url, init = {}) => {
    calls.push({ url, init });
    return {
      ok: true,
      status: 200,
      json: async () => payloads[url] ?? payloads.default ?? {}
    };
  };
  fetcher.calls = calls;
  return fetcher;
}

test("正式核算上线治理 API helper 覆盖校验、迁移、备份、恢复和门禁", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/accounting-governance/integrity-checks?account_set_id=default&period=2026-06": {
      overall_status: "pass",
      checks: []
    },
    "http://api.local/api/v1/accounting-governance/migration-preview": {
      mode: "dry_run",
      ready_count: 0
    },
    "http://api.local/api/v1/accounting-governance/backups": {
      backup_manifest_id: "backup-default-2026-06"
    },
    "http://api.local/api/v1/accounting-governance/restore-rehearsals": {
      status: "passed"
    },
    "http://api.local/api/v1/accounting-governance/permission-matrix": {
      required_permissions: ["accounting_migration.apply"]
    },
    "http://api.local/api/v1/accounting-governance/go-live-gate?account_set_id=default&period=2026-06&backend_tests=passed&frontend_tests=passed&frontend_build=passed": {
      status: "pass"
    }
  });

  const integrity = await fetchAccountingIntegrityChecks("default", "2026-06", "http://api.local", fetcher);
  const preview = await previewAccountingMigration(
    { account_set_id: "default", period: "2026-06", actor_id: "migration-user" },
    "http://api.local",
    fetcher
  );
  const backup = await createAccountingBackup(
    { account_set_id: "default", period: "2026-06", actor_id: "backup-user" },
    "http://api.local",
    fetcher
  );
  const restore = await rehearseAccountingRestore(
    {
      backup_manifest_id: "backup-default-2026-06",
      target_database_path: "D:/tmp/formal-accounting-restore.sqlite3",
      actor_id: "restore-user"
    },
    "http://api.local",
    fetcher
  );
  const matrix = await fetchAccountingPermissionMatrix("http://api.local", fetcher);
  const gate = await fetchAccountingGoLiveGate(
    "default",
    "2026-06",
    { backend_tests: "passed", frontend_tests: "passed", frontend_build: "passed" },
    "http://api.local",
    fetcher
  );

  assert.equal(integrity.overall_status, "pass");
  assert.equal(preview.mode, "dry_run");
  assert.equal(backup.backup_manifest_id, "backup-default-2026-06");
  assert.equal(restore.status, "passed");
  assert.equal(matrix.required_permissions[0], "accounting_migration.apply");
  assert.equal(gate.status, "pass");
  assert.equal(fetcher.calls[0].init.headers["X-Actor-Id"], "u-finance-manager");
  assert.equal(fetcher.calls[1].init.method, "POST");
  assert.equal(JSON.parse(fetcher.calls[1].init.body).actor_id, "migration-user");
  assert.equal(fetcher.calls[3].url, "http://api.local/api/v1/accounting-governance/restore-rehearsals");
  assert.match(fetcher.calls.at(-1).url, /frontend_build=passed/);
});
