import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("AI财务中心接入工资管理面板", async () => {
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");
  const panel = await readFile(resolve("src/components/PayrollPanel.tsx"), "utf8");

  assert.match(layout, /PayrollPanel/);
  assert.match(panel, /payroll-panel/);
  assert.match(panel, /calculatePayroll/);
  assert.match(panel, /payroll-summary-grid/);
  assert.match(panel, /payroll-employee-table/);
  assert.match(panel, /payroll-department-table/);
  assert.match(panel, /工资计算/);
  assert.match(panel, /部门分析/);
});
