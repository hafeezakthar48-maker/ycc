import assert from "node:assert/strict";
import test from "node:test";

import { fetchDefaultStatementMappingSet } from "../src/services/dashboardApi.ts";

function createFetcher(payload) {
  const calls = [];
  const fetcher = async (url, init = {}) => {
    calls.push({ url, init });
    return {
      ok: true,
      status: 200,
      json: async () => payload
    };
  };
  fetcher.calls = calls;
  return fetcher;
}

test("报表映射 API helper 获取默认映射集", async () => {
  const fetcher = createFetcher({
    mapping_set: { mapping_set_id: "stmtmap_default_default", mapping_set_name: "中国企业会计准则通用报表映射" },
    rules: [{ line_code: "BS-CASH", line_name: "货币资金" }]
  });

  const result = await fetchDefaultStatementMappingSet("default", "http://api.local", fetcher);

  assert.equal(result.mapping_set.mapping_set_id, "stmtmap_default_default");
  assert.equal(fetcher.calls[0].url, "http://api.local/api/v1/financial-statements/mapping-sets/default?account_set_id=default");
  assert.equal(fetcher.calls[0].init.headers["X-Actor-Id"], "u-finance-manager");
});
