import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("AI财务中心接入期间结账操作面板", async () => {
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");
  const panel = await readFile(resolve("src/components/PeriodClosePanel.tsx"), "utf8");
  const styles = await readFile(resolve("src/styles.css"), "utf8");

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
  assert.match(panel, /from "antd"/);
  for (const component of ["Alert", "Button", "Card", "Checkbox", "Input", "Segmented", "Statistic", "Table", "Tag"]) {
    assert.ok(panel.includes(component), `期间结账工作台缺少 Ant Design 组件：${component}`);
  }
  for (const label of [
    "期间结账工作台",
    "结账控制",
    "结账动作",
    "检查清单",
    "生成结果",
    "阻断项",
    "关闭期间",
    "重开期间",
    "执行检查",
    "生成期末分录"
  ]) {
    assert.ok(panel.includes(label), `期间结账工作台缺少文案：${label}`);
  }
  assert.match(panel, /scroll=\{\{ x:/, "结账生成结果需要表内横向滚动");
  assert.doesNotMatch(panel, /<table/, "期间结账工作台不应继续使用原生 table");
  for (const className of [
    "period-close-workbench",
    "period-close-toolbar",
    "period-close-summary-grid",
    "period-close-layout",
    "period-close-result-table"
  ]) {
    assert.ok(styles.includes(className), `缺少期间结账工作台样式：${className}`);
  }
  assert.match(styles, /\.period-close-result-table\s*\{[\s\S]*overflow-x: hidden/, "结账结果表外层需要裁剪内部宽表，避免页面级横向溢出");
  assert.match(styles, /\.period-close-result-table \.ant-table-content[\s\S]*overflow-x: auto/, "结账结果表内容层需要保留局部横向滚动");
});
