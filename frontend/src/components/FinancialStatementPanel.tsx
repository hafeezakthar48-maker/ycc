import { useEffect, useMemo, useState } from "react";
import { generateFinancialStatements } from "../services/dashboardApi";
import type {
  FinancialStatementBundle,
  MoneyValue,
  StatementLineItem
} from "../types/financialStatement";

interface FinancialStatementPanelProps {
  period: string;
}

interface StatementTableProps {
  title: string;
  period: string;
  items: StatementLineItem[];
  totals: Array<{ label: string; value: MoneyValue }>;
}

function money(value: MoneyValue) {
  return Number(value).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function sourceLabel(source: string) {
  if (source === "formal_journal_entries") {
    return "正式分录";
  }
  return source === "reviewed_vouchers" ? "已审核凭证" : "样例经营数据";
}

export default function FinancialStatementPanel({ period }: FinancialStatementPanelProps) {
  const [bundle, setBundle] = useState<FinancialStatementBundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const statementTables = useMemo(() => {
    if (!bundle) {
      return [
        { title: "资产负债表", period, items: [], totals: [] },
        { title: "利润表", period, items: [], totals: [] },
        { title: "现金流量表", period, items: [], totals: [] },
        { title: "所有者权益变动表", period, items: [], totals: [] }
      ];
    }
    return [
      {
        title: bundle.balance_sheet.title,
        period: bundle.balance_sheet.period,
        items: bundle.balance_sheet.items,
        totals: [
          { label: "资产合计", value: bundle.balance_sheet.total_assets },
          { label: "负债合计", value: bundle.balance_sheet.total_liabilities },
          { label: "所有者权益", value: bundle.balance_sheet.total_equity },
          { label: "负债和权益合计", value: bundle.balance_sheet.total_liabilities_and_equity }
        ]
      },
      {
        title: bundle.income_statement.title,
        period: bundle.income_statement.period,
        items: bundle.income_statement.items,
        totals: [
          { label: "营业收入", value: bundle.income_statement.total_revenue },
          { label: "营业成本", value: bundle.income_statement.total_cost },
          { label: "期间费用", value: bundle.income_statement.total_expense },
          { label: "净利润", value: bundle.income_statement.net_profit }
        ]
      },
      {
        title: bundle.cash_flow_statement.title,
        period: bundle.cash_flow_statement.period,
        items: bundle.cash_flow_statement.items,
        totals: [
          { label: "经营现金流", value: bundle.cash_flow_statement.operating_cash_flow_net },
          { label: "投资现金流", value: bundle.cash_flow_statement.investing_cash_flow_net },
          { label: "筹资现金流", value: bundle.cash_flow_statement.financing_cash_flow_net },
          { label: "现金净增加额", value: bundle.cash_flow_statement.net_cash_flow }
        ]
      },
      {
        title: bundle.equity_statement.title,
        period: bundle.equity_statement.period,
        items: bundle.equity_statement.items,
        totals: [
          { label: "期初权益", value: bundle.equity_statement.opening_equity },
          { label: "本期净利润", value: bundle.equity_statement.current_period_profit },
          { label: "期末权益", value: bundle.equity_statement.closing_equity }
        ]
      }
    ];
  }, [bundle, period]);

  function loadStatements() {
    setIsLoading(true);
    setError(null);
    generateFinancialStatements({ period, account_set_id: "default", operator: "财务主管" })
      .then(setBundle)
      .catch((statementError) => {
        setError(statementError instanceof Error ? statementError.message : "财务报表生成失败");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    generateFinancialStatements({ period, account_set_id: "default", operator: "财务主管" })
      .then((payload) => {
        if (!cancelled) {
          setBundle(payload);
        }
      })
      .catch((statementError) => {
        if (!cancelled) {
          setError(statementError instanceof Error ? statementError.message : "财务报表生成失败");
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
  }, [period]);

  return (
    <section id="financial-statements-panel" className="financial-statements-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">财务报表</span>
          <h2>标准报表自动生成</h2>
        </div>
        <div className="statement-actions">
          <span>{period}</span>
          <button type="button" className="button-secondary" onClick={loadStatements} disabled={isLoading}>
            {isLoading ? "生成中..." : "重新生成"}
          </button>
        </div>
      </div>

      {error ? <p className="inline-error">{error}</p> : null}

      <div className="financial-statement-summary-grid">
        <article>
          <span>报表来源</span>
          <strong>{bundle ? sourceLabel(bundle.source) : "读取中"}</strong>
        </article>
        <article>
          <span>平衡校验</span>
          <strong>{bundle?.summary.asset_liability_balanced ? "已平衡" : "待复核"}</strong>
        </article>
        <article>
          <span>已审核凭证</span>
          <strong>{bundle?.summary.reviewed_voucher_count ?? 0}</strong>
        </article>
        <article>
          <span>生成报表</span>
          <strong>{bundle?.summary.generated_statement_count ?? 0}</strong>
        </article>
      </div>

      <div className="financial-statement-grid">
        {statementTables.map((statement) => (
          <StatementTable
            key={statement.title}
            title={statement.title}
            period={statement.period}
            items={statement.items}
            totals={statement.totals}
          />
        ))}
        <section className="panel statement-management-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">管理报表</span>
              <h3>{bundle?.management_summary.title ?? "管理报表摘要"}</h3>
            </div>
          </div>
          <div className="statement-kpi-list">
            {Object.entries(bundle?.management_summary.key_metrics ?? {}).map(([label, value]) => (
              <span key={label}>{label} {value}</span>
            ))}
          </div>
          <div className="statement-summary-list">
            {(bundle?.management_summary.highlights ?? ["正在生成管理摘要"]).map((item) => (
              <p key={item}>{item}</p>
            ))}
          </div>
          <div className="statement-risk-list">
            {(bundle?.management_summary.risks ?? []).map((item) => (
              <p key={item}>{item}</p>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}

function StatementTable({ title, period, items, totals }: StatementTableProps) {
  return (
    <section className="panel statement-table-panel">
      <div className="panel-header">
        <div>
          <span className="eyebrow">{period}</span>
          <h3>{title}</h3>
        </div>
      </div>
      <div className="voucher-table-wrap">
        <table className="voucher-table statement-table">
          <thead>
            <tr>
              <th>项目</th>
              <th>金额</th>
              <th>取数口径</th>
            </tr>
          </thead>
          <tbody>
            {items.length ? items.map((item) => (
              <tr key={item.code}>
                <td>{item.name}</td>
                <td>{money(item.amount)}</td>
                <td>{item.formula}</td>
              </tr>
            )) : (
              <tr>
                <td colSpan={3}>暂无报表项目</td>
              </tr>
            )}
          </tbody>
          <tfoot>
            {totals.map((total) => (
              <tr key={total.label}>
                <td>{total.label}</td>
                <td>{money(total.value)}</td>
                <td>自动汇总</td>
              </tr>
            ))}
          </tfoot>
        </table>
      </div>
    </section>
  );
}
