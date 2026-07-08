import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const financialPanel = readFileSync(new URL("../src/components/FinancialStatementPanel.tsx", import.meta.url), "utf8");
const styles = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");

test("财务报表生成面板升级为 Ant Design 报表交付工作台", () => {
  assert.match(financialPanel, /from "antd"/);
  for (const component of ["Alert", "Button", "Card", "Progress", "Table", "Tabs", "Tag"]) {
    assert.ok(financialPanel.includes(component), `财务报表工作台缺少 ${component}`);
  }
  for (const label of [
    "报表交付工作台",
    "四表预览",
    "生成队列",
    "平衡校验",
    "取数追溯",
    "管理层摘要",
    "重新生成",
    "导出报表包",
    "归档锁定"
  ]) {
    assert.ok(financialPanel.includes(label), `财务报表工作台缺少文案：${label}`);
  }
});

test("财务报表工作台保留四表、追溯和校验能力", () => {
  for (const label of ["资产负债表", "利润表", "现金流量表", "所有者权益变动表"]) {
    assert.ok(financialPanel.includes(label), `缺少标准报表：${label}`);
  }
  assert.match(financialPanel, /trace_items/);
  assert.match(financialPanel, /validation_items/);
  assert.match(financialPanel, /scroll=\{\{ x:/, "报表明细和追溯表格需要表内横向滚动");
  assert.doesNotMatch(financialPanel, /<Space[^>]*direction=/, "Ant Design v6 中 Space 应使用 orientation，避免控制台弃用警告");
});

test("财务报表工作台具备专业 SaaS 密度和响应式样式", () => {
  for (const className of [
    "statement-delivery-workbench",
    "statement-delivery-toolbar",
    "statement-delivery-layout",
    "statement-preview-tabs",
    "statement-trace-table"
  ]) {
    assert.ok(styles.includes(className), `缺少财务报表工作台样式：${className}`);
  }
  assert.match(styles, /\.statement-delivery-card\.statement-validation-panel[\s\S]*display: block/, "取数追溯卡片需要覆盖旧网格样式，避免 Ant Design Card 被撑宽");
  assert.match(styles, /\.financial-statement-summary-grid\.ant-row[\s\S]*display: flex/, "报表指标区使用 Ant Design Row 时不能被旧 grid 样式压成窄列");
});
