import assert from "node:assert/strict";
import test from "node:test";

import {
  createConsolidationGroup,
  fetchConsolidatedStatements,
  fetchConsolidationEliminations,
  fetchConsolidationGroups,
  fetchConsolidationReportingPackage,
  rebuildConsolidationEliminations
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

test("合并报表 API helper 覆盖集团、报表包、抵销和合并报表", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/consolidation/groups": {
      group_id: "group-001",
      group_name: "中国财务AI集团",
      total_groups: 1,
      groups: [],
      entities: []
    },
    "http://api.local/api/v1/consolidation/reporting-package?account_set_id=default&period=2026-06": {
      account_set_id: "default",
      period: "2026-06",
      balance_sheet: { title: "资产负债表" },
      income_statement: { title: "利润表" },
      cash_flow_statement: { title: "现金流量表" }
    },
    "http://api.local/api/v1/consolidation/eliminations/rebuild": {
      group_id: "group-001",
      period: "2026-06",
      total_eliminations: 4,
      eliminations: []
    },
    "http://api.local/api/v1/consolidation/eliminations?group_id=group-001&period=2026-06": {
      group_id: "group-001",
      period: "2026-06",
      total_eliminations: 4,
      eliminations: []
    },
    "http://api.local/api/v1/consolidation/statements?group_id=group-001&period=2026-06": {
      group_id: "group-001",
      period: "2026-06",
      minority_interest: "200000.00"
    }
  });

  const groups = await fetchConsolidationGroups("http://api.local", fetcher);
  const group = await createConsolidationGroup(
    { group_id: "group-001", group_name: "中国财务AI集团", entities: [] },
    "http://api.local",
    fetcher
  );
  const reportingPackage = await fetchConsolidationReportingPackage("default", "2026-06", "http://api.local", fetcher);
  const rebuilt = await rebuildConsolidationEliminations(
    { group_id: "group-001", period: "2026-06" },
    "http://api.local",
    fetcher
  );
  const eliminations = await fetchConsolidationEliminations("group-001", "2026-06", "http://api.local", fetcher);
  const statements = await fetchConsolidatedStatements("group-001", "2026-06", "http://api.local", fetcher);

  assert.equal(groups.total_groups, 1);
  assert.equal(group.group_id, "group-001");
  assert.equal(reportingPackage.balance_sheet.title, "资产负债表");
  assert.equal(rebuilt.total_eliminations, 4);
  assert.equal(eliminations.total_eliminations, 4);
  assert.equal(statements.minority_interest, "200000.00");
  assert.deepEqual(fetcher.calls.map((call) => call.url), [
    "http://api.local/api/v1/consolidation/groups",
    "http://api.local/api/v1/consolidation/groups",
    "http://api.local/api/v1/consolidation/reporting-package?account_set_id=default&period=2026-06",
    "http://api.local/api/v1/consolidation/eliminations/rebuild",
    "http://api.local/api/v1/consolidation/eliminations?group_id=group-001&period=2026-06",
    "http://api.local/api/v1/consolidation/statements?group_id=group-001&period=2026-06"
  ]);
  assert.ok(fetcher.calls.every((call) => call.init.headers["X-Actor-Id"] === "u-finance-manager"));
});
