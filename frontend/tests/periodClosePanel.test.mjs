import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("AI财务中心接入期间结账操作面板", async () => {
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");
  const panel = await readFile(resolve("src/components/PeriodClosePanel.tsx"), "utf8");

  assert.match(layout, /PeriodClosePanel/);
  assert.match(panel, /period-close-panel/);
  assert.match(panel, /runPeriodCloseChecks/);
  assert.match(panel, /generatePeriodCloseActions/);
  assert.match(panel, /closePeriod/);
  assert.match(panel, /reopenPeriod/);
  assert.match(panel, /period-close-check-grid/);
  assert.match(panel, /profit_loss_carryforward/);
  assert.match(panel, /fx_revaluation/);
  assert.match(panel, /year_end_profit_distribution/);
});
