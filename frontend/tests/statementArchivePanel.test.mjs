import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("报表归档面板接入快照、锁定和导出动作", async () => {
  const panel = await readFile(resolve("src/components/StatementArchivePanel.tsx"), "utf8");
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");
  const styles = await readFile(resolve("src/styles.css"), "utf8");

  assert.match(panel, /statement-archive-panel/);
  assert.match(panel, /createStatementSnapshot/);
  assert.match(panel, /listStatementSnapshots/);
  assert.match(panel, /lockStatementSnapshot/);
  assert.match(panel, /exportStatementSnapshot/);
  assert.match(panel, /from "antd"/);
  for (const component of ["Alert", "Button", "Card", "Statistic", "Table", "Tabs", "Tag"]) {
    assert.ok(panel.includes(component), `报表归档工作台缺少 Ant Design 组件：${component}`);
  }
  for (const label of [
    "归档与正式交付工作台",
    "快照版本",
    "锁定状态",
    "审计信息",
    "哈希校验",
    "归档台账",
    "正式交付",
    "生成快照",
    "锁定归档",
    "导出报表包"
  ]) {
    assert.ok(panel.includes(label), `报表归档工作台缺少文案：${label}`);
  }
  assert.match(panel, /Excel/);
  assert.match(panel, /PDF/);
  assert.match(panel, /scroll=\{\{ x:/, "报表归档台账需要表内横向滚动");
  assert.doesNotMatch(panel, /<table/, "报表归档工作台不应继续使用原生 table");
  for (const className of [
    "statement-archive-workbench",
    "statement-archive-toolbar",
    "statement-archive-summary-grid",
    "statement-archive-layout",
    "statement-archive-ledger-table"
  ]) {
    assert.ok(styles.includes(className), `缺少报表归档工作台样式：${className}`);
  }
  assert.match(styles, /\.statement-archive-ledger-table\s*\{[\s\S]*overflow-x: hidden/, "归档台账外层需要裁剪内部宽表，避免页面级横向溢出");
  assert.match(styles, /\.statement-archive-ledger-table \.ant-table-content[\s\S]*overflow-x: auto/, "归档台账内容层需要保留局部横向滚动");
  assert.match(layout, /StatementArchivePanel/);
});
