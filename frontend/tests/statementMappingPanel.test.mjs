import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("报表映射面板展示映射规则和校验追溯", async () => {
  const panel = await readFile(resolve("src/components/StatementMappingPanel.tsx"), "utf8");
  const financialPanel = await readFile(resolve("src/components/FinancialStatementPanel.tsx"), "utf8");

  assert.match(panel, /statement-mapping-panel/);
  assert.match(panel, /fetchDefaultStatementMappingSet/);
  assert.match(panel, /资产负债表/);
  assert.match(panel, /利润表/);
  assert.match(panel, /现金流量表/);
  assert.match(panel, /所有者权益变动表/);
  assert.match(financialPanel, /trace_items/);
  assert.match(financialPanel, /validation_items/);
});
