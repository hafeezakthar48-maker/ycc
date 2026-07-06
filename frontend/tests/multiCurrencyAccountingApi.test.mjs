import assert from "node:assert/strict";
import test from "node:test";

import { fetchCurrencies, fetchExchangeRates, saveExchangeRate } from "../src/services/dashboardApi.ts";

test("fetchCurrencies calls accounting currencies endpoint", async () => {
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    return { ok: true, json: async () => ({ currencies: [] }) };
  };

  await fetchCurrencies("http://api.local", fetcher, "u-finance-manager");

  assert.equal(calls[0].url, "http://api.local/api/v1/accounting/currencies");
  assert.equal(calls[0].options.headers["X-Actor-Id"], "u-finance-manager");
});

test("saveExchangeRate posts exchange rate payload", async () => {
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    return { ok: true, json: async () => ({ id: "default:2026-06-18:USD:CNY", rate: "7.120000" }) };
  };

  await saveExchangeRate(
    {
      account_set_id: "default",
      rate_date: "2026-06-18",
      source_currency: "USD",
      target_currency: "CNY",
      rate: "7.120000",
      source: "manual"
    },
    "http://api.local",
    fetcher,
    "u-finance-manager"
  );

  assert.equal(calls[0].url, "http://api.local/api/v1/accounting/exchange-rates");
  assert.equal(JSON.parse(calls[0].options.body).source_currency, "USD");
});

test("fetchExchangeRates passes account set", async () => {
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    return { ok: true, json: async () => ({ account_set_id: "default", rates: [] }) };
  };

  await fetchExchangeRates("default", "http://api.local", fetcher, "u-finance-manager");

  assert.equal(calls[0].url, "http://api.local/api/v1/accounting/exchange-rates?account_set_id=default");
  assert.equal(calls[0].options.headers["X-Actor-Id"], "u-finance-manager");
});
