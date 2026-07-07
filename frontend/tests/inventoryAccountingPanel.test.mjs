import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("AI财务中心接入存货正式核算面板", async () => {
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");
  const panel = await readFile(resolve("src/components/InventoryAccountingPanel.tsx"), "utf8");

  assert.match(layout, /InventoryAccountingPanel/);
  assert.match(panel, /inventory-accounting-panel/);
  assert.match(panel, /fetchInventoryAccountingBalances/);
  assert.match(panel, /postInventoryPurchaseReceipt/);
  assert.match(panel, /postInventorySalesIssue/);
  assert.match(panel, /recordInventoryImpairment/);
  assert.match(panel, /recordInventoryCountVariance/);
  assert.match(panel, /inventory-accounting-balance-table/);
  assert.match(panel, /inventory_cost_rollforward/);
});
