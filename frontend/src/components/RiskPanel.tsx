import { useEffect, useMemo, useState } from "react";
import {
  addRiskProcessRecord,
  addRiskReviewRecord,
  assignRiskOwner,
  fetchRiskClosures
} from "../services/riskClosureApi";
import type { RiskItem } from "../types/dashboard";
import type { RiskClosureItem, RiskClosureListResponse, RiskClosureStatus } from "../types/riskClosure";

interface RiskPanelProps {
  risks: RiskItem[];
  period: string;
}

function stars(level: number) {
  return "★".repeat(level) + "☆".repeat(5 - level);
}

const statusLabel: Record<RiskClosureStatus, string> = {
  open: "待分派",
  assigned: "已分派",
  processing: "处理中",
  resolved: "待复核",
  closed: "已关闭"
};

function toOpenClosure(period: string, risk: RiskItem): RiskClosureItem {
  return {
    period,
    risk,
    status: "open",
    owner: null,
    due_date: null,
    process_records: [],
    review_records: []
  };
}

export default function RiskPanel({ risks, period }: RiskPanelProps) {
  const [closureResponse, setClosureResponse] = useState<RiskClosureListResponse | null>(null);
  const [busyRiskId, setBusyRiskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fallbackItems = useMemo(() => risks.map((risk) => toOpenClosure(period, risk)), [period, risks]);
  const items = closureResponse?.items ?? fallbackItems;
  const openCount = closureResponse?.open_count ?? items.filter((item) => item.status !== "closed").length;
  const closedCount = closureResponse?.closed_count ?? items.filter((item) => item.status === "closed").length;

  async function reloadClosures() {
    const response = await fetchRiskClosures(period);
    setClosureResponse(response);
  }

  useEffect(() => {
    let cancelled = false;

    fetchRiskClosures(period)
      .then((response) => {
        if (!cancelled) {
          setClosureResponse(response);
          setError(null);
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setClosureResponse(null);
          setError(loadError instanceof Error ? loadError.message : "风险闭环加载失败");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [period]);

  async function runRiskAction(riskId: string, action: () => Promise<RiskClosureItem>) {
    setBusyRiskId(riskId);
    setError(null);
    try {
      await action();
      await reloadClosures();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "风险闭环操作失败");
    } finally {
      setBusyRiskId(null);
    }
  }

  return (
    <section className="panel risk-panel">
      <div className="panel-header">
        <div>
          <span className="eyebrow">风险预警</span>
          <h2>异常清单与闭环跟踪</h2>
        </div>
        <strong className="risk-count">{items.length} 项</strong>
      </div>

      <div className="risk-closure-summary">
        <span>未关闭 {openCount}</span>
        <span>已关闭 {closedCount}</span>
        <span>{period}</span>
      </div>

      {error ? <p className="inline-error">{error}</p> : null}

      <div className="risk-list">
        {items.map((item) => (
          <article key={item.risk.id} className="risk-item">
            <div className="risk-item__title">
              <h3>{item.risk.title}</h3>
              <span>{stars(item.risk.level)}</span>
            </div>
            <p>{item.risk.description}</p>
            <div className="risk-meta">
              <strong>{item.risk.level_label}</strong>
              <span>{item.risk.trigger_reason}</span>
            </div>
            <div className="risk-closure-meta">
              <span className={`risk-status risk-status--${item.status}`}>{statusLabel[item.status]}</span>
              <span>负责人：{item.owner ?? "未分派"}</span>
              <span>到期：{item.due_date ?? "-"}</span>
            </div>
            <details>
              <summary>建议检查资料</summary>
              <ul>
                {item.risk.suggested_checks.map((checkItem) => (
                  <li key={checkItem}>{checkItem}</li>
                ))}
              </ul>
              <p>{item.risk.compliance_note}</p>
            </details>
            <div className="risk-record-strip">
              <span>处理记录 {item.process_records.length}</span>
              <span>复核记录 {item.review_records.length}</span>
            </div>
            <div className="risk-actions">
              <button
                type="button"
                className="button-secondary"
                disabled={busyRiskId === item.risk.id || item.status === "closed"}
                onClick={() => runRiskAction(
                  item.risk.id,
                  () => assignRiskOwner(item.risk.id, {
                    period,
                    owner: "财务主管",
                    due_date: "2026-07-10",
                    note: "先复核触发原因和建议检查资料。"
                  })
                )}
              >
                分派
              </button>
              <button
                type="button"
                className="button-secondary"
                disabled={busyRiskId === item.risk.id || item.status === "closed"}
                onClick={() => runRiskAction(
                  item.risk.id,
                  () => addRiskProcessRecord(item.risk.id, {
                    period,
                    handler: item.owner ?? "财务主管",
                    action: "已完成初步复核",
                    note: "已核对触发原因，并形成后续处理建议。",
                    next_status: "processing"
                  })
                )}
              >
                处理
              </button>
              <button
                type="button"
                disabled={busyRiskId === item.risk.id || item.status === "closed"}
                onClick={() => runRiskAction(
                  item.risk.id,
                  () => addRiskReviewRecord(item.risk.id, {
                    period,
                    reviewer: "内控复核员",
                    conclusion: "复核记录完整，准予关闭。",
                    next_status: "closed"
                  })
                )}
              >
                复核关闭
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
