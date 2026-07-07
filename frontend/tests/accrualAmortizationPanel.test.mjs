import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("AI财务中心接入预提摊销与融资利息面板", async () => {
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");
  const panel = await readFile(resolve("src/components/AccrualAmortizationPanel.tsx"), "utf8");
  const periodClosePanel = await readFile(resolve("src/components/PeriodClosePanel.tsx"), "utf8");

  assert.match(layout, /AccrualAmortizationPanel/);
  assert.match(panel, /accrual-amortization-panel/);
  assert.match(panel, /fetchAccrualAmortizationSchedules/);
  assert.match(panel, /createAccountingSchedule/);
  assert.match(panel, /postAccountingScheduleForPeriod/);
  assert.match(panel, /postLoanInterestAccrual/);
  assert.match(panel, /accrual-amortization-schedule-table/);
  assert.match(panel, /accrual-amortization-loan-table/);
  assert.match(panel, /accrual_amortization_posting/);
  assert.match(periodClosePanel, /accrual_amortization_posting/);
});
