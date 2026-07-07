import { useEffect, useMemo, useState } from "react";
import {
  createConsolidationGroup,
  fetchConsolidatedStatements,
  fetchConsolidationEliminations,
  fetchConsolidationGroups,
  fetchConsolidationReportingPackage,
  rebuildConsolidationEliminations
} from "../services/dashboardApi";
import type {
  ConsolidatedStatementResponse,
  ConsolidationEliminationEntry,
  ConsolidationGroup,
  ConsolidationReportingPackage
} from "../types/consolidation";

interface ConsolidationPanelProps {
  period: string;
}

function money(value: string | number | null | undefined) {
  return Number(value ?? 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

const eliminationLabels: Record<string, string> = {
  intercompany_balance: "内部往来",
  intercompany_revenue_cost: "内部交易",
  investment_equity: "投资权益",
  unrealized_profit: "未实现利润"
};

export default function ConsolidationPanel({ period }: ConsolidationPanelProps) {
  const [selectedPeriod, setSelectedPeriod] = useState(period);
  const [groups, setGroups] = useState<ConsolidationGroup[]>([]);
  const [groupId, setGroupId] = useState("group-001");
  const [groupName, setGroupName] = useState("中国财务AI集团");
  const [packageAccountSetId, setPackageAccountSetId] = useState("default");
  const [reportingPackage, setReportingPackage] = useState<ConsolidationReportingPackage | null>(null);
  const [eliminations, setEliminations] = useState<ConsolidationEliminationEntry[]>([]);
  const [statements, setStatements] = useState<ConsolidatedStatementResponse | null>(null);
  const [lastAction, setLastAction] = useState("待处理");
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  const totalEliminationAmount = useMemo(
    () => eliminations.reduce((sum, item) => sum + Number(item.amount ?? 0), 0),
    [eliminations]
  );
  const scopeRows = useMemo(
    () => groups.flatMap((group) => group.entities.map((entity) => ({ group, entity }))),
    [groups]
  );

  useEffect(() => {
    setSelectedPeriod(period);
  }, [period]);

  useEffect(() => {
    refreshConsolidation();
  }, [selectedPeriod, groupId, packageAccountSetId]);

  function refreshConsolidation() {
    setError(null);
    return Promise.all([
      fetchConsolidationGroups(),
      fetchConsolidationReportingPackage(packageAccountSetId, selectedPeriod),
      fetchConsolidationEliminations(groupId, selectedPeriod).catch(() => null),
      fetchConsolidatedStatements(groupId, selectedPeriod).catch(() => null)
    ])
      .then(([groupResponse, packageResponse, eliminationResponse, statementResponse]) => {
        setGroups(groupResponse.groups ?? []);
        setReportingPackage(packageResponse);
        setEliminations(eliminationResponse?.eliminations ?? []);
        setStatements(statementResponse);
      })
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "合并报表读取失败"));
  }

  function runAction(action: () => Promise<unknown>, label: string) {
    setIsBusy(true);
    setError(null);
    action()
      .then(() => {
        setLastAction(label);
        return refreshConsolidation();
      })
      .catch((actionError) => setError(actionError instanceof Error ? actionError.message : `${label}失败`))
      .finally(() => setIsBusy(false));
  }

  function handleCreateGroup() {
    runAction(
      () => createConsolidationGroup({
        group_id: groupId,
        group_name: groupName,
        entities: [
          {
            consolidation_group_id: groupId,
            account_set_id: "default",
            entity_name: "母公司",
            ownership_percentage: "1.000000",
            consolidation_method: "full"
          },
          {
            consolidation_group_id: groupId,
            account_set_id: "cross_border",
            entity_name: "子公司A",
            ownership_percentage: "0.800000",
            consolidation_method: "proportionate"
          }
        ]
      }),
      "consolidation.group.write"
    );
  }

  function handleRebuildEliminations() {
    runAction(
      () => rebuildConsolidationEliminations({
        group_id: groupId,
        period: selectedPeriod,
        intercompany_balance_amount: "50000.00",
        intercompany_revenue_amount: "80000.00",
        intercompany_cost_amount: "60000.00",
        ending_internal_inventory_amount: "100000.00",
        internal_gross_margin_rate: "0.200000",
        investment_amount: "800000.00",
        subsidiary_equity_amount: "1000000.00",
        ownership_percentage: "0.800000"
      }),
      "consolidation.elimination.rebuild"
    );
  }

  return (
    <section id="consolidation-panel" className="consolidation-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">合并报表与抵销工作底稿</span>
          <h2>合并范围、单体报表包与内部交易抵销</h2>
        </div>
        <div className="qa-status-strip">
          <span>{selectedPeriod}</span>
          <span>{lastAction}</span>
          <span>{groups.length} 个集团</span>
        </div>
      </div>

      {error ? <p className="inline-error">{error}</p> : null}

      <div className="period-close-toolbar consolidation-toolbar">
        <label>
          <span>期间</span>
          <input value={selectedPeriod} onChange={(event) => setSelectedPeriod(event.target.value)} />
        </label>
        <label>
          <span>集团编号</span>
          <input value={groupId} onChange={(event) => setGroupId(event.target.value)} />
        </label>
        <label>
          <span>集团名称</span>
          <input value={groupName} onChange={(event) => setGroupName(event.target.value)} />
        </label>
        <label>
          <span>报表包账套</span>
          <select value={packageAccountSetId} onChange={(event) => setPackageAccountSetId(event.target.value)}>
            <option value="default">default</option>
            <option value="cross_border">cross_border</option>
          </select>
        </label>
        <button type="button" className="button-secondary" onClick={() => refreshConsolidation()} disabled={isBusy}>刷新</button>
        <button type="button" onClick={handleCreateGroup} disabled={isBusy}>保存范围</button>
        <button type="button" onClick={handleRebuildEliminations} disabled={isBusy}>重建抵销</button>
      </div>

      <div className="period-close-summary-grid consolidation-summary-grid">
        <article>
          <span>抵销分录</span>
          <strong>{eliminations.length}</strong>
        </article>
        <article>
          <span>抵销金额</span>
          <strong>{money(totalEliminationAmount)}</strong>
        </article>
        <article>
          <span>少数股东权益</span>
          <strong>{money(statements?.minority_interest)}</strong>
        </article>
      </div>

      <div className="period-close-grid consolidation-grid">
        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">合并范围</span>
              <h3>集团、账套与持股比例</h3>
            </div>
            <strong>{groups.length}</strong>
          </div>
          <div className="voucher-table-wrap">
            <table className="voucher-table consolidation-scope-table">
              <thead>
                <tr>
                  <th>集团</th>
                  <th>账套</th>
                  <th>主体</th>
                  <th>持股</th>
                  <th>方法</th>
                </tr>
              </thead>
              <tbody>
                {scopeRows.length ? scopeRows.map(({ group, entity }) => (
                  <tr key={`${group.group_id}-${entity.account_set_id}`}>
                    <td>{group.group_name}</td>
                    <td>{entity.account_set_id}</td>
                    <td>{entity.entity_name}</td>
                    <td>{(Number(entity.ownership_percentage) * 100).toFixed(2)}%</td>
                    <td>{entity.consolidation_method}</td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={5}>暂无合并范围</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">单体报表包</span>
              <h3>{reportingPackage?.account_set_id ?? packageAccountSetId}</h3>
            </div>
            <strong>{reportingPackage?.period ?? selectedPeriod}</strong>
          </div>
          <div className="statement-kpi-grid">
            <article>
              <span>资产总额</span>
              <strong>{money(reportingPackage?.balance_sheet.total_assets)}</strong>
            </article>
            <article>
              <span>营业收入</span>
              <strong>{money(reportingPackage?.income_statement.total_revenue)}</strong>
            </article>
            <article>
              <span>现金净流量</span>
              <strong>{money(reportingPackage?.cash_flow_statement.net_cash_flow)}</strong>
            </article>
          </div>
        </section>

        <section className="panel panel--wide">
          <div className="panel-header">
            <div>
              <span className="eyebrow">抵销工作底稿</span>
              <h3>内部往来、内部交易与投资权益</h3>
            </div>
            <strong>{eliminations.length}</strong>
          </div>
          <div className="voucher-table-wrap">
            <table className="voucher-table consolidation-elimination-table">
              <thead>
                <tr>
                  <th>类型</th>
                  <th>借方</th>
                  <th>贷方</th>
                  <th>金额</th>
                  <th>说明</th>
                </tr>
              </thead>
              <tbody>
                {eliminations.length ? eliminations.map((entry) => (
                  <tr key={entry.elimination_id}>
                    <td>{eliminationLabels[entry.elimination_type] ?? entry.elimination_type}</td>
                    <td>{entry.debit_account_code}</td>
                    <td>{entry.credit_account_code}</td>
                    <td>{money(entry.amount)}</td>
                    <td>{entry.explanation}</td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={5}>暂无抵销分录</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel panel--wide">
          <div className="panel-header">
            <div>
              <span className="eyebrow">合并报表</span>
              <h3>资产负债、利润与现金流</h3>
            </div>
            <strong>{statements?.elimination_count ?? 0}</strong>
          </div>
          <div className="voucher-table-wrap">
            <table className="voucher-table consolidation-statement-table">
              <thead>
                <tr>
                  <th>项目</th>
                  <th>金额</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>合并资产总额</td>
                  <td>{money(statements?.balance_sheet.total_assets)}</td>
                </tr>
                <tr>
                  <td>合并营业收入</td>
                  <td>{money(statements?.income_statement.total_revenue)}</td>
                </tr>
                <tr>
                  <td>合并净利润</td>
                  <td>{money(statements?.income_statement.net_profit)}</td>
                </tr>
                <tr>
                  <td>合并现金净流量</td>
                  <td>{money(statements?.cash_flow_statement.net_cash_flow)}</td>
                </tr>
                <tr>
                  <td>少数股东权益</td>
                  <td>{money(statements?.minority_interest)}</td>
                </tr>
                <tr>
                  <td>少数股东损益</td>
                  <td>{money(statements?.minority_profit)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </section>
  );
}
