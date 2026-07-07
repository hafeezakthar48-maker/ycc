import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("AI财务中心接入正式核算上线治理面板", async () => {
  const panel = await readFile(resolve("src/components/AccountingGovernancePanel.tsx"), "utf8");
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");
  const systemAdminPanel = await readFile(resolve("src/components/SystemAdminPanel.tsx"), "utf8");

  assert.match(panel, /accounting-governance-panel/);
  assert.match(panel, /fetchAccountingIntegrityChecks/);
  assert.match(panel, /previewAccountingMigration/);
  assert.match(panel, /createAccountingBackup/);
  assert.match(panel, /rehearseAccountingRestore/);
  assert.match(panel, /fetchAccountingGoLiveGate/);
  assert.match(panel, /accounting_migration.apply/);
  assert.match(layout, /AccountingGovernancePanel/);
  assert.match(systemAdminPanel, /accounting_governance\.read/);
});
