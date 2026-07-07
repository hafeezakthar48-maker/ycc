import { useEffect, useMemo, useState } from "react";
import {
  createAccountingSchedule,
  fetchAccrualAmortizationSchedules,
  postAccountingScheduleForPeriod,
  postLoanInterestAccrual
} from "../services/dashboardApi";
import type {
  AccountingSchedule,
  AccrualAmortizationScheduleListResponse,
  LoanSchedule,
  ScheduleType
} from "../types/accrualAmortization";

interface AccrualAmortizationPanelProps {
  period: string;
}

const scheduleLabels: Record<ScheduleType, string> = {
  prepaid_amortization: "预付摊销",
  accrued_expense: "预提费用",
  deferred_revenue: "递延收入",
  loan_interest: "借款利息"
};

function money(value: string | number | null | undefined) {
  return Number(value ?? 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function percent(value: string | number | null | undefined) {
  return `${(Number(value ?? 0) * 100).toFixed(2)}%`;
}

function monthsBetween(startPeriod: string, endPeriod: string) {
  const [startYear, startMonth] = startPeriod.split("-").map(Number);
  const [endYear, endMonth] = endPeriod.split("-").map(Number);
  return Math.max((endYear - startYear) * 12 + endMonth - startMonth + 1, 1);
}

function monthlyAmount(schedule: AccountingSchedule) {
  return Number(schedule.total_amount ?? 0) / monthsBetween(schedule.start_period, schedule.end_period);
}

function monthlyInterest(loan: LoanSchedule) {
  return Number(loan.principal ?? 0) * Number(loan.annual_rate ?? 0) / 12;
}

export default function AccrualAmortizationPanel({ period }: AccrualAmortizationPanelProps) {
  const [selectedPeriod, setSelectedPeriod] = useState(period);
  const [payload, setPayload] = useState<AccrualAmortizationScheduleListResponse | null>(null);
  const [scheduleCode, setScheduleCode] = useState("AMORT-2026-001");
  const [scheduleType, setScheduleType] = useState<ScheduleType>("prepaid_amortization");
  const [startPeriod, setStartPeriod] = useState(period);
  const [endPeriod, setEndPeriod] = useState(period);
  const [totalAmount, setTotalAmount] = useState("12000.00");
  const [debitAccountCode, setDebitAccountCode] = useState("6602");
  const [creditAccountCode, setCreditAccountCode] = useState("1801");
  const [loanCode, setLoanCode] = useState("LOAN-2026-001");
  const [principal, setPrincipal] = useState("1000000.00");
  const [annualRate, setAnnualRate] = useState("0.036");
  const [lastAction, setLastAction] = useState("待处理");
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  const schedules = payload?.schedules ?? [];
  const loans = payload?.loan_schedules ?? [];
  const activeScheduleCount = useMemo(() => schedules.filter((item) => item.status === "active").length, [schedules]);
  const postedScheduleCount = schedules.filter((item) => item.posted_periods.includes(selectedPeriod)).length;

  useEffect(() => {
    setSelectedPeriod(period);
    setStartPeriod(period);
    setEndPeriod(period);
  }, [period]);

  useEffect(() => {
    refreshSchedules();
  }, [selectedPeriod]);

  function refreshSchedules() {
    setError(null);
    return fetchAccrualAmortizationSchedules("default")
      .then(setPayload)
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "预提摊销读取失败"));
  }

  function runAction(action: () => Promise<unknown>, label: string) {
    setIsBusy(true);
    setError(null);
    action()
      .then(() => {
        setLastAction(label);
        return refreshSchedules();
      })
      .catch((actionError) => setError(actionError instanceof Error ? actionError.message : `${label}失败`))
      .finally(() => setIsBusy(false));
  }

  function handleCreateSchedule() {
    runAction(
      () => createAccountingSchedule({
        account_set_id: "default",
        schedule_code: scheduleCode,
        schedule_type: scheduleType,
        start_period: startPeriod,
        end_period: endPeriod,
        total_amount: totalAmount,
        debit_account_code: debitAccountCode,
        credit_account_code: creditAccountCode
      }),
      "schedule_created"
    );
  }

  function handlePostSchedule(code = scheduleCode) {
    runAction(
      () => postAccountingScheduleForPeriod(code, { account_set_id: "default", period: selectedPeriod }),
      "accrual_amortization_posting"
    );
  }

  function handlePostLoanInterest() {
    runAction(
      () => postLoanInterestAccrual({
        account_set_id: "default",
        loan_code: loanCode,
        period: selectedPeriod,
        principal,
        annual_rate: annualRate,
        start_period: selectedPeriod,
        end_period: endPeriod
      }),
      "loan_interest_accrual"
    );
  }

  return (
    <section id="accrual-amortization-panel" className="accrual-amortization-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">预提摊销与融资利息</span>
          <h2>核算计划、本期生成与借款利息计提</h2>
        </div>
        <div className="qa-status-strip">
          <span>{selectedPeriod}</span>
          <span>{lastAction}</span>
          <span>{activeScheduleCount} 个启用计划</span>
        </div>
      </div>

      {error ? <p className="inline-error">{error}</p> : null}

      <div className="period-close-toolbar accrual-amortization-toolbar">
        <label>
          <span>期间</span>
          <input value={selectedPeriod} onChange={(event) => setSelectedPeriod(event.target.value)} />
        </label>
        <label>
          <span>计划编号</span>
          <input value={scheduleCode} onChange={(event) => setScheduleCode(event.target.value)} />
        </label>
        <label>
          <span>类型</span>
          <select value={scheduleType} onChange={(event) => setScheduleType(event.target.value as ScheduleType)}>
            <option value="prepaid_amortization">预付摊销</option>
            <option value="accrued_expense">预提费用</option>
            <option value="deferred_revenue">递延收入</option>
          </select>
        </label>
        <label>
          <span>起始</span>
          <input value={startPeriod} onChange={(event) => setStartPeriod(event.target.value)} />
        </label>
        <label>
          <span>结束</span>
          <input value={endPeriod} onChange={(event) => setEndPeriod(event.target.value)} />
        </label>
        <label>
          <span>总金额</span>
          <input value={totalAmount} onChange={(event) => setTotalAmount(event.target.value)} />
        </label>
        <label>
          <span>借方科目</span>
          <input value={debitAccountCode} onChange={(event) => setDebitAccountCode(event.target.value)} />
        </label>
        <label>
          <span>贷方科目</span>
          <input value={creditAccountCode} onChange={(event) => setCreditAccountCode(event.target.value)} />
        </label>
        <button type="button" className="button-secondary" onClick={() => refreshSchedules()} disabled={isBusy}>刷新</button>
        <button type="button" onClick={handleCreateSchedule} disabled={isBusy}>创建计划</button>
        <button type="button" onClick={() => handlePostSchedule()} disabled={isBusy}>生成本期</button>
      </div>

      <div className="period-close-toolbar accrual-amortization-loan-form">
        <label>
          <span>借款编号</span>
          <input value={loanCode} onChange={(event) => setLoanCode(event.target.value)} />
        </label>
        <label>
          <span>本金</span>
          <input value={principal} onChange={(event) => setPrincipal(event.target.value)} />
        </label>
        <label>
          <span>年利率</span>
          <input value={annualRate} onChange={(event) => setAnnualRate(event.target.value)} />
        </label>
        <button type="button" onClick={handlePostLoanInterest} disabled={isBusy}>计提借款利息</button>
      </div>

      <div className="period-close-summary-grid accrual-amortization-summary-grid">
        <article>
          <span>核算计划</span>
          <strong>{schedules.length}</strong>
        </article>
        <article>
          <span>本期已生成</span>
          <strong>{postedScheduleCount}</strong>
        </article>
        <article>
          <span>借款计划</span>
          <strong>{loans.length}</strong>
        </article>
      </div>

      <div className="period-close-grid accrual-amortization-grid">
        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">核算计划</span>
              <h3>预付、预提与递延收入</h3>
            </div>
            <strong>{schedules.length}</strong>
          </div>
          <div className="voucher-table-wrap">
            <table className="voucher-table accrual-amortization-schedule-table">
              <thead>
                <tr>
                  <th>计划编号</th>
                  <th>类型</th>
                  <th>起止期间</th>
                  <th>总金额</th>
                  <th>本期金额</th>
                  <th>已生成期间</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {schedules.length ? schedules.map((schedule) => (
                  <tr key={schedule.schedule_code}>
                    <td>{schedule.schedule_code}</td>
                    <td>{scheduleLabels[schedule.schedule_type]}</td>
                    <td>{schedule.start_period} 至 {schedule.end_period}</td>
                    <td>{money(schedule.total_amount)}</td>
                    <td>{money(monthlyAmount(schedule))}</td>
                    <td>{schedule.posted_periods.length ? schedule.posted_periods.join(", ") : "未生成"}</td>
                    <td>{schedule.status}</td>
                    <td>
                      <button type="button" className="button-secondary" onClick={() => handlePostSchedule(schedule.schedule_code)} disabled={isBusy}>
                        生成
                      </button>
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={8}>暂无核算计划</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">借款利息</span>
              <h3>本金、利率与本期利息</h3>
            </div>
            <strong>{loans.length}</strong>
          </div>
          <div className="voucher-table-wrap">
            <table className="voucher-table accrual-amortization-loan-table">
              <thead>
                <tr>
                  <th>借款编号</th>
                  <th>本金</th>
                  <th>年利率</th>
                  <th>本期利息</th>
                  <th>已计提期间</th>
                  <th>还款状态</th>
                </tr>
              </thead>
              <tbody>
                {loans.length ? loans.map((loan) => (
                  <tr key={loan.loan_code}>
                    <td>{loan.loan_code}</td>
                    <td>{money(loan.principal)}</td>
                    <td>{percent(loan.annual_rate)}</td>
                    <td>{money(monthlyInterest(loan))}</td>
                    <td>{loan.interest_posted_periods.length ? loan.interest_posted_periods.join(", ") : "未计提"}</td>
                    <td>{loan.interest_posted_periods.includes(selectedPeriod) ? "本期已计提" : "待计提"}</td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={6}>暂无借款计划</td>
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
