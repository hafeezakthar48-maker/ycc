import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("会计档案面板展示文档、案卷和下载入口", async () => {
  const panel = await readFile(resolve("src/components/AccountingArchivePanel.tsx"), "utf8");
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");
  const voucherPanel = await readFile(resolve("src/components/VoucherCenterPanel.tsx"), "utf8");

  assert.match(panel, /accounting-archive-panel/);
  assert.match(panel, /fetchAccountingArchiveDocuments/);
  assert.match(panel, /createAccountingArchiveCase/);
  assert.match(panel, /downloadAccountingArchivePackage/);
  assert.match(panel, /sha256_hash/);
  assert.match(panel, /verification_status/);
  assert.match(layout, /AccountingArchivePanel/);
  assert.match(voucherPanel, /archive_document_id/);
  assert.match(voucherPanel, /sha256_hash/);
  assert.match(voucherPanel, /storage_status/);
});
