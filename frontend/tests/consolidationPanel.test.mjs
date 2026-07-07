import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("AI财务中心接入合并报表与抵销工作底稿面板", async () => {
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");
  const panel = await readFile(resolve("src/components/ConsolidationPanel.tsx"), "utf8");

  assert.match(layout, /ConsolidationPanel/);
  assert.match(panel, /consolidation-panel/);
  assert.match(panel, /fetchConsolidationGroups/);
  assert.match(panel, /createConsolidationGroup/);
  assert.match(panel, /fetchConsolidationReportingPackage/);
  assert.match(panel, /rebuildConsolidationEliminations/);
  assert.match(panel, /fetchConsolidationEliminations/);
  assert.match(panel, /fetchConsolidatedStatements/);
  assert.match(panel, /consolidation-scope-table/);
  assert.match(panel, /consolidation-elimination-table/);
  assert.match(panel, /consolidation-statement-table/);
  assert.match(panel, /少数股东权益/);
});
