import { useEffect, useState } from "react";
import {
  fetchBankMatchCandidates,
  fetchBankReconciliationStatement
} from "../services/dashboardApi";
import type {
  BankBalanceReconciliationStatement,
  BankMatchCandidate
} from "../types/bankReconciliation";

interface BankReconciliationPanelProps {
  period: string;
}

const DEFAULT_BANK_ACCOUNT_ID = "bank-001";

function money(value: string | number) {
  return Number(value).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function directionLabel(direction: "inflow" | "outflow") {
  return direction === "inflow" ? "流入" : "流出";
}

export default function BankReconciliationPanel({ period }: BankReconciliationPanelProps) {
  const [bankAccountId, setBankAccountId] = useState(DEFAULT_BANK_ACCOUNT_ID);
  const [statement, setStatement] = useState<BankBalanceReconciliationStatement | null>(null);
  const [candidates, setCandidates] = useState<BankMatchCandidate[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setIsLoading(true);
    Promise.all([
      fetchBankReconciliationStatement("default", bankAccountId, period),
      fetchBankMatchCandidates("default", bankAccountId, period, 80)
    ])
      .then(([statementPayload, candidatePayload]) => {
        if (cancelled) {
          return;
        }
        setStatement(statementPayload);
        setCandidates(candidatePayload.candidates);
      })
      .catch((bankError) => {
        if (!cancelled) {
          setError(bankError instanceof Error ? bankError.message : "银行对账读取失败");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [bankAccountId, period]);

  return (
    <section id="bank-reconciliation-panel" className="bank-reconciliation-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">银行对账</span>
          <h2>银行余额调节表</h2>
        </div>
        <div className="statement-actions bank-reconciliation-actions">
          <label>
            <span>银行账户</span>
            <input
              value={bankAccountId}
              onChange={(event) => setBankAccountId(event.target.value)}
              aria-label="银行账户"
            />
          </label>
          <span>{isLoading ? "读取中" : period}</span>
        </div>
      </div>

      {error ? <p className="inline-error">{error}</p> : null}

      <div className="ledger-summary-grid bank-reconciliation-summary-grid">
        <article>
          <span>银行账面余额</span>
          <strong>{money(statement?.bank_balance ?? 0)}</strong>
        </article>
        <article>
          <span>企业账面余额</span>
          <strong>{money(statement?.book_balance ?? 0)}</strong>
        </article>
        <article>
          <span>调节后银行</span>
          <strong>{money(statement?.adjusted_bank_balance ?? 0)}</strong>
        </article>
        <article>
          <span>调节后企业</span>
          <strong>{money(statement?.adjusted_book_balance ?? 0)}</strong>
        </article>
      </div>

      <div className="bank-reconciliation-grid">
        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">未达账项</span>
              <h3>银行流水</h3>
            </div>
            <strong>{statement?.unmatched_statement_count ?? 0}</strong>
          </div>
          <div className="voucher-table-wrap">
            <table className="voucher-table bank-reconciliation-table">
              <thead>
                <tr>
                  <th>日期</th>
                  <th>方向</th>
                  <th>金额</th>
                  <th>对方</th>
                  <th>摘要</th>
                </tr>
              </thead>
              <tbody>
                {(statement?.unmatched_statement_lines ?? []).map((line) => (
                  <tr key={line.statement_line_id}>
                    <td>{line.transaction_date}</td>
                    <td>{directionLabel(line.direction)}</td>
                    <td>{money(line.amount)}</td>
                    <td>{line.counterparty_name || "-"}</td>
                    <td>{line.summary || "-"}</td>
                  </tr>
                ))}
                {statement && statement.unmatched_statement_lines.length === 0 ? (
                  <tr>
                    <td colSpan={5}>当前期间暂无银行未达账项</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">未达账项</span>
              <h3>企业账务</h3>
            </div>
            <strong>{statement?.unmatched_journal_count ?? 0}</strong>
          </div>
          <div className="voucher-table-wrap">
            <table className="voucher-table bank-reconciliation-table">
              <thead>
                <tr>
                  <th>日期</th>
                  <th>科目</th>
                  <th>方向</th>
                  <th>金额</th>
                  <th>摘要</th>
                </tr>
              </thead>
              <tbody>
                {(statement?.unmatched_journal_lines ?? []).map((line) => (
                  <tr key={line.line_id}>
                    <td>{line.entry_date}</td>
                    <td>{line.account_name}</td>
                    <td>{directionLabel(line.cash_direction)}</td>
                    <td>{money(line.base_amount)}</td>
                    <td>{line.summary || "-"}</td>
                  </tr>
                ))}
                {statement && statement.unmatched_journal_lines.length === 0 ? (
                  <tr>
                    <td colSpan={5}>当前期间暂无企业未达账项</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <section className="panel">
        <div className="panel-header">
          <div>
            <span className="eyebrow">匹配候选</span>
            <h3>候选匹配</h3>
          </div>
        </div>
        <div className="voucher-table-wrap">
          <table className="voucher-table bank-reconciliation-candidate-table">
            <thead>
              <tr>
                <th>银行日期</th>
                <th>账务日期</th>
                <th>方向</th>
                <th>银行金额</th>
                <th>账务金额</th>
                <th>评分</th>
                <th>依据</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((candidate) => (
                <tr key={`${candidate.statement_line_id}-${candidate.journal_line_id}`}>
                  <td>{candidate.statement_date}</td>
                  <td>{candidate.journal_date}</td>
                  <td>{directionLabel(candidate.direction)}</td>
                  <td>{money(candidate.statement_amount)}</td>
                  <td>{money(candidate.journal_amount)}</td>
                  <td>{candidate.score}</td>
                  <td>{candidate.reasons.join("、") || "-"}</td>
                  <td>
                    <button type="button" className="button-secondary" disabled>
                      确认
                    </button>
                  </td>
                </tr>
              ))}
              {candidates.length === 0 ? (
                <tr>
                  <td colSpan={8}>当前期间暂无匹配候选</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
