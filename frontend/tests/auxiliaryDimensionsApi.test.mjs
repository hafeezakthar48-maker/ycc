import assert from "node:assert/strict";
import test from "node:test";

import { fetchAuxiliaryDimensions, saveAuxiliaryDimension } from "../src/services/dashboardApi.ts";

test("fetchAuxiliaryDimensions calls accounting dimensions endpoint", async () => {
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    return {
      ok: true,
      json: async () => ({
        account_set_id: "default",
        dimension_type: "customer",
        supported_dimension_types: [],
        total: 0,
        dimensions: []
      })
    };
  };

  await fetchAuxiliaryDimensions("default", "customer", "http://api.local", fetcher, "u-finance-manager");

  assert.equal(calls[0].url, "http://api.local/api/v1/accounting/dimensions?account_set_id=default&dimension_type=customer");
  assert.equal(calls[0].options.headers["X-Actor-Id"], "u-finance-manager");
});

test("saveAuxiliaryDimension posts dimension payload", async () => {
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    return {
      ok: true,
      json: async () => ({ id: "default:customer:CUST-SH-001", dimension_name: "上海客户" })
    };
  };

  await saveAuxiliaryDimension(
    {
      account_set_id: "default",
      dimension_type: "customer",
      dimension_code: "CUST-SH-001",
      dimension_name: "上海客户",
      is_active: true
    },
    "http://api.local",
    fetcher,
    "u-finance-manager"
  );

  assert.equal(calls[0].url, "http://api.local/api/v1/accounting/dimensions");
  assert.equal(JSON.parse(calls[0].options.body).dimension_code, "CUST-SH-001");
});
