import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("AI财务中心接入总账、明细账和科目余额表面板", async () => {
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");
  const panel = await readFile(resolve("src/components/LedgerPanel.tsx"), "utf8");

  assert.match(layout, /LedgerPanel/);
  assert.match(panel, /fetchGeneralLedger/);
  assert.match(panel, /fetchDetailLedger/);
  assert.match(panel, /fetchAccountBalanceTable/);
  assert.match(panel, /fetchAccountingPeriods/);
  assert.match(panel, /closeAccountingPeriod/);
  assert.match(panel, /reopenAccountingPeriod/);
  assert.match(panel, /selectedAccountSetId/);
  assert.match(panel, /setSelectedAccountSetId/);
  assert.match(panel, /account-set-select/);
  assert.match(panel, /ledger-panel/);
  assert.match(panel, /period-status-strip/);
  assert.match(panel, /ledgerSourceLabel/);
  assert.match(panel, /formal_journal_entries/);
  assert.match(panel, /originalCurrencyText/);
  assert.match(panel, /original_amount/);
  assert.match(panel, /exchange_rate/);
});
