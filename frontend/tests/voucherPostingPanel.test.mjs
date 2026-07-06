import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("凭证中心接入过账和反过账操作", async () => {
  const api = await readFile(resolve("src/services/dashboardApi.ts"), "utf8");
  const types = await readFile(resolve("src/types/voucherCenter.ts"), "utf8");
  const panel = await readFile(resolve("src/components/VoucherCenterPanel.tsx"), "utf8");

  assert.match(api, /postVoucherCenterRecord/);
  assert.match(api, /unpostVoucherCenterRecord/);
  assert.match(api, /\/post/);
  assert.match(api, /\/unpost/);
  assert.match(types, /posting_status/);
  assert.match(types, /posted_by/);
  assert.match(types, /posted_at/);
  assert.match(types, /journal_entry_id/);
  assert.match(types, /journal_reversal_entry_id/);
  assert.match(types, /archive_document_id/);
  assert.match(types, /sha256_hash/);
  assert.match(types, /storage_status/);
  assert.match(panel, /handlePost/);
  assert.match(panel, /handleUnpost/);
  assert.match(panel, /posting_status/);
  assert.match(panel, /formalJournalLabel/);
  assert.match(panel, /archive_document_id/);
  assert.match(panel, /sha256_hash/);
  assert.match(panel, /storage_status/);
});
