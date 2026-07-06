import assert from "node:assert/strict";
import test from "node:test";

import { fetchAccountingAccounts, fetchJournalEntries } from "../src/services/dashboardApi.ts";

test("fetchAccountingAccounts calls accounting account endpoint", async () => {
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    return {
      ok: true,
      json: async () => ({ account_set_id: "default", accounts: [] })
    };
  };

  await fetchAccountingAccounts("default", "http://api.local", fetcher, "u-finance-manager");

  assert.equal(calls[0].url, "http://api.local/api/v1/accounting/accounts?account_set_id=default");
  assert.equal(calls[0].options.headers["X-Actor-Id"], "u-finance-manager");
});

test("fetchJournalEntries passes account set and period", async () => {
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    return {
      ok: true,
      json: async () => ({ account_set_id: "default", period: "2026-06", total: 0, entries: [] })
    };
  };

  await fetchJournalEntries("default", "2026-06", "http://api.local", fetcher, "u-finance-manager");

  assert.equal(calls[0].url, "http://api.local/api/v1/accounting/journal-entries?account_set_id=default&period=2026-06");
});
