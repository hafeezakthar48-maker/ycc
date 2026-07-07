import assert from "node:assert/strict";
import test from "node:test";

import {
  accruePayrollBatch,
  fetchPayrollAccountingBatches,
  payPayrollBatch,
  remitPayrollLiabilities
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

test("薪酬正式核算 API helper 覆盖批次、计提、发放和缴纳", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/payroll-accounting/batches?account_set_id=default&period=2026-06": {
      account_set_id: "default",
      period: "2026-06",
      total: 1,
      batches: [{ payroll_batch_id: "PAY-2026-06", status: "paid", liability_payment_status: "remitted" }]
    },
    "http://api.local/api/v1/payroll-accounting/accruals": {
      id: "je-accrual",
      source_type: "payroll_accrual"
    },
    "http://api.local/api/v1/payroll-accounting/payments": {
      id: "je-payment",
      source_type: "payroll_payment"
    },
    "http://api.local/api/v1/payroll-accounting/liability-payments": {
      id: "je-remit",
      source_type: "payroll_liability_payment"
    }
  });

  const batches = await fetchPayrollAccountingBatches("default", "2026-06", "http://api.local", fetcher);
  const accrual = await accruePayrollBatch(
    { account_set_id: "default", period: "2026-06", payroll_batch_id: "PAY-2026-06" },
    "http://api.local",
    fetcher
  );
  const payment = await payPayrollBatch(
    { account_set_id: "default", period: "2026-06", payroll_batch_id: "PAY-2026-06", bank_account_code: "1002" },
    "http://api.local",
    fetcher
  );
  const remittance = await remitPayrollLiabilities(
    { account_set_id: "default", period: "2026-07", payroll_batch_id: "PAY-2026-06", bank_account_code: "1002" },
    "http://api.local",
    fetcher
  );

  assert.equal(batches.batches[0].payroll_batch_id, "PAY-2026-06");
  assert.equal(accrual.source_type, "payroll_accrual");
  assert.equal(payment.source_type, "payroll_payment");
  assert.equal(remittance.source_type, "payroll_liability_payment");
  assert.deepEqual(fetcher.calls.map((call) => call.url), [
    "http://api.local/api/v1/payroll-accounting/batches?account_set_id=default&period=2026-06",
    "http://api.local/api/v1/payroll-accounting/accruals",
    "http://api.local/api/v1/payroll-accounting/payments",
    "http://api.local/api/v1/payroll-accounting/liability-payments"
  ]);
  assert.ok(fetcher.calls.every((call) => call.init.headers["X-Actor-Id"] === "u-finance-manager"));
});
