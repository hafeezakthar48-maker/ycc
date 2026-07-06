import assert from "node:assert/strict";
import test from "node:test";

import {
  capitalizeFixedAsset,
  disposeFixedAssetFormally,
  fetchFixedAssetAccountingCards,
  postFixedAssetDepreciation,
  recordFixedAssetImpairment
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

test("固定资产正式核算 API helper 覆盖卡片、入账、折旧、减值和处置", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/fixed-asset-accounting/cards?account_set_id=default": {
      account_set_id: "default",
      cards: [{ asset_id: "fixed-asset-1", formal_accounting_status: "capitalized" }]
    },
    "http://api.local/api/v1/fixed-asset-accounting/capitalize": {
      id: "je-capitalize",
      source_type: "fixed_asset_capitalization"
    },
    "http://api.local/api/v1/fixed-asset-accounting/depreciation": {
      account_set_id: "default",
      period: "2026-06",
      status: "generated",
      depreciated_count: 1,
      total_depreciation: "1800.00",
      entries: []
    },
    "http://api.local/api/v1/fixed-asset-accounting/impairment": {
      id: "je-impairment",
      source_type: "fixed_asset_impairment"
    },
    "http://api.local/api/v1/fixed-asset-accounting/disposal": {
      account_set_id: "default",
      period: "2026-07",
      asset_id: "fixed-asset-1",
      asset_code: "FA-202601-0001",
      asset_status: "sold",
      clearing_account_code: "1606",
      disposal_gain_or_loss: "-15200.00",
      entries: []
    }
  });

  const cards = await fetchFixedAssetAccountingCards("default", "http://api.local", fetcher);
  const capitalization = await capitalizeFixedAsset(
    { account_set_id: "default", asset_id: "fixed-asset-1", period: "2026-01", credit_account_code: "2202" },
    "http://api.local",
    fetcher
  );
  const depreciation = await postFixedAssetDepreciation(
    { account_set_id: "default", period: "2026-06" },
    "http://api.local",
    fetcher
  );
  const impairment = await recordFixedAssetImpairment(
    { account_set_id: "default", asset_id: "fixed-asset-1", period: "2026-06", amount: 3000 },
    "http://api.local",
    fetcher
  );
  const disposal = await disposeFixedAssetFormally(
    { account_set_id: "default", asset_id: "fixed-asset-1", period: "2026-07", proceeds_amount: 100000 },
    "http://api.local",
    fetcher
  );

  assert.equal(cards.cards[0].formal_accounting_status, "capitalized");
  assert.equal(capitalization.source_type, "fixed_asset_capitalization");
  assert.equal(depreciation.depreciated_count, 1);
  assert.equal(impairment.source_type, "fixed_asset_impairment");
  assert.equal(disposal.clearing_account_code, "1606");
  assert.deepEqual(fetcher.calls.map((call) => call.url), [
    "http://api.local/api/v1/fixed-asset-accounting/cards?account_set_id=default",
    "http://api.local/api/v1/fixed-asset-accounting/capitalize",
    "http://api.local/api/v1/fixed-asset-accounting/depreciation",
    "http://api.local/api/v1/fixed-asset-accounting/impairment",
    "http://api.local/api/v1/fixed-asset-accounting/disposal"
  ]);
  assert.ok(fetcher.calls.every((call) => call.init.headers["X-Actor-Id"] === "u-finance-manager"));
});
