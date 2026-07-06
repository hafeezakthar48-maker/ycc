import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("AI财务中心接入财务报表生成面板", async () => {
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");
  const panel = await readFile(resolve("src/components/FinancialStatementPanel.tsx"), "utf8");

  assert.match(layout, /FinancialStatementPanel/);
  assert.match(panel, /financial-statements-panel/);
  assert.match(panel, /generateFinancialStatements/);
  assert.match(panel, /financial-statement-summary-grid/);
  assert.match(panel, /statement-table/);
  assert.match(panel, /资产负债表/);
  assert.match(panel, /利润表/);
  assert.match(panel, /现金流量表/);
  assert.match(panel, /所有者权益变动表/);
  assert.match(panel, /formal_journal_entries/);
  assert.match(panel, /正式分录/);
  assert.match(panel, /本位币/);
  assert.match(panel, /外币分录/);
  assert.match(panel, /foreign_currency_line_count/);
});
