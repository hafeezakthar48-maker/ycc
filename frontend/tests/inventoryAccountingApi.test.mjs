import assert from "node:assert/strict";
import test from "node:test";

import {
  fetchInventoryAccountingBalances,
  postInventoryPurchaseReceipt,
  postInventorySalesIssue,
  recordInventoryCountVariance,
  recordInventoryImpairment
} from "../src/services/dashboardApi.ts";

function createFetcher(payloads) {
  const calls = [];
  const fetcher = async (url, init = {}) => {
    calls.push({ url, init });
    const payload = payloads[url];
    return {
      ok: Boolean(payload),
      status: payload ? 200 : 404,
      json: async () => payload ?? { detail: "not found" }
    };
  };
  fetcher.calls = calls;
  return fetcher;
}

test("存货正式核算 API helper 覆盖余额、入库、出库、跌价和盘点差异", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/inventory-accounting/balances?account_set_id=default": {
      account_set_id: "default",
      total_balances: 1,
      total_movements: 1,
      balances: [{ sku_id: "SKU-001", quantity: "10.0000", amount: "1000.00" }],
      movements: [{ movement_type: "purchase_receipt", source_id: "inventory_receipt:default:2026-06:SKU-001:SUP-001" }]
    },
    "http://api.local/api/v1/inventory-accounting/purchase-receipts": {
      movement_id: "im-receipt",
      movement_type: "purchase_receipt"
    },
    "http://api.local/api/v1/inventory-accounting/sales-issues": {
      journal_entry_id: "je-issue",
      cogs_account_code: "6401"
    },
    "http://api.local/api/v1/inventory-accounting/impairments": {
      id: "je-impairment",
      source_type: "inventory_impairment"
    },
    "http://api.local/api/v1/inventory-accounting/count-variances": {
      variance_type: "loss",
      journal_entry_id: "je-count"
    }
  });

  const summary = await fetchInventoryAccountingBalances("default", "http://api.local", fetcher);
  const receipt = await postInventoryPurchaseReceipt(
    {
      account_set_id: "default",
      sku_id: "SKU-001",
      warehouse_id: "WH-SH",
      period: "2026-06",
      quantity: "10",
      amount: "1000.00",
      supplier_id: "SUP-001"
    },
    "http://api.local",
    fetcher
  );
  const issue = await postInventorySalesIssue(
    { account_set_id: "default", sku_id: "SKU-001", warehouse_id: "WH-SH", period: "2026-06", quantity: "3" },
    "http://api.local",
    fetcher
  );
  const impairment = await recordInventoryImpairment(
    { account_set_id: "default", sku_id: "SKU-001", period: "2026-06", amount: "500.00" },
    "http://api.local",
    fetcher
  );
  const count = await recordInventoryCountVariance(
    {
      account_set_id: "default",
      sku_id: "SKU-001",
      warehouse_id: "WH-SH",
      period: "2026-06",
      actual_quantity: "6",
      approved_by: "controller",
      approved_at: "2026-06-30T10:00:00Z"
    },
    "http://api.local",
    fetcher
  );

  assert.equal(summary.total_balances, 1);
  assert.equal(receipt.movement_type, "purchase_receipt");
  assert.equal(issue.cogs_account_code, "6401");
  assert.equal(impairment.source_type, "inventory_impairment");
  assert.equal(count.variance_type, "loss");
  assert.deepEqual(fetcher.calls.map((call) => call.url), [
    "http://api.local/api/v1/inventory-accounting/balances?account_set_id=default",
    "http://api.local/api/v1/inventory-accounting/purchase-receipts",
    "http://api.local/api/v1/inventory-accounting/sales-issues",
    "http://api.local/api/v1/inventory-accounting/impairments",
    "http://api.local/api/v1/inventory-accounting/count-variances"
  ]);
  assert.ok(fetcher.calls.every((call) => call.init.headers["X-Actor-Id"] === "u-finance-manager"));
});
