import assert from "node:assert/strict";
import test from "node:test";

import {
  closeAccountingPeriod,
  fetchAccountSets,
  fetchAccountBalanceTable,
  fetchDetailLedger,
  fetchGeneralLedger,
  fetchAccountingPeriods,
  reopenAccountingPeriod
} from "../src/services/dashboardApi.ts";

function createFetcher(payloads) {
  const calls = [];
  const fetcher = async (url, init) => {
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

test("账簿 API helper 读取总账、明细账和科目余额表", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/ledger/general?period=2026-06": {
      period: "2026-06",
      voucher_count: 1,
      entry_count: 3,
      total_debit: "1060.00",
      total_credit: "1060.00",
      balanced: true,
      accounts: []
    },
    "http://api.local/api/v1/ledger/detail?period=2026-06&account_code=6602": {
      period: "2026-06",
      account_code: "6602",
      account_name: "管理费用",
      line_count: 1,
      debit_total: "1000.00",
      credit_total: "0.00",
      balance_direction: "借",
      balance_amount: "1000.00",
      lines: []
    },
    "http://api.local/api/v1/ledger/account-balances?period=2026-06": {
      period: "2026-06",
      account_count: 3,
      total_debit: "1060.00",
      total_credit: "1060.00",
      balanced: true,
      accounts: []
    }
  });

  const general = await fetchGeneralLedger("2026-06", "http://api.local", fetcher);
  const detail = await fetchDetailLedger("2026-06", "6602", "http://api.local", fetcher);
  const balanceTable = await fetchAccountBalanceTable("2026-06", "http://api.local", fetcher);

  assert.equal(general.voucher_count, 1);
  assert.equal(detail.account_name, "管理费用");
  assert.equal(balanceTable.account_count, 3);
  assert.deepEqual(fetcher.calls.map((call) => call.url), [
    "http://api.local/api/v1/ledger/general?period=2026-06",
    "http://api.local/api/v1/ledger/detail?period=2026-06&account_code=6602",
    "http://api.local/api/v1/ledger/account-balances?period=2026-06"
  ]);
  assert.ok(fetcher.calls.every((call) => call.init.headers["X-Actor-Id"] === "u-finance-manager"));
});

test("账套与会计期间 API helper 接入读取、关账和重开", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/ledger/account-sets": {
      account_sets: [{ id: "default", name: "默认账套", base_currency: "CNY", accounting_standard: "企业会计准则", is_default: true }]
    },
    "http://api.local/api/v1/ledger/periods?account_set_id=default": {
      account_set_id: "default",
      periods: [{ account_set_id: "default", period: "2026-06", status: "open", closed_by: null, closed_at: null, voucher_count: 0, posted_voucher_count: 0 }]
    },
    "http://api.local/api/v1/ledger/periods/2026-06/close": {
      account_set_id: "default",
      period: "2026-06",
      status: "closed",
      closed_by: "财务主管",
      closed_at: "2026-07-05T00:00:00Z",
      voucher_count: 0,
      posted_voucher_count: 0
    },
    "http://api.local/api/v1/ledger/periods/2026-06/reopen": {
      account_set_id: "default",
      period: "2026-06",
      status: "open",
      closed_by: null,
      closed_at: null,
      voucher_count: 0,
      posted_voucher_count: 0
    }
  });

  const accountSets = await fetchAccountSets("http://api.local", fetcher);
  const periods = await fetchAccountingPeriods("default", "http://api.local", fetcher);
  const closed = await closeAccountingPeriod("2026-06", "财务主管", "http://api.local", fetcher);
  const reopened = await reopenAccountingPeriod("2026-06", "财务主管", "http://api.local", fetcher);

  assert.equal(accountSets.account_sets[0].id, "default");
  assert.equal(periods.periods[0].status, "open");
  assert.equal(closed.status, "closed");
  assert.equal(reopened.status, "open");
  assert.equal(fetcher.calls.at(-1).init.method, "POST");
  assert.ok(fetcher.calls.every((call) => call.init.headers["X-Actor-Id"] === "u-finance-manager"));
});

test("账簿 API helper 支持按账套读取和操作期间", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/ledger/general?period=2026-06&account_set_id=cross_border": {
      period: "2026-06",
      voucher_count: 1,
      entry_count: 3,
      total_debit: "2120.00",
      total_credit: "2120.00",
      balanced: true,
      accounts: []
    },
    "http://api.local/api/v1/ledger/detail?period=2026-06&account_code=6602&account_set_id=cross_border": {
      period: "2026-06",
      account_code: "6602",
      account_name: "管理费用",
      line_count: 1,
      debit_total: "2000.00",
      credit_total: "0.00",
      balance_direction: "借",
      balance_amount: "2000.00",
      lines: []
    },
    "http://api.local/api/v1/ledger/account-balances?period=2026-06&account_set_id=cross_border": {
      period: "2026-06",
      account_count: 3,
      total_debit: "2120.00",
      total_credit: "2120.00",
      balanced: true,
      accounts: []
    },
    "http://api.local/api/v1/ledger/periods?account_set_id=cross_border": {
      account_set_id: "cross_border",
      periods: []
    },
    "http://api.local/api/v1/ledger/periods/2026-06/close?account_set_id=cross_border": {
      account_set_id: "cross_border",
      period: "2026-06",
      status: "closed",
      closed_by: "财务主管",
      closed_at: "2026-07-05T00:00:00Z",
      voucher_count: 1,
      posted_voucher_count: 1
    }
  });

  await fetchGeneralLedger("2026-06", "http://api.local", fetcher, "u-finance-manager", "cross_border");
  await fetchDetailLedger("2026-06", "6602", "http://api.local", fetcher, "u-finance-manager", "cross_border");
  await fetchAccountBalanceTable("2026-06", "http://api.local", fetcher, "u-finance-manager", "cross_border");
  await fetchAccountingPeriods("cross_border", "http://api.local", fetcher);
  await closeAccountingPeriod("2026-06", "财务主管", "http://api.local", fetcher, "u-finance-manager", "cross_border");

  assert.deepEqual(fetcher.calls.map((call) => call.url), [
    "http://api.local/api/v1/ledger/general?period=2026-06&account_set_id=cross_border",
    "http://api.local/api/v1/ledger/detail?period=2026-06&account_code=6602&account_set_id=cross_border",
    "http://api.local/api/v1/ledger/account-balances?period=2026-06&account_set_id=cross_border",
    "http://api.local/api/v1/ledger/periods?account_set_id=cross_border",
    "http://api.local/api/v1/ledger/periods/2026-06/close?account_set_id=cross_border"
  ]);
});
