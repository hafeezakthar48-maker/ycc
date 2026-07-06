import { useEffect, useState } from "react";
import { calculatePayroll, fetchAccountSets } from "../services/dashboardApi";
import type { AccountSetItem } from "../types/ledger";
import type {
  MoneyValue,
  PayrollCalculationResponse,
  PayrollEmployeeInput,
  PayrollSummary
} from "../types/payroll";

interface PayrollPanelProps {
  period: string;
}

const emptySummary: PayrollSummary = {
  employee_count: 0,
  gross_pay_total: 0,
  employee_social_security_total: 0,
  employer_social_security_total: 0,
  employee_housing_fund_total: 0,
  employer_housing_fund_total: 0,
  individual_income_tax_total: 0,
  net_pay_total: 0,
  employer_cost_total: 0,
  average_net_pay: 0
};

const defaultEmployees: PayrollEmployeeInput[] = [
  {
    employee_id: "E001",
    employee_name: "张会计",
    department: "财务部",
    base_salary: 20000,
    bonus: 0,
    allowance: 0,
    social_security_base: 20000,
    housing_fund_base: 20000,
    special_additional_deduction: 1000,
    other_deduction: 0
  },
  {
    employee_id: "E002",
    employee_name: "李运营",
    department: "运营部",
    base_salary: 8000,
    bonus: 0,
    allowance: 0,
    social_security_base: 8000,
    housing_fund_base: 8000,
    special_additional_deduction: 0,
    other_deduction: 0
  }
];

const numericFields: Array<keyof PayrollEmployeeInput> = [
  "base_salary",
  "bonus",
  "allowance",
  "social_security_base",
  "housing_fund_base",
  "special_additional_deduction",
  "other_deduction"
];

function money(value: MoneyValue | null | undefined) {
  return Number(value ?? 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function percent(value: MoneyValue | null | undefined) {
  return `${(Number(value ?? 0) * 100).toFixed(0)}%`;
}

export default function PayrollPanel({ period }: PayrollPanelProps) {
  const [accountSets, setAccountSets] = useState<AccountSetItem[]>([]);
  const [selectedAccountSetId, setSelectedAccountSetId] = useState("default");
  const [employees, setEmployees] = useState<PayrollEmployeeInput[]>(defaultEmployees);
  const [result, setResult] = useState<PayrollCalculationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  const summary = result?.summary ?? emptySummary;
  const selectedAccountSet = accountSets.find((accountSet) => accountSet.id === selectedAccountSetId) ?? accountSets[0] ?? null;

  useEffect(() => {
    fetchAccountSets()
      .then((payload) => setAccountSets(payload.account_sets))
      .catch(() => setAccountSets([]));
  }, []);

  useEffect(() => {
    const fallbackAccountSetId = accountSets.find((accountSet) => accountSet.is_default)?.id ?? accountSets[0]?.id;
    if (fallbackAccountSetId && !accountSets.some((accountSet) => accountSet.id === selectedAccountSetId)) {
      setSelectedAccountSetId(fallbackAccountSetId);
    }
  }, [accountSets, selectedAccountSetId]);

  function updateEmployee(index: number, key: keyof PayrollEmployeeInput, value: string) {
    setEmployees((current) => current.map((employee, employeeIndex) => {
      if (employeeIndex !== index) {
        return employee;
      }
      if (numericFields.includes(key)) {
        const numericValue = Number(value);
        return { ...employee, [key]: Number.isFinite(numericValue) ? numericValue : 0 };
      }
      return { ...employee, [key]: value };
    }));
  }

  function addEmployeeRow() {
    const nextIndex = employees.length + 1;
    setEmployees((current) => [
      ...current,
      {
        employee_id: `E${String(nextIndex).padStart(3, "0")}`,
        employee_name: "新员工",
        department: "未分配",
        base_salary: 8000,
        bonus: 0,
        allowance: 0,
        social_security_base: 8000,
        housing_fund_base: 8000,
        special_additional_deduction: 0,
        other_deduction: 0
      }
    ]);
  }

  function removeEmployeeRow(index: number) {
    setEmployees((current) => current.length > 1 ? current.filter((_, employeeIndex) => employeeIndex !== index) : current);
  }

  function handleCalculate() {
    setIsBusy(true);
    setError(null);
    calculatePayroll({
      account_set_id: selectedAccountSetId,
      period,
      operator: "财务主管",
      employees
    })
      .then(setResult)
      .catch((calculateError) => {
        setError(calculateError instanceof Error ? calculateError.message : "工资计算失败");
      })
      .finally(() => {
        setIsBusy(false);
      });
  }

  return (
    <section id="payroll-panel" className="payroll-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">工资管理</span>
          <h2>工资计算、社保、公积金与个税</h2>
        </div>
        <div className="qa-status-strip">
          <span>{selectedAccountSet?.name ?? "默认账套"}</span>
          <span>{period}</span>
          <span>{summary.employee_count} 名员工</span>
        </div>
      </div>

      {error ? <p className="inline-error">{error}</p> : null}

      <div className="payroll-toolbar">
        <label>
          <span>账套</span>
          <select value={selectedAccountSetId} onChange={(event) => setSelectedAccountSetId(event.target.value)} aria-label="工资账套">
            {(accountSets.length ? accountSets : [{ id: selectedAccountSetId, name: "默认账套" } as AccountSetItem]).map((accountSet) => (
              <option value={accountSet.id} key={accountSet.id}>{accountSet.name}</option>
            ))}
          </select>
        </label>
        <div className="payroll-actions">
          <button type="button" className="button-secondary" onClick={addEmployeeRow}>新增员工行</button>
          <button type="button" onClick={handleCalculate} disabled={isBusy}>工资计算</button>
        </div>
      </div>

      <div className="payroll-summary-grid">
        <article>
          <span>应发合计</span>
          <strong>{money(summary.gross_pay_total)}</strong>
        </article>
        <article>
          <span>个税合计</span>
          <strong>{money(summary.individual_income_tax_total)}</strong>
        </article>
        <article>
          <span>实发合计</span>
          <strong>{money(summary.net_pay_total)}</strong>
        </article>
        <article>
          <span>企业成本</span>
          <strong>{money(summary.employer_cost_total)}</strong>
        </article>
      </div>

      <section className="panel">
        <div className="panel-header">
          <div>
            <span className="eyebrow">员工工资项</span>
            <h3>计算输入</h3>
          </div>
        </div>
        <div className="voucher-table-wrap">
          <table className="voucher-table payroll-input-table">
            <thead>
              <tr>
                <th>员工</th>
                <th>部门</th>
                <th>基本工资</th>
                <th>奖金</th>
                <th>津贴</th>
                <th>社保基数</th>
                <th>公积金基数</th>
                <th>专项附加</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {employees.map((employee, index) => (
                <tr key={`${employee.employee_id}-${index}`}>
                  <td>
                    <input value={employee.employee_name} onChange={(event) => updateEmployee(index, "employee_name", event.target.value)} aria-label={`员工${index + 1}姓名`} />
                  </td>
                  <td>
                    <input value={employee.department} onChange={(event) => updateEmployee(index, "department", event.target.value)} aria-label={`员工${index + 1}部门`} />
                  </td>
                  <td><input type="number" min="0" value={employee.base_salary} onChange={(event) => updateEmployee(index, "base_salary", event.target.value)} /></td>
                  <td><input type="number" min="0" value={employee.bonus ?? 0} onChange={(event) => updateEmployee(index, "bonus", event.target.value)} /></td>
                  <td><input type="number" min="0" value={employee.allowance ?? 0} onChange={(event) => updateEmployee(index, "allowance", event.target.value)} /></td>
                  <td><input type="number" min="0" value={employee.social_security_base} onChange={(event) => updateEmployee(index, "social_security_base", event.target.value)} /></td>
                  <td><input type="number" min="0" value={employee.housing_fund_base} onChange={(event) => updateEmployee(index, "housing_fund_base", event.target.value)} /></td>
                  <td><input type="number" min="0" value={employee.special_additional_deduction ?? 0} onChange={(event) => updateEmployee(index, "special_additional_deduction", event.target.value)} /></td>
                  <td><button type="button" className="button-secondary" onClick={() => removeEmployeeRow(index)}>移除</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="payroll-result-grid">
        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">工资明细</span>
              <h3>员工实发与企业成本</h3>
            </div>
          </div>
          <div className="voucher-table-wrap">
            <table className="voucher-table payroll-employee-table">
              <thead>
                <tr>
                  <th>员工</th>
                  <th>部门</th>
                  <th>应发</th>
                  <th>个人社保</th>
                  <th>公积金</th>
                  <th>应税所得</th>
                  <th>税率</th>
                  <th>个税</th>
                  <th>实发</th>
                  <th>企业成本</th>
                </tr>
              </thead>
              <tbody>
                {result?.employees.length ? result.employees.map((employee) => (
                  <tr key={employee.employee_id}>
                    <td>{employee.employee_name}</td>
                    <td>{employee.department}</td>
                    <td>{money(employee.gross_pay)}</td>
                    <td>{money(employee.employee_social_security)}</td>
                    <td>{money(employee.employee_housing_fund)}</td>
                    <td>{money(employee.taxable_income)}</td>
                    <td>{percent(employee.tax_rate)}</td>
                    <td>{money(employee.individual_income_tax)}</td>
                    <td>{money(employee.net_pay)}</td>
                    <td>{money(employee.employer_cost)}</td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={10}>点击工资计算后生成明细</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">部门分析</span>
              <h3>人工成本分布</h3>
            </div>
          </div>
          <div className="voucher-table-wrap">
            <table className="voucher-table payroll-department-table">
              <thead>
                <tr>
                  <th>部门</th>
                  <th>人数</th>
                  <th>应发</th>
                  <th>实发</th>
                  <th>企业成本</th>
                </tr>
              </thead>
              <tbody>
                {result?.department_analysis.length ? result.department_analysis.map((department) => (
                  <tr key={department.department}>
                    <td>{department.department}</td>
                    <td>{department.employee_count}</td>
                    <td>{money(department.gross_pay_total)}</td>
                    <td>{money(department.net_pay_total)}</td>
                    <td>{money(department.employer_cost_total)}</td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={5}>暂无部门分析</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </section>
  );
}
