import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("AI财务中心接入固定资产台账面板", async () => {
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");
  const panel = await readFile(resolve("src/components/FixedAssetPanel.tsx"), "utf8");

  assert.match(layout, /FixedAssetPanel/);
  assert.match(panel, /fixed-asset-panel/);
  assert.match(panel, /fetchFixedAssets/);
  assert.match(panel, /createFixedAsset/);
  assert.match(panel, /runMonthlyDepreciation/);
  assert.match(panel, /inventoryFixedAsset/);
  assert.match(panel, /disposeFixedAsset/);
  assert.match(panel, /sellFixedAsset/);
  assert.match(panel, /fixed-asset-summary-grid/);
  assert.match(panel, /fixed-asset-form/);
});
