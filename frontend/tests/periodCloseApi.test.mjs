import assert from "node:assert/strict";
import test from "node:test";

import {
  closePeriod,
  generatePeriodCloseActions,
  reopenPeriod,
  runPeriodCloseChecks
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

test("period close API helpers keep request scope and actor explicit", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/period-close/checks": { items: [] },
    "http://api.local/api/v1/period-close/actions/generate": { results: [] },
    "http://api.local/api/v1/period-close/close": { period: "2026-06", status: "closed" },
    "http://api.local/api/v1/period-close/reopen": { period: "2026-06", status: "open" }
  });

  await runPeriodCloseChecks({ account_set_id: "default", period: "2026-06" }, "http://api.local", fetcher);
  await generatePeriodCloseActions(
    {
      account_set_id: "default",
      period: "2026-06",
      actions: ["profit_loss_carryforward"],
      generated_by: "finance-user"
    },
    "http://api.local",
    fetcher
  );
  await closePeriod({ account_set_id: "default", period: "2026-06", operator: "finance-user" }, "http://api.local", fetcher);
  await reopenPeriod({ account_set_id: "default", period: "2026-06", operator: "finance-user" }, "http://api.local", fetcher);

  assert.equal(fetcher.calls.length, 4);
  assert.equal(fetcher.calls[0].url, "http://api.local/api/v1/period-close/checks");
  assert.equal(fetcher.calls[1].url, "http://api.local/api/v1/period-close/actions/generate");
  assert.equal(fetcher.calls[2].url, "http://api.local/api/v1/period-close/close");
  assert.equal(fetcher.calls[3].url, "http://api.local/api/v1/period-close/reopen");
  assert.ok(fetcher.calls.every((call) => call.init.method === "POST"));
  assert.ok(fetcher.calls.every((call) => call.init.headers["X-Actor-Id"] === "u-finance-manager"));
});
