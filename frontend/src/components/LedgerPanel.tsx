import { useEffect, useMemo, useState } from "react";
import {
  closeAccountingPeriod,
  fetchAccountBalanceTable,
  fetchAccountSets,
  fetchAccountingPeriods,
  fetchDetailLedger,
  fetchGeneralLedger,
  reopenAccountingPeriod
} from "../services/dashboardApi";
import type {
  AccountBalanceTableResponse,
  AccountingPeriodItem,
  AccountSetItem,
  DetailLedgerResponse,
  GeneralLedgerResponse,
  LedgerAccountSummary,
  MoneyValue
} from "../types/ledger";

interface LedgerPanelProps {
  period: string;
}

function money(value: MoneyValue) {
  return Number(value).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function periodStatusLabel(period: AccountingPeriodItem | null) {
  if (!period) {
    return "读取中";
  }
  return period.status === "closed" ? "已关闭" : "开放";
}

function ledgerSourceLabel(source?: string) {
  return source === "formal_journal_entries" ? "正式分录" : "MVP凭证工作流";
}

function originalCurrencyText(line: { currency: string; original_amount: MoneyValue; exchange_rate: MoneyValue }) {
  if (line.currency === "CNY") {
    return null;
  }
  return `${money(line.original_amount)} ${line.currency} @ ${line.exchange_rate}`;
}

export default function LedgerPanel({ period }: LedgerPanelProps) {
  const [generalLedger, setGeneralLedger] = useState<GeneralLedgerResponse | null>(null);
  const [balanceTable, setBalanceTable] = useState<AccountBalanceTableResponse | null>(null);
  const [detailLedger, setDetailLedger] = useState<DetailLedgerResponse | null>(null);
  const [accountSets, setAccountSets] = useState<AccountSetItem[]>([]);
  const [accountingPeriods, setAccountingPeriods] = useState<AccountingPeriodItem[]>([]);
  const [selectedAccountSetId, setSelectedAccountSetId] = useState("default");
  const [selectedAccountCode, setSelectedAccountCode] = useState("6602");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [periodAction, setPeriodAction] = useState<"close" | "reopen" | null>(null);

  const selectedAccount = useMemo(
    () => generalLedger?.accounts.find((account) => account.account_code === selectedAccountCode) ?? null,
    [generalLedger, selectedAccountCode]
  );
  const selectedAccountSet = accountSets.find((accountSet) => accountSet.id === selectedAccountSetId) ?? accountSets[0] ?? null;
  const currentPeriod = useMemo(
    () => accountingPeriods.find((accountingPeriod) => (
      accountingPeriod.period === period && accountingPeriod.account_set_id === selectedAccountSetId
    )) ?? null,
    [accountingPeriods, period, selectedAccountSetId]
  );
  const isPeriodBusy = periodAction !== null;

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    Promise.all([
      fetchGeneralLedger(period, undefined, undefined, undefined, selectedAccountSetId),
      fetchAccountBalanceTable(period, undefined, undefined, undefined, selectedAccountSetId),
      fetchDetailLedger(period, selectedAccountCode, undefined, undefined, undefined, selectedAccountSetId),
      fetchAccountSets(),
      fetchAccountingPeriods(selectedAccountSetId)
    ])
      .then(([general, balances, detail, accountSetPayload, periodPayload]) => {
        if (cancelled) {
          return;
        }
        setGeneralLedger(general);
        setBalanceTable(balances);
        setDetailLedger(detail);
        setAccountSets(accountSetPayload.account_sets);
        setAccountingPeriods(periodPayload.periods);
      })
      .catch((ledgerError) => {
        if (!cancelled) {
          setError(ledgerError instanceof Error ? ledgerError.message : "账簿读取失败");
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
  }, [period, selectedAccountCode, selectedAccountSetId]);

  useEffect(() => {
    const fallbackAccountSetId = accountSets.find((accountSet) => accountSet.is_default)?.id ?? accountSets[0]?.id;
    if (fallbackAccountSetId && !accountSets.some((accountSet) => accountSet.id === selectedAccountSetId)) {
      setSelectedAccountSetId(fallbackAccountSetId);
    }
  }, [accountSets, selectedAccountSetId]);

  useEffect(() => {
    const firstAccountCode = generalLedger?.accounts[0]?.account_code;
    if (firstAccountCode && !generalLedger.accounts.some((account) => account.account_code === selectedAccountCode)) {
      setSelectedAccountCode(firstAccountCode);
    }
  }, [generalLedger, selectedAccountCode]);

  function updatePeriod(nextPeriod: AccountingPeriodItem) {
    setAccountingPeriods((items) => {
      if (items.some((item) => item.period === nextPeriod.period && item.account_set_id === nextPeriod.account_set_id)) {
        return items.map((item) => (
          item.period === nextPeriod.period && item.account_set_id === nextPeriod.account_set_id ? nextPeriod : item
        ));
      }
      return [nextPeriod, ...items];
    });
  }

  function runPeriodAction(
    actionName: "close" | "reopen",
    action: () => Promise<AccountingPeriodItem>
  ) {
    setPeriodAction(actionName);
    setError(null);
    action()
      .then(updatePeriod)
      .catch((periodError) => {
        setError(periodError instanceof Error ? periodError.message : "会计期间状态更新失败");
      })
      .finally(() => {
        setPeriodAction(null);
      });
  }

  function handleClosePeriod() {
    runPeriodAction("close", () => closeAccountingPeriod(period, "财务主管", undefined, undefined, undefined, selectedAccountSetId));
  }

  function handleReopenPeriod() {
    runPeriodAction("reopen", () => reopenAccountingPeriod(period, "财务主管", undefined, undefined, undefined, selectedAccountSetId));
  }

  return (
    <section id="ledger-panel" className="ledger-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">账簿读模型</span>
          <h2>总账、明细账与科目余额表</h2>
        </div>
        <div className="qa-status-strip">
          <span>{period}</span>
          <span>{ledgerSourceLabel(generalLedger?.source)}</span>
          <span>{generalLedger?.balanced ? "借贷平衡" : "待复核"}</span>
          <span>{isLoading ? "读取中" : `${generalLedger?.voucher_count ?? 0} 张已审核凭证`}</span>
        </div>
      </div>

      {error ? <p className="inline-error">{error}</p> : null}

      <div className="period-status-strip">
        <article>
          <span>账套</span>
          <select
            className="account-set-select"
            value={selectedAccountSetId}
            onChange={(event) => setSelectedAccountSetId(event.target.value)}
            aria-label="选择账套"
          >
            {(accountSets.length ? accountSets : [{ id: selectedAccountSetId, name: selectedAccountSet?.name ?? "默认账套" } as AccountSetItem]).map((accountSet) => (
              <option value={accountSet.id} key={accountSet.id}>{accountSet.name}</option>
            ))}
          </select>
        </article>
        <article>
          <span>会计期间</span>
          <strong>{period}</strong>
        </article>
        <article>
          <span>期间状态</span>
          <strong>{periodStatusLabel(currentPeriod)}</strong>
        </article>
        <article>
          <span>过账进度</span>
          <strong>{currentPeriod ? `${currentPeriod.posted_voucher_count}/${currentPeriod.voucher_count}` : "读取中"}</strong>
        </article>
        <div className="period-actions">
          <button
            type="button"
            className="button-secondary"
            onClick={handleClosePeriod}
            disabled={isPeriodBusy || currentPeriod?.status === "closed"}
          >
            关账
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={handleReopenPeriod}
            disabled={isPeriodBusy || currentPeriod?.status !== "closed"}
          >
            重开
          </button>
        </div>
      </div>

      <div className="ledger-summary-grid">
        <article>
          <span>借方合计</span>
          <strong>{money(generalLedger?.total_debit ?? 0)}</strong>
        </article>
        <article>
          <span>贷方合计</span>
          <strong>{money(generalLedger?.total_credit ?? 0)}</strong>
        </article>
        <article>
          <span>分录数</span>
          <strong>{generalLedger?.entry_count ?? 0}</strong>
        </article>
        <article>
          <span>科目数</span>
          <strong>{balanceTable?.account_count ?? 0}</strong>
        </article>
      </div>

      <div className="ledger-grid">
        <section className="panel ledger-accounts-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">总账</span>
              <h3>科目汇总</h3>
            </div>
          </div>
          <LedgerAccountTable
            accounts={generalLedger?.accounts ?? []}
            selectedAccountCode={selectedAccountCode}
            onSelect={setSelectedAccountCode}
          />
        </section>

        <section className="panel ledger-detail-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">明细账</span>
              <h3>{selectedAccount?.account_name ?? detailLedger?.account_name ?? selectedAccountCode}</h3>
            </div>
            <strong className="risk-count">{money(detailLedger?.balance_amount ?? 0)}</strong>
          </div>
          <div className="voucher-table-wrap">
            <table className="voucher-table ledger-table">
              <thead>
                <tr>
                  <th>日期</th>
                  <th>凭证号</th>
                  <th>摘要</th>
                  <th>借方</th>
                  <th>贷方</th>
                </tr>
              </thead>
              <tbody>
                {detailLedger?.lines.length ? detailLedger.lines.map((line) => (
                  <tr key={`${line.voucher_id}-${line.account_code}-${line.explanation}`}>
                    <td>{line.voucher_date}</td>
                    <td>{line.voucher_number}</td>
                    <td>{line.summary}</td>
                    <td>
                      {money(line.debit_amount)}
                      {originalCurrencyText(line) ? <small>{originalCurrencyText(line)}</small> : null}
                    </td>
                    <td>
                      {money(line.credit_amount)}
                      {originalCurrencyText(line) ? <small>{originalCurrencyText(line)}</small> : null}
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={5}>暂无已审核凭证明细</td>
                  </tr>
                )}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={3}>合计</td>
                  <td>{money(detailLedger?.debit_total ?? 0)}</td>
                  <td>{money(detailLedger?.credit_total ?? 0)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </section>

        <section className="panel ledger-balance-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">科目余额表</span>
              <h3>{balanceTable?.balanced ? "平衡" : "待复核"}</h3>
            </div>
          </div>
          <LedgerAccountTable
            accounts={balanceTable?.accounts ?? []}
            selectedAccountCode={selectedAccountCode}
            onSelect={setSelectedAccountCode}
          />
        </section>
      </div>
    </section>
  );
}

function LedgerAccountTable({
  accounts,
  selectedAccountCode,
  onSelect
}: {
  accounts: LedgerAccountSummary[];
  selectedAccountCode: string;
  onSelect: (accountCode: string) => void;
}) {
  return (
    <div className="voucher-table-wrap">
      <table className="voucher-table ledger-table">
        <thead>
          <tr>
            <th>科目</th>
            <th>借方</th>
            <th>贷方</th>
            <th>余额</th>
            <th>分录</th>
          </tr>
        </thead>
        <tbody>
          {accounts.length ? accounts.map((account) => (
            <tr key={account.account_code}>
              <td>
                <button
                  type="button"
                  className={`ledger-account-button ${selectedAccountCode === account.account_code ? "ledger-account-button--active" : ""}`}
                  onClick={() => onSelect(account.account_code)}
                >
                  <strong>{account.account_code}</strong>
                  <span>{account.account_name}</span>
                </button>
              </td>
              <td>{money(account.debit_total)}</td>
              <td>{money(account.credit_total)}</td>
              <td>{account.balance_direction} {money(account.balance_amount)}</td>
              <td>{account.entry_count}</td>
            </tr>
          )) : (
            <tr>
              <td colSpan={5}>暂无已审核凭证</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
