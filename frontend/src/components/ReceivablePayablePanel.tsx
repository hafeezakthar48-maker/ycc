import { useEffect, useMemo, useState } from "react";
import { fetchCounterpartyAging, fetchCounterpartyBalances } from "../services/dashboardApi";
import type { CounterpartyAgingResponse, CounterpartyBalanceResponse, OpenItemType } from "../types/receivablePayable";

interface ReceivablePayablePanelProps {
  period: string;
}

function money(value: string | number) {
  return Number(value).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function periodEndDate(period: string) {
  const [yearText, monthText] = period.split("-");
  const year = Number(yearText);
  const month = Number(monthText);
  const endDate = new Date(year, month, 0);
  return `${endDate.getFullYear()}-${String(endDate.getMonth() + 1).padStart(2, "0")}-${String(endDate.getDate()).padStart(2, "0")}`;
}

function typeLabel(openItemType: OpenItemType) {
  return openItemType === "receivable" ? "应收" : "应付";
}

export default function ReceivablePayablePanel({ period }: ReceivablePayablePanelProps) {
  const [openItemType, setOpenItemType] = useState<OpenItemType>("receivable");
  const [balances, setBalances] = useState<CounterpartyBalanceResponse | null>(null);
  const [aging, setAging] = useState<CounterpartyAgingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const asOfDate = useMemo(() => periodEndDate(period), [period]);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setIsLoading(true);
    Promise.all([
      fetchCounterpartyBalances("default", period, openItemType),
      fetchCounterpartyAging("default", period, openItemType, asOfDate)
    ])
      .then(([balancePayload, agingPayload]) => {
        if (cancelled) {
          return;
        }
        setBalances(balancePayload);
        setAging(agingPayload);
      })
      .catch((rpError) => {
        if (!cancelled) {
          setError(rpError instanceof Error ? rpError.message : "往来核算读取失败");
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
  }, [period, openItemType, asOfDate]);

  return (
    <section id="receivable-payable-panel" className="receivable-payable-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">往来核算</span>
          <h2>应收应付余额与账龄</h2>
        </div>
        <div className="statement-actions">
          <button
            type="button"
            className={openItemType === "receivable" ? "" : "button-secondary"}
            onClick={() => setOpenItemType("receivable")}
          >
            应收
          </button>
          <button
            type="button"
            className={openItemType === "payable" ? "" : "button-secondary"}
            onClick={() => setOpenItemType("payable")}
          >
            应付
          </button>
        </div>
      </div>

      {error ? <p className="inline-error">{error}</p> : null}

      <div className="ledger-summary-grid">
        <article>
          <span>{typeLabel(openItemType)}余额</span>
          <strong>{money(balances?.total_base_balance ?? 0)}</strong>
        </article>
        <article>
          <span>往来对象</span>
          <strong>{balances?.item_count ?? 0}</strong>
        </article>
        <article>
          <span>账龄余额</span>
          <strong>{money(aging?.total_base_balance ?? 0)}</strong>
        </article>
        <article>
          <span>截止日</span>
          <strong>{isLoading ? "读取中" : asOfDate}</strong>
        </article>
      </div>

      <div className="receivable-payable-grid">
        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">余额</span>
              <h3>{openItemType === "receivable" ? "客户应收" : "供应商应付"}</h3>
            </div>
          </div>
          <div className="voucher-table-wrap">
            <table className="voucher-table receivable-payable-table">
              <thead>
                <tr>
                  <th>往来对象</th>
                  <th>币种</th>
                  <th>本位币余额</th>
                  <th>未清项</th>
                </tr>
              </thead>
              <tbody>
                {(balances?.items ?? []).map((item) => (
                  <tr key={`${item.counterparty_type}-${item.counterparty_code}-${item.currency}`}>
                    <td>{item.counterparty_name}</td>
                    <td>{item.currency}</td>
                    <td>{money(item.base_balance)}</td>
                    <td>{item.open_item_count}</td>
                  </tr>
                ))}
                {balances && balances.items.length === 0 ? (
                  <tr>
                    <td colSpan={4}>当前期间暂无{typeLabel(openItemType)}未清项</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">账龄</span>
              <h3>账龄分布</h3>
            </div>
          </div>
          <div className="voucher-table-wrap">
            <table className="voucher-table receivable-payable-table">
              <thead>
                <tr>
                  <th>账龄</th>
                  <th>金额</th>
                  <th>未清项</th>
                </tr>
              </thead>
              <tbody>
                {(aging?.buckets ?? []).map((bucket) => (
                  <tr key={bucket.bucket_code}>
                    <td>{bucket.bucket_code}</td>
                    <td>{money(bucket.amount)}</td>
                    <td>{bucket.open_item_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </section>
  );
}
