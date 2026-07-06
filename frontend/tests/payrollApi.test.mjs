import assert from "node:assert/strict";
import test from "node:test";

import { calculatePayroll } from "../src/services/dashboardApi.ts";

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

test("工资管理 API helper 发送工资计算请求", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/payroll/calculate": {
      account_set_id: "default",
      period: "2026-06",
      operator: "财务主管",
      summary: {
        employee_count: 1,
        gross_pay_total: "20000.00",
        employee_social_security_total: "2100.00",
        employer_social_security_total: "5260.00",
        employee_housing_fund_total: "1400.00",
        employer_housing_fund_total: "1400.00",
        individual_income_tax_total: "840.00",
        net_pay_total: "15660.00",
        employer_cost_total: "26660.00",
        average_net_pay: "15660.00"
      },
      employees: [],
      department_analysis: []
    }
  });

  const result = await calculatePayroll(
    {
      account_set_id: "default",
      period: "2026-06",
      operator: "财务主管",
      employees: [
        {
          employee_id: "E001",
          employee_name: "张会计",
          department: "财务部",
          base_salary: 20000,
          bonus: 0,
          allowance: 0,
          social_security_base: 20000,
          housing_fund_base: 20000,
          special_additional_deduction: 1000
        }
      ]
    },
    "http://api.local",
    fetcher
  );

  assert.equal(result.summary.net_pay_total, "15660.00");
  assert.equal(fetcher.calls[0].url, "http://api.local/api/v1/payroll/calculate");
  assert.equal(fetcher.calls[0].init.method, "POST");
  assert.equal(fetcher.calls[0].init.headers["X-Actor-Id"], "u-finance-manager");
  assert.match(fetcher.calls[0].init.body, /张会计/);
});
