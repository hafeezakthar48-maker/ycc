import assert from "node:assert/strict";
import test from "node:test";

import {
  fetchTaxFilingWorksheet,
  fetchVatLedger,
  postIncomeTaxAccrual,
  postSurtaxAccrual,
  postTaxPayment,
  postUnpaidVatTransfer
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

test("税务核算 API helper 覆盖台账、底稿、计提和缴款", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/tax-accounting/vat-ledger?account_set_id=default&period=2026-06": {
      account_set_id: "default",
      period: "2026-06",
      total: 2,
      lines: []
    },
    "http://api.local/api/v1/tax-accounting/filing-worksheet?account_set_id=default&period=2026-06": {
      account_set_id: "default",
      period: "2026-06",
      output_vat: "130.00",
      input_vat: "104.00",
      input_transfer_out: "0.00",
      vat_payable: "26.00",
      surtax_payable: "3.12",
      income_tax_payable: "5000.00"
    },
    "http://api.local/api/v1/tax-accounting/unpaid-vat-transfer": { id: "je-vat", source_type: "tax_unpaid_vat_transfer" },
    "http://api.local/api/v1/tax-accounting/surtax-accrual": { id: "je-surtax", source_type: "tax_surtax_accrual" },
    "http://api.local/api/v1/tax-accounting/income-tax-accrual": { id: "je-income-tax", source_type: "tax_income_tax_accrual" },
    "http://api.local/api/v1/tax-accounting/tax-payments": { id: "je-payment", source_type: "tax_payment" }
  });

  const ledger = await fetchVatLedger("default", "2026-06", "http://api.local", fetcher);
  const worksheet = await fetchTaxFilingWorksheet("default", "2026-06", "http://api.local", fetcher);
  const vat = await postUnpaidVatTransfer({ account_set_id: "default", period: "2026-06", amount: "26.00" }, "http://api.local", fetcher);
  const surtax = await postSurtaxAccrual({ account_set_id: "default", period: "2026-06", vat_payable: "26.00" }, "http://api.local", fetcher);
  const incomeTax = await postIncomeTaxAccrual({ account_set_id: "default", period: "2026-06", amount: "5000.00" }, "http://api.local", fetcher);
  const payment = await postTaxPayment(
    { account_set_id: "default", period: "2026-07", tax_account_code: "222102", amount: "26.00", bank_account_code: "1002" },
    "http://api.local",
    fetcher
  );

  assert.equal(ledger.total, 2);
  assert.equal(worksheet.vat_payable, "26.00");
  assert.equal(vat.source_type, "tax_unpaid_vat_transfer");
  assert.equal(surtax.source_type, "tax_surtax_accrual");
  assert.equal(incomeTax.source_type, "tax_income_tax_accrual");
  assert.equal(payment.source_type, "tax_payment");
  assert.deepEqual(fetcher.calls.map((call) => call.url), [
    "http://api.local/api/v1/tax-accounting/vat-ledger?account_set_id=default&period=2026-06",
    "http://api.local/api/v1/tax-accounting/filing-worksheet?account_set_id=default&period=2026-06",
    "http://api.local/api/v1/tax-accounting/unpaid-vat-transfer",
    "http://api.local/api/v1/tax-accounting/surtax-accrual",
    "http://api.local/api/v1/tax-accounting/income-tax-accrual",
    "http://api.local/api/v1/tax-accounting/tax-payments"
  ]);
  assert.ok(fetcher.calls.every((call) => call.init.headers["X-Actor-Id"] === "u-finance-manager"));
});
