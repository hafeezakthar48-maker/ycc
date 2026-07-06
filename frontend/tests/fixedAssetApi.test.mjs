import assert from "node:assert/strict";
import test from "node:test";

import {
  createFixedAsset,
  disposeFixedAsset,
  fetchFixedAssets,
  inventoryFixedAsset,
  runMonthlyDepreciation,
  sellFixedAsset
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

test("固定资产 API helper 支持台账读取、新增和月折旧", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/fixed-assets?account_set_id=default": {
      account_set_id: "default",
      summary: { asset_count: 1, active_count: 1 },
      assets: []
    },
    "http://api.local/api/v1/fixed-assets": {
      id: "fixed-asset-1",
      asset_code: "FA-202601-0001",
      name: "自动贴标机"
    },
    "http://api.local/api/v1/fixed-assets/depreciation/run": {
      account_set_id: "default",
      period: "2026-06",
      depreciated_count: 1,
      total_depreciation: "1800.00",
      assets: []
    }
  });

  const list = await fetchFixedAssets("default", "http://api.local", fetcher);
  const created = await createFixedAsset(
    {
      account_set_id: "default",
      name: "自动贴标机",
      category: "生产设备",
      acquisition_date: "2026-01-15",
      original_cost: 120000,
      salvage_value: 12000,
      useful_life_months: 60,
      location: "一号仓",
      custodian: "设备管理员"
    },
    "http://api.local",
    fetcher
  );
  const depreciation = await runMonthlyDepreciation(
    { account_set_id: "default", period: "2026-06", operator: "财务主管" },
    "http://api.local",
    fetcher
  );

  assert.equal(list.summary.asset_count, 1);
  assert.equal(created.asset_code, "FA-202601-0001");
  assert.equal(depreciation.depreciated_count, 1);
  assert.deepEqual(fetcher.calls.map((call) => call.url), [
    "http://api.local/api/v1/fixed-assets?account_set_id=default",
    "http://api.local/api/v1/fixed-assets",
    "http://api.local/api/v1/fixed-assets/depreciation/run"
  ]);
  assert.equal(fetcher.calls[1].init.method, "POST");
  assert.equal(fetcher.calls[2].init.method, "POST");
  assert.ok(fetcher.calls.every((call) => call.init.headers["X-Actor-Id"] === "u-finance-manager"));
});

test("固定资产 API helper 支持盘点、报废和出售", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/fixed-assets/fixed-asset-1/inventory": {
      id: "fixed-asset-1",
      inventory_status: "checked",
      last_inventory_by: "盘点员"
    },
    "http://api.local/api/v1/fixed-assets/fixed-asset-1/dispose": {
      id: "fixed-asset-1",
      status: "disposed"
    },
    "http://api.local/api/v1/fixed-assets/fixed-asset-2/sell": {
      id: "fixed-asset-2",
      status: "sold",
      sale_gain_or_loss: "-2000.00"
    }
  });

  const inventory = await inventoryFixedAsset(
    "fixed-asset-1",
    {
      inventory_date: "2026-06-30",
      location: "二号仓",
      custodian: "资产专员",
      condition: "正常",
      operator: "盘点员",
      note: "已贴标签"
    },
    "http://api.local",
    fetcher
  );
  const disposed = await disposeFixedAsset(
    "fixed-asset-1",
    { disposal_date: "2026-06-30", reason: "损坏报废", operator: "财务主管" },
    "http://api.local",
    fetcher
  );
  const sold = await sellFixedAsset(
    "fixed-asset-2",
    { sale_date: "2026-06-30", sale_amount: 118000, reason: "更新换代", operator: "财务主管" },
    "http://api.local",
    fetcher
  );

  assert.equal(inventory.inventory_status, "checked");
  assert.equal(disposed.status, "disposed");
  assert.equal(sold.status, "sold");
  assert.deepEqual(fetcher.calls.map((call) => call.url), [
    "http://api.local/api/v1/fixed-assets/fixed-asset-1/inventory",
    "http://api.local/api/v1/fixed-assets/fixed-asset-1/dispose",
    "http://api.local/api/v1/fixed-assets/fixed-asset-2/sell"
  ]);
  assert.ok(fetcher.calls.every((call) => call.init.method === "POST"));
});
