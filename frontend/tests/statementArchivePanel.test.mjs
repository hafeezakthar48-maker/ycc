import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("报表归档面板接入快照、锁定和导出动作", async () => {
  const panel = await readFile(resolve("src/components/StatementArchivePanel.tsx"), "utf8");
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");

  assert.match(panel, /statement-archive-panel/);
  assert.match(panel, /createStatementSnapshot/);
  assert.match(panel, /listStatementSnapshots/);
  assert.match(panel, /lockStatementSnapshot/);
  assert.match(panel, /exportStatementSnapshot/);
  assert.match(panel, /Excel/);
  assert.match(panel, /PDF/);
  assert.match(layout, /StatementArchivePanel/);
});
