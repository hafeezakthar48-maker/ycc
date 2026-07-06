import assert from "node:assert/strict";
import test from "node:test";

import { fetchCounterpartyAging, fetchCounterpartyBalances } from "../src/services/dashboardApi.ts";

function createFetcher(payloads) {
  const calls = [];
  const fetcher = async (url, init = {}) => {
    calls.push({ url, init });
    return {
      ok: true,
      status: 200,
      json: async () => payloads[url]
    };
  };
  fetcher.calls = calls;
  return fetcher;
}

test("往来余额 API helper 请求 balances endpoint", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/receivable-payable/balances?account_set_id=default&period=2026-06&open_item_type=receivable": {
      account_set_id: "default",
      period: "2026-06",
      open_item_type: "receivable",
      total_base_balance: "0.00",
      item_count: 0,
      items: []
    }
  });

  await fetchCounterpartyBalances("default", "2026-06", "receivable", "http://api.local", fetcher);

  assert.equal(fetcher.calls[0].init.headers["X-Actor-Id"], "u-finance-manager");
});

test("往来账龄 API helper 请求 aging endpoint", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/receivable-payable/aging?account_set_id=default&period=2026-06&open_item_type=receivable&as_of_date=2026-06-30": {
      account_set_id: "default",
      period: "2026-06",
      as_of_date: "2026-06-30",
      open_item_type: "receivable",
      buckets: [],
      items: [],
      total_base_balance: "0.00"
    }
  });

  await fetchCounterpartyAging("default", "2026-06", "receivable", "2026-06-30", "http://api.local", fetcher);

  assert.equal(
    fetcher.calls[0].url,
    "http://api.local/api/v1/receivable-payable/aging?account_set_id=default&period=2026-06&open_item_type=receivable&as_of_date=2026-06-30"
  );
});
