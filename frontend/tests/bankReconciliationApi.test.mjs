import assert from "node:assert/strict";
import test from "node:test";

import {
  fetchBankMatchCandidates,
  fetchBankReconciliationStatement,
  importBankStatementLines
} from "../src/services/dashboardApi.ts";

function createFetcher(payloads) {
  const calls = [];
  const fetcher = async (url, init = {}) => {
    calls.push({ url, init });
    return {
      ok: true,
      status: 200,
      json: async () => payloads[url]
    };
  };
  fetcher.calls = calls;
  return fetcher;
}

test("银行调节表 API helper 请求 statements endpoint", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/bank-reconciliation/statements?account_set_id=default&bank_account_id=bank-001&period=2026-06": {
      account_set_id: "default",
      bank_account_id: "bank-001",
      period: "2026-06",
      bank_balance: "0.00",
      book_balance: "0.00",
      bank_received_not_booked: "0.00",
      bank_paid_not_booked: "0.00",
      book_received_not_bank: "0.00",
      book_paid_not_bank: "0.00",
      adjusted_bank_balance: "0.00",
      adjusted_book_balance: "0.00",
      unmatched_statement_count: 0,
      unmatched_journal_count: 0,
      unmatched_statement_lines: [],
      unmatched_journal_lines: []
    }
  });

  await fetchBankReconciliationStatement("default", "bank-001", "2026-06", "http://api.local", fetcher);

  assert.equal(fetcher.calls[0].init.headers["X-Actor-Id"], "u-finance-manager");
});

test("银行匹配候选 API helper 请求 matches endpoint", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/bank-reconciliation/matches?account_set_id=default&bank_account_id=bank-001&period=2026-06&minimum_score=80": {
      account_set_id: "default",
      bank_account_id: "bank-001",
      period: "2026-06",
      minimum_score: 80,
      candidates: []
    }
  });

  await fetchBankMatchCandidates("default", "bank-001", "2026-06", 80, "http://api.local", fetcher);

  assert.equal(fetcher.calls[0].url, "http://api.local/api/v1/bank-reconciliation/matches?account_set_id=default&bank_account_id=bank-001&period=2026-06&minimum_score=80");
});

test("银行流水导入 API helper 使用 import endpoint", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/bank-reconciliation/statements/import": {
      account_set_id: "default",
      imported_count: 1,
      duplicate_count: 0,
      lines: []
    }
  });

  await importBankStatementLines(
    {
      account_set_id: "default",
      lines: [
        {
          account_set_id: "default",
          bank_account_id: "bank-001",
          transaction_date: "2026-06-30",
          direction: "inflow",
          amount: "1200.00",
          currency: "CNY",
          counterparty_name: "上海客户A",
          summary: "销售回款",
          bank_reference: "B20260630001"
        }
      ]
    },
    "http://api.local",
    fetcher
  );

  assert.equal(fetcher.calls[0].init.method, "POST");
  assert.equal(fetcher.calls[0].init.headers["X-Actor-Id"], "u-finance-manager");
});
