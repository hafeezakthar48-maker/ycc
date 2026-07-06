import { useEffect, useMemo, useState } from "react";
import { fetchDefaultStatementMappingSet } from "../services/dashboardApi";
import type { StatementMappingRule, StatementMappingSetResponse, StatementType } from "../types/statementMapping";

const statementLabels: Record<StatementType, string> = {
  balance_sheet: "资产负债表",
  income_statement: "利润表",
  cash_flow_statement: "现金流量表",
  equity_statement: "所有者权益变动表"
};

const sourceLabels: Record<string, string> = {
  account_balance: "科目余额",
  account_activity: "期间发生额",
  formula: "公式",
  cash_flow_item: "现金流项目",
  period_close_result: "期末处理"
};

export default function StatementMappingPanel() {
  const [payload, setPayload] = useState<StatementMappingSetResponse | null>(null);
  const [activeStatement, setActiveStatement] = useState<StatementType>("balance_sheet");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchDefaultStatementMappingSet()
      .then((result) => {
        if (!cancelled) {
          setPayload(result);
        }
      })
      .catch((mappingError) => {
        if (!cancelled) {
          setError(mappingError instanceof Error ? mappingError.message : "报表映射读取失败");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const rules = useMemo(
    () => (payload?.rules ?? []).filter((rule) => rule.statement_type === activeStatement),
    [payload, activeStatement]
  );

  return (
    <section id="statement-mapping-panel" className="statement-mapping-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">报表映射</span>
          <h2>{payload?.mapping_set.mapping_set_name ?? "中国企业会计准则通用报表映射"}</h2>
        </div>
        <div className="statement-mapping-meta">
          <span>{payload?.mapping_set.base_currency ?? "CNY"}</span>
          <span>{rules.length} 条规则</span>
        </div>
      </div>
      {error ? <p className="inline-error">{error}</p> : null}
      <div className="statement-tab-list" role="tablist" aria-label="报表映射类型">
        {(Object.keys(statementLabels) as StatementType[]).map((type) => (
          <button
            key={type}
            type="button"
            className={activeStatement === type ? "button-primary" : "button-secondary"}
            onClick={() => setActiveStatement(type)}
          >
            {statementLabels[type]}
          </button>
        ))}
      </div>
      <div className="voucher-table-wrap">
        <table className="voucher-table statement-mapping-table">
          <thead>
            <tr>
              <th>项目编码</th>
              <th>项目名称</th>
              <th>来源</th>
              <th>科目/项目</th>
              <th>公式</th>
            </tr>
          </thead>
          <tbody>
            {rules.length ? rules.map((rule: StatementMappingRule) => (
              <tr key={rule.rule_id}>
                <td>{rule.line_code}</td>
                <td>{rule.line_name}</td>
                <td>{sourceLabels[rule.source_type] ?? rule.source_type}</td>
                <td>{rule.account_prefixes.join(" / ") || rule.cash_flow_item_codes.join(" / ") || "-"}</td>
                <td>{rule.formula || rule.normal_side}</td>
              </tr>
            )) : (
              <tr>
                <td colSpan={5}>正在读取报表映射</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
