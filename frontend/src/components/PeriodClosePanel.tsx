import { useEffect, useMemo, useState } from "react";
import {
  closePeriod,
  generatePeriodCloseActions,
  reopenPeriod,
  runPeriodCloseChecks
} from "../services/dashboardApi";
import type {
  PeriodCloseActionResult,
  PeriodCloseActionType,
  PeriodCloseCheckItem,
  PeriodCloseType
} from "../types/periodClose";

interface PeriodClosePanelProps {
  period: string;
}

const closeActions: Array<{ type: PeriodCloseActionType; label: string }> = [
  { type: "fixed_asset_depreciation", label: "固定资产折旧" },
  { type: "payroll_accrual", label: "工资计提" },
  { type: "tax_accrual", label: "税费计提" },
  { type: "fx_revaluation", label: "外币重估" },
  { type: "profit_loss_carryforward", label: "损益结转" },
  { type: "bad_debt_provision", label: "坏账准备" },
  { type: "year_end_profit_distribution", label: "年终利润分配" }
];

const defaultActions: PeriodCloseActionType[] = [
  "fixed_asset_depreciation",
  "payroll_accrual",
  "tax_accrual",
  "fx_revaluation",
  "profit_loss_carryforward",
  "bad_debt_provision"
];

function money(value: string | number) {
  return Number(value).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function checkStatusLabel(item: PeriodCloseCheckItem) {
  if (item.status === "passed") {
    return "通过";
  }
  return item.status === "warning" ? "提醒" : "阻断";
}

function actionLabel(actionType: PeriodCloseActionType) {
  return closeActions.find((item) => item.type === actionType)?.label ?? actionType;
}

export default function PeriodClosePanel({ period }: PeriodClosePanelProps) {
  const [selectedPeriod, setSelectedPeriod] = useState(period);
  const [closeType, setCloseType] = useState<PeriodCloseType>("month");
  const [selectedActions, setSelectedActions] = useState<PeriodCloseActionType[]>(defaultActions);
  const [checks, setChecks] = useState<PeriodCloseCheckItem[]>([]);
  const [results, setResults] = useState<PeriodCloseActionResult[]>([]);
  const [periodStatus, setPeriodStatus] = useState<"open" | "closed">("open");
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  const blockerCount = useMemo(
    () => checks.filter((item) => item.status === "failed" && item.severity === "blocker").length,
    [checks]
  );
  const generatedCount = results.filter((item) => item.status === "generated" || item.status === "existing").length;

  useEffect(() => {
    setSelectedPeriod(period);
  }, [period]);

  useEffect(() => {
    if (closeType === "year" && !selectedActions.includes("year_end_profit_distribution")) {
      setSelectedActions((current) => [...current, "year_end_profit_distribution"]);
    }
    if (closeType === "month" && selectedActions.includes("year_end_profit_distribution")) {
      setSelectedActions((current) => current.filter((action) => action !== "year_end_profit_distribution"));
    }
  }, [closeType, selectedActions]);

  function toggleAction(actionType: PeriodCloseActionType) {
    setSelectedActions((current) => {
      if (current.includes(actionType)) {
        return current.filter((item) => item !== actionType);
      }
      return [...current, actionType];
    });
  }

  function handleChecks() {
    setIsBusy(true);
    setError(null);
    runPeriodCloseChecks({ account_set_id: "default", period: selectedPeriod })
      .then((payload) => setChecks(payload.items))
      .catch((checkError) => setError(checkError instanceof Error ? checkError.message : "结账检查失败"))
      .finally(() => setIsBusy(false));
  }

  function handleGenerate() {
    setIsBusy(true);
    setError(null);
    generatePeriodCloseActions({
      account_set_id: "default",
      period: selectedPeriod,
      actions: selectedActions,
      generated_by: "finance-user"
    })
      .then((payload) => setResults(payload.results))
      .catch((generateError) => setError(generateError instanceof Error ? generateError.message : "期末分录生成失败"))
      .finally(() => setIsBusy(false));
  }

  function handleClose() {
    setIsBusy(true);
    setError(null);
    closePeriod({ account_set_id: "default", period: selectedPeriod, operator: "finance-user" })
      .then((payload) => setPeriodStatus(payload.status === "closed" ? "closed" : "open"))
      .catch((closeError) => setError(closeError instanceof Error ? closeError.message : "期间关闭失败"))
      .finally(() => setIsBusy(false));
  }

  function handleReopen() {
    setIsBusy(true);
    setError(null);
    reopenPeriod({ account_set_id: "default", period: selectedPeriod, operator: "finance-user" })
      .then((payload) => setPeriodStatus(payload.status === "closed" ? "closed" : "open"))
      .catch((reopenError) => setError(reopenError instanceof Error ? reopenError.message : "期间重开失败"))
      .finally(() => setIsBusy(false));
  }

  return (
    <section id="period-close-panel" className="period-close-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">期间结账</span>
          <h2>检查、生成、关闭与重开</h2>
        </div>
        <div className="qa-status-strip">
          <span>{selectedPeriod}</span>
          <span>{closeType === "year" ? "年结" : "月结"}</span>
          <span>{periodStatus === "closed" ? "已关闭" : "打开"}</span>
        </div>
      </div>

      {error ? <p className="inline-error">{error}</p> : null}

      <div className="period-close-toolbar">
        <label>
          <span>期间</span>
          <input value={selectedPeriod} onChange={(event) => setSelectedPeriod(event.target.value)} />
        </label>
        <label>
          <span>类型</span>
          <select value={closeType} onChange={(event) => setCloseType(event.target.value as PeriodCloseType)}>
            <option value="month">月结</option>
            <option value="year">年结</option>
          </select>
        </label>
        <button type="button" className="button-secondary" onClick={handleChecks} disabled={isBusy}>
          执行检查
        </button>
        <button type="button" onClick={handleGenerate} disabled={isBusy || selectedActions.length === 0}>
          生成分录
        </button>
        <button type="button" onClick={handleClose} disabled={isBusy || blockerCount > 0 || periodStatus === "closed"}>
          关闭期间
        </button>
        <button type="button" className="button-secondary" onClick={handleReopen} disabled={isBusy || periodStatus !== "closed"}>
          重开
        </button>
      </div>

      <div className="period-close-action-grid">
        {closeActions.map((action) => (
          <label key={action.type} className="period-close-action-toggle">
            <input
              type="checkbox"
              checked={selectedActions.includes(action.type)}
              onChange={() => toggleAction(action.type)}
              disabled={closeType === "month" && action.type === "year_end_profit_distribution"}
            />
            <span>{action.label}</span>
          </label>
        ))}
      </div>

      <div className="period-close-summary-grid">
        <article>
          <span>阻断项</span>
          <strong>{blockerCount}</strong>
        </article>
        <article>
          <span>检查项</span>
          <strong>{checks.length}</strong>
        </article>
        <article>
          <span>已生成/已存在</span>
          <strong>{generatedCount}</strong>
        </article>
      </div>

      <div className="period-close-grid">
        <section className="panel period-close-check-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">检查清单</span>
              <h3>结账前置条件</h3>
            </div>
          </div>
          <div className="period-close-check-grid">
            {checks.length ? checks.map((item) => (
              <article className={`period-close-check period-close-check--${item.status}`} key={item.check_code}>
                <span>{checkStatusLabel(item)}</span>
                <strong>{item.check_name}</strong>
                <p>{item.message}</p>
              </article>
            )) : (
              <p className="empty-state">暂无检查结果</p>
            )}
          </div>
        </section>

        <section className="panel period-close-result-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">期末动作</span>
              <h3>生成结果</h3>
            </div>
          </div>
          <div className="voucher-table-wrap">
            <table className="voucher-table period-close-result-table">
              <thead>
                <tr>
                  <th>动作</th>
                  <th>状态</th>
                  <th>金额</th>
                  <th>分录</th>
                </tr>
              </thead>
              <tbody>
                {results.length ? results.map((result) => (
                  <tr key={result.action_type}>
                    <td>{actionLabel(result.action_type)}</td>
                    <td>{result.status}</td>
                    <td>{money(result.amount)}</td>
                    <td>{result.journal_entry_ids.length ? result.journal_entry_ids.join(", ") : result.message}</td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={4}>暂无生成结果</td>
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
