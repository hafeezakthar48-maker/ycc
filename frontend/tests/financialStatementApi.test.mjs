import assert from "node:assert/strict";
import test from "node:test";

import { generateFinancialStatements } from "../src/services/dashboardApi.ts";

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

test("财务报表 API helper 发送生成请求", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/financial-statements/generate": {
      period: "2026-06",
      source: "sample_finance_data",
      balance_sheet: { title: "资产负债表", items: [] },
      income_statement: { title: "利润表", items: [] },
      cash_flow_statement: { title: "现金流量表", items: [] },
      equity_statement: { title: "所有者权益变动表", items: [] },
      management_summary: { title: "管理报表摘要", key_metrics: {}, highlights: [], risks: [] }
    }
  });

  const result = await generateFinancialStatements(
    { period: "2026-06", account_set_id: "default", operator: "财务主管" },
    "http://api.local",
    fetcher
  );

  assert.equal(result.balance_sheet.title, "资产负债表");
  assert.equal(fetcher.calls[0].url, "http://api.local/api/v1/financial-statements/generate");
  assert.equal(fetcher.calls[0].init.method, "POST");
  assert.equal(fetcher.calls[0].init.headers["X-Actor-Id"], "u-finance-manager");
  assert.match(fetcher.calls[0].init.body, /2026-06/);
});
