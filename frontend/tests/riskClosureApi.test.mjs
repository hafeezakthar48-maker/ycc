import assert from "node:assert/strict";
import test from "node:test";

import {
  addRiskProcessRecord,
  addRiskReviewRecord,
  assignRiskOwner,
  fetchRiskClosures
} from "../src/services/riskClosureApi.ts";

function createFetcher(routes) {
  const calls = [];
  const fetcher = async (url, init = {}) => {
    calls.push({ url, init });
    const parsedUrl = new URL(url);
    const key = `${init.method ?? "GET"} ${parsedUrl.pathname}${parsedUrl.search}`;
    const payload = routes[key];
    return {
      ok: Boolean(payload),
      status: payload ? 200 : 404,
      json: async () => payload ?? { detail: "not found" }
    };
  };
  fetcher.calls = calls;
  return fetcher;
}

const closureItem = {
  period: "2026-06",
  risk: {
    id: "cash-profit-divergence",
    title: "现金流与利润背离",
    level: 4,
    level_label: "高风险",
    description: "经营现金流低于净利润。",
    trigger_reason: "经营现金流/净利润低于80%。",
    suggested_checks: ["应收账款账龄表"],
    compliance_note: "建议复核。"
  },
  status: "open",
  owner: null,
  due_date: null,
  process_records: [],
  review_records: []
};

test("fetchRiskClosures 读取风险闭环列表", async () => {
  const fetcher = createFetcher({
    "GET /api/v1/risks/closures?period=2026-06": {
      period: "2026-06",
      total: 1,
      open_count: 1,
      closed_count: 0,
      items: [closureItem]
    }
  });

  const response = await fetchRiskClosures("2026-06", null, "http://api.local", fetcher);

  assert.equal(fetcher.calls[0].url, "http://api.local/api/v1/risks/closures?period=2026-06");
  assert.equal(response.items[0].risk.id, "cash-profit-divergence");
});

test("assignRiskOwner 发送负责人和到期日", async () => {
  const fetcher = createFetcher({
    "POST /api/v1/risks/closures/cash-profit-divergence/assign": {
      ...closureItem,
      status: "assigned",
      owner: "财务主管",
      due_date: "2026-07-10"
    }
  });

  const response = await assignRiskOwner(
    "cash-profit-divergence",
    { period: "2026-06", owner: "财务主管", due_date: "2026-07-10", note: "先复核账龄。" },
    "http://api.local",
    fetcher
  );

  assert.equal(response.status, "assigned");
  assert.equal(JSON.parse(fetcher.calls[0].init.body).owner, "财务主管");
});

test("addRiskProcessRecord 和 addRiskReviewRecord 写入处理与复核记录", async () => {
  const fetcher = createFetcher({
    "POST /api/v1/risks/closures/cash-profit-divergence/process-records": {
      ...closureItem,
      status: "processing"
    },
    "POST /api/v1/risks/closures/cash-profit-divergence/review-records": {
      ...closureItem,
      status: "closed"
    }
  });

  const processing = await addRiskProcessRecord(
    "cash-profit-divergence",
    {
      period: "2026-06",
      handler: "财务主管",
      action: "已复核账龄",
      note: "已确认回款计划。",
      next_status: "processing"
    },
    "http://api.local",
    fetcher
  );
  const closed = await addRiskReviewRecord(
    "cash-profit-divergence",
    {
      period: "2026-06",
      reviewer: "内控复核员",
      conclusion: "可以关闭。",
      next_status: "closed"
    },
    "http://api.local",
    fetcher
  );

  assert.equal(processing.status, "processing");
  assert.equal(closed.status, "closed");
  assert.equal(fetcher.calls.length, 2);
});
