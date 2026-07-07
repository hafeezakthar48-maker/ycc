import assert from "node:assert/strict";
import test from "node:test";

import {
  createAccountingSchedule,
  fetchAccrualAmortizationSchedules,
  postAccountingScheduleForPeriod,
  postLoanInterestAccrual
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

test("预提摊销 API helper 覆盖计划列表、创建、本期生成和借款利息", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/accrual-amortization/schedules?account_set_id=default": {
      account_set_id: "default",
      total_schedules: 1,
      total_loans: 1,
      schedules: [],
      loan_schedules: []
    },
    "http://api.local/api/v1/accrual-amortization/schedules": {
      schedule_code: "AMORT-2026-001",
      schedule_type: "prepaid_amortization"
    },
    "http://api.local/api/v1/accrual-amortization/schedules/AMORT-2026-001/post": {
      id: "je-amort",
      source_id: "schedule_posting:default:2026-06:AMORT-2026-001"
    },
    "http://api.local/api/v1/accrual-amortization/loan-interest": {
      id: "je-interest",
      source_id: "loan_interest_accrual:default:2026-06:LOAN-2026-001"
    }
  });

  const list = await fetchAccrualAmortizationSchedules("default", "http://api.local", fetcher);
  const schedule = await createAccountingSchedule(
    {
      account_set_id: "default",
      schedule_code: "AMORT-2026-001",
      schedule_type: "prepaid_amortization",
      start_period: "2026-06",
      end_period: "2026-08",
      total_amount: "3000.00",
      debit_account_code: "6602",
      credit_account_code: "1801"
    },
    "http://api.local",
    fetcher
  );
  const posting = await postAccountingScheduleForPeriod(
    "AMORT-2026-001",
    { account_set_id: "default", period: "2026-06" },
    "http://api.local",
    fetcher
  );
  const interest = await postLoanInterestAccrual(
    {
      account_set_id: "default",
      loan_code: "LOAN-2026-001",
      period: "2026-06",
      principal: "1000000.00",
      annual_rate: "0.036",
      start_period: "2026-06",
      end_period: "2026-12"
    },
    "http://api.local",
    fetcher
  );

  assert.equal(list.total_schedules, 1);
  assert.equal(schedule.schedule_code, "AMORT-2026-001");
  assert.equal(posting.source_id, "schedule_posting:default:2026-06:AMORT-2026-001");
  assert.equal(interest.source_id, "loan_interest_accrual:default:2026-06:LOAN-2026-001");
  assert.deepEqual(fetcher.calls.map((call) => call.url), [
    "http://api.local/api/v1/accrual-amortization/schedules?account_set_id=default",
    "http://api.local/api/v1/accrual-amortization/schedules",
    "http://api.local/api/v1/accrual-amortization/schedules/AMORT-2026-001/post",
    "http://api.local/api/v1/accrual-amortization/loan-interest"
  ]);
  assert.ok(fetcher.calls.every((call) => call.init.headers["X-Actor-Id"] === "u-finance-manager"));
});
