import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("风险预警面板接入闭环跟踪 API", async () => {
  const panel = await readFile(resolve("src/components/RiskPanel.tsx"), "utf8");
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");

  assert.match(panel, /fetchRiskClosures/);
  assert.match(panel, /assignRiskOwner/);
  assert.match(panel, /addRiskProcessRecord/);
  assert.match(panel, /addRiskReviewRecord/);
  assert.match(panel, /owner/);
  assert.match(panel, /process_records/);
  assert.match(panel, /review_records/);
  assert.match(layout, /period=\{overview\.period\}/);
});
