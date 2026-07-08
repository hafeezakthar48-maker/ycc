import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("报表映射面板展示映射规则和校验追溯", async () => {
  const panel = await readFile(resolve("src/components/StatementMappingPanel.tsx"), "utf8");
  const financialPanel = await readFile(resolve("src/components/FinancialStatementPanel.tsx"), "utf8");
  const styles = await readFile(resolve("src/styles.css"), "utf8");

  assert.match(panel, /statement-mapping-panel/);
  assert.match(panel, /fetchDefaultStatementMappingSet/);
  assert.match(panel, /from "antd"/);
  for (const component of ["Alert", "Button", "Card", "Input", "Statistic", "Table", "Tabs", "Tag"]) {
    assert.ok(panel.includes(component), `报表映射工作台缺少 Ant Design 组件：${component}`);
  }
  for (const label of [
    "报表口径映射工作台",
    "映射集概览",
    "四表映射",
    "规则来源",
    "校验追溯入口",
    "启用规则",
    "重新读取",
    "导出映射",
    "查看校验"
  ]) {
    assert.ok(panel.includes(label), `报表映射工作台缺少文案：${label}`);
  }
  assert.match(panel, /资产负债表/);
  assert.match(panel, /利润表/);
  assert.match(panel, /现金流量表/);
  assert.match(panel, /所有者权益变动表/);
  assert.match(panel, /scroll=\{\{ x:/, "报表映射规则表需要表内横向滚动");
  assert.doesNotMatch(panel, /<table/, "报表映射工作台不应继续使用原生 table");
  for (const className of [
    "statement-mapping-workbench",
    "statement-mapping-toolbar",
    "statement-mapping-summary-grid",
    "statement-mapping-layout",
    "statement-mapping-rules-table"
  ]) {
    assert.ok(styles.includes(className), `缺少报表映射工作台样式：${className}`);
  }
  assert.match(styles, /\.statement-mapping-rules-table\s*\{[\s\S]*overflow-x: hidden/, "映射规则表外层需要裁剪内部宽表，避免页面级横向溢出");
  assert.match(styles, /\.statement-mapping-rules-table \.ant-table-content[\s\S]*overflow-x: auto/, "映射规则表内容层需要保留局部横向滚动");
  assert.match(financialPanel, /trace_items/);
  assert.match(financialPanel, /validation_items/);
});
