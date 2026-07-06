import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("往来核算面板展示余额、账龄和应收应付切换", async () => {
  const panel = await readFile(resolve("src/components/ReceivablePayablePanel.tsx"), "utf8");
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");
  const navigation = await readFile(resolve("src/navigation/osModules.json"), "utf8");

  assert.match(panel, /receivable-payable-panel/);
  assert.match(panel, /fetchCounterpartyBalances/);
  assert.match(panel, /fetchCounterpartyAging/);
  assert.match(panel, /应收/);
  assert.match(panel, /应付/);
  assert.match(panel, /账龄/);
  assert.match(layout, /ReceivablePayablePanel/);
  assert.match(navigation, /receivable-payable-panel/);
});
