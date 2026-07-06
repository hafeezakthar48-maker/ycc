import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("银行对账面板展示调节表、未达项和匹配候选", async () => {
  const panel = await readFile(resolve("src/components/BankReconciliationPanel.tsx"), "utf8");
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");

  assert.match(panel, /bank-reconciliation-panel/);
  assert.match(panel, /fetchBankReconciliationStatement/);
  assert.match(panel, /fetchBankMatchCandidates/);
  assert.match(panel, /银行余额调节表/);
  assert.match(panel, /未达账项/);
  assert.match(panel, /匹配候选/);
  assert.match(layout, /BankReconciliationPanel/);
});
