import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("AI财务中心接入税务核算与申报底稿面板", async () => {
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");
  const panel = await readFile(resolve("src/components/TaxAccountingPanel.tsx"), "utf8");
  const periodClosePanel = await readFile(resolve("src/components/PeriodClosePanel.tsx"), "utf8");

  assert.match(layout, /TaxAccountingPanel/);
  assert.match(panel, /tax-accounting-panel/);
  assert.match(panel, /fetchVatLedger/);
  assert.match(panel, /fetchTaxFilingWorksheet/);
  assert.match(panel, /postUnpaidVatTransfer/);
  assert.match(panel, /postSurtaxAccrual/);
  assert.match(panel, /postIncomeTaxAccrual/);
  assert.match(panel, /postTaxPayment/);
  assert.match(panel, /tax-accounting-worksheet-table/);
  assert.match(panel, /tax_surtax_accrual/);
  assert.match(periodClosePanel, /tax_surtax_accrual/);
});
