import { useEffect, useMemo, useState } from "react";
import {
  fetchTaxFilingWorksheet,
  fetchVatLedger,
  postIncomeTaxAccrual,
  postSurtaxAccrual,
  postTaxPayment,
  postUnpaidVatTransfer
} from "../services/dashboardApi";
import type { TaxFilingWorksheet, VatDirection, VatLedgerLine, VatLedgerLineListResponse } from "../types/taxAccounting";

interface TaxAccountingPanelProps {
  period: string;
}

const directionLabels: Record<VatDirection, string> = {
  input: "进项税额",
  output: "销项税额",
  input_transfer_out: "进项税额转出"
};

const emptyWorksheet: TaxFilingWorksheet = {
  account_set_id: "default",
  period: "",
  output_vat: "0.00",
  input_vat: "0.00",
  input_transfer_out: "0.00",
  vat_payable: "0.00",
  surtax_payable: "0.00",
  income_tax_payable: "0.00"
};

function money(value: string | number | null | undefined) {
  return Number(value ?? 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function directionLabel(direction: VatDirection) {
  return directionLabels[direction] ?? direction;
}

function nextPeriod(period: string) {
  const [yearValue, monthValue] = period.split("-").map(Number);
  if (!yearValue || !monthValue) {
    return period;
  }
  const nextMonth = monthValue === 12 ? 1 : monthValue + 1;
  const nextYear = monthValue === 12 ? yearValue + 1 : yearValue;
  return `${nextYear}-${String(nextMonth).padStart(2, "0")}`;
}

export default function TaxAccountingPanel({ period }: TaxAccountingPanelProps) {
  const [selectedPeriod, setSelectedPeriod] = useState(period);
  const [ledger, setLedger] = useState<VatLedgerLineListResponse | null>(null);
  const [worksheet, setWorksheet] = useState<TaxFilingWorksheet | null>(null);
  const [vatTransferAmount, setVatTransferAmount] = useState("0.00");
  const [surtaxVatBase, setSurtaxVatBase] = useState("0.00");
  const [incomeTaxAmount, setIncomeTaxAmount] = useState("0.00");
  const [taxPaymentAmount, setTaxPaymentAmount] = useState("0.00");
  const [taxAccountCode, setTaxAccountCode] = useState("222102");
  const [bankAccountCode, setBankAccountCode] = useState("1002");
  const [paymentPeriod, setPaymentPeriod] = useState(nextPeriod(period));
  const [lastAction, setLastAction] = useState("待处理");
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  const currentWorksheet = worksheet ?? emptyWorksheet;
  const vatLines = ledger?.lines ?? [];
  const ledgerTotals = useMemo(() => ({
    input: totalVat(vatLines, "input"),
    output: totalVat(vatLines, "output"),
    input_transfer_out: totalVat(vatLines, "input_transfer_out")
  }), [vatLines]);

  useEffect(() => {
    setSelectedPeriod(period);
  }, [period]);

  useEffect(() => {
    setPaymentPeriod(nextPeriod(selectedPeriod));
    refreshTaxData(selectedPeriod);
  }, [selectedPeriod]);

  function refreshTaxData(targetPeriod = selectedPeriod) {
    setIsBusy(true);
    setError(null);
    return Promise.all([
      fetchVatLedger("default", targetPeriod),
      fetchTaxFilingWorksheet("default", targetPeriod)
    ])
      .then(([ledgerPayload, worksheetPayload]) => {
        setLedger(ledgerPayload);
        setWorksheet(worksheetPayload);
        setVatTransferAmount(String(worksheetPayload.vat_payable));
        setSurtaxVatBase(String(worksheetPayload.vat_payable));
        setIncomeTaxAmount(String(worksheetPayload.income_tax_payable));
        setTaxPaymentAmount(String(worksheetPayload.vat_payable));
      })
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "税务核算读取失败"))
      .finally(() => setIsBusy(false));
  }

  function runTaxAction(action: () => Promise<unknown>, label: string) {
    setIsBusy(true);
    setError(null);
    action()
      .then(() => {
        setLastAction(label);
        return refreshTaxData();
      })
      .catch((actionError) => setError(actionError instanceof Error ? actionError.message : `${label}失败`))
      .finally(() => setIsBusy(false));
  }

  function handleUnpaidVatTransfer() {
    runTaxAction(
      () => postUnpaidVatTransfer({ account_set_id: "default", period: selectedPeriod, amount: vatTransferAmount }),
      "tax_unpaid_vat_transfer"
    );
  }

  function handleSurtaxAccrual() {
    runTaxAction(
      () => postSurtaxAccrual({ account_set_id: "default", period: selectedPeriod, vat_payable: surtaxVatBase }),
      "tax_surtax_accrual"
    );
  }

  function handleIncomeTaxAccrual() {
    runTaxAction(
      () => postIncomeTaxAccrual({ account_set_id: "default", period: selectedPeriod, amount: incomeTaxAmount }),
      "tax_income_tax_accrual"
    );
  }

  function handleTaxPayment() {
    runTaxAction(
      () => postTaxPayment({
        account_set_id: "default",
        period: paymentPeriod,
        tax_account_code: taxAccountCode,
        amount: taxPaymentAmount,
        bank_account_code: bankAccountCode
      }),
      "tax_payment"
    );
  }

  return (
    <section id="tax-accounting-panel" className="tax-accounting-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">税务核算与申报底稿</span>
          <h2>增值税台账、附加税计提与纳税支付</h2>
        </div>
        <div className="qa-status-strip">
          <span>{selectedPeriod}</span>
          <span>{lastAction}</span>
          <span>{ledger?.total ?? 0} 条台账</span>
        </div>
      </div>

      {error ? <p className="inline-error">{error}</p> : null}

      <div className="period-close-toolbar tax-accounting-toolbar">
        <label>
          <span>期间</span>
          <input value={selectedPeriod} onChange={(event) => setSelectedPeriod(event.target.value)} />
        </label>
        <label>
          <span>未交增值税</span>
          <input value={vatTransferAmount} onChange={(event) => setVatTransferAmount(event.target.value)} />
        </label>
        <label>
          <span>附加税税基</span>
          <input value={surtaxVatBase} onChange={(event) => setSurtaxVatBase(event.target.value)} />
        </label>
        <label>
          <span>所得税金额</span>
          <input value={incomeTaxAmount} onChange={(event) => setIncomeTaxAmount(event.target.value)} />
        </label>
        <button type="button" className="button-secondary" onClick={() => refreshTaxData()} disabled={isBusy}>
          刷新
        </button>
      </div>

      <div className="period-close-toolbar tax-accounting-actionbar">
        <button type="button" onClick={handleUnpaidVatTransfer} disabled={isBusy}>结转未交增值税</button>
        <button type="button" onClick={handleSurtaxAccrual} disabled={isBusy}>计提附加税</button>
        <button type="button" className="button-secondary" onClick={handleIncomeTaxAccrual} disabled={isBusy}>计提所得税</button>
        <label>
          <span>缴款期间</span>
          <input value={paymentPeriod} onChange={(event) => setPaymentPeriod(event.target.value)} />
        </label>
        <label>
          <span>税费科目</span>
          <select value={taxAccountCode} onChange={(event) => setTaxAccountCode(event.target.value)}>
            <option value="222102">未交增值税</option>
            <option value="222103">城建税及教育费附加</option>
            <option value="222104">企业所得税</option>
          </select>
        </label>
        <label>
          <span>银行科目</span>
          <input value={bankAccountCode} onChange={(event) => setBankAccountCode(event.target.value)} />
        </label>
        <label>
          <span>缴款金额</span>
          <input value={taxPaymentAmount} onChange={(event) => setTaxPaymentAmount(event.target.value)} />
        </label>
        <button type="button" onClick={handleTaxPayment} disabled={isBusy}>缴款入账</button>
      </div>

      <div className="period-close-summary-grid tax-accounting-summary-grid">
        <article>
          <span>销项税额</span>
          <strong>{money(currentWorksheet.output_vat)}</strong>
        </article>
        <article>
          <span>进项税额</span>
          <strong>{money(currentWorksheet.input_vat)}</strong>
        </article>
        <article>
          <span>进项转出</span>
          <strong>{money(currentWorksheet.input_transfer_out)}</strong>
        </article>
        <article>
          <span>应交增值税</span>
          <strong>{money(currentWorksheet.vat_payable)}</strong>
        </article>
        <article>
          <span>附加税</span>
          <strong>{money(currentWorksheet.surtax_payable)}</strong>
        </article>
        <article>
          <span>企业所得税</span>
          <strong>{money(currentWorksheet.income_tax_payable)}</strong>
        </article>
      </div>

      <div className="period-close-grid tax-accounting-grid">
        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">增值税台账</span>
              <h3>来源分录与发票税额</h3>
            </div>
            <strong>{ledger?.total ?? 0}</strong>
          </div>
          <div className="voucher-table-wrap">
            <table className="voucher-table tax-accounting-vat-table">
              <thead>
                <tr>
                  <th>方向</th>
                  <th>发票号</th>
                  <th>税基</th>
                  <th>税额</th>
                  <th>往来方</th>
                  <th>来源分录</th>
                </tr>
              </thead>
              <tbody>
                {vatLines.length ? vatLines.map((line: VatLedgerLine) => (
                  <tr key={`${line.source_journal_entry_id}-${line.tax_direction}-${line.invoice_no}`}>
                    <td>{directionLabel(line.tax_direction)}</td>
                    <td>{line.invoice_no}</td>
                    <td>{money(line.tax_base)}</td>
                    <td>{money(line.tax_amount)}</td>
                    <td>{line.counterparty_id ?? "-"}</td>
                    <td>{line.source_journal_entry_id}</td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={6}>暂无增值税台账</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">申报底稿</span>
              <h3>税额汇总与计提状态</h3>
            </div>
          </div>
          <div className="voucher-table-wrap">
            <table className="voucher-table tax-accounting-worksheet-table">
              <thead>
                <tr>
                  <th>项目</th>
                  <th>台账金额</th>
                  <th>底稿金额</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>销项税额</td>
                  <td>{money(ledgerTotals.output)}</td>
                  <td>{money(currentWorksheet.output_vat)}</td>
                </tr>
                <tr>
                  <td>进项税额</td>
                  <td>{money(ledgerTotals.input)}</td>
                  <td>{money(currentWorksheet.input_vat)}</td>
                </tr>
                <tr>
                  <td>进项税额转出</td>
                  <td>{money(ledgerTotals.input_transfer_out)}</td>
                  <td>{money(currentWorksheet.input_transfer_out)}</td>
                </tr>
                <tr>
                  <td>应交增值税</td>
                  <td>{money(Math.max(ledgerTotals.output - ledgerTotals.input + ledgerTotals.input_transfer_out, 0))}</td>
                  <td>{money(currentWorksheet.vat_payable)}</td>
                </tr>
                <tr>
                  <td>附加税计提</td>
                  <td>{lastAction === "tax_surtax_accrual" ? "已触发" : "待计提"}</td>
                  <td>{money(currentWorksheet.surtax_payable)}</td>
                </tr>
                <tr>
                  <td>所得税计提</td>
                  <td>{lastAction === "tax_income_tax_accrual" ? "已触发" : "待计提"}</td>
                  <td>{money(currentWorksheet.income_tax_payable)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </section>
  );
}

function totalVat(lines: VatLedgerLine[], direction: VatDirection) {
  return lines
    .filter((line) => line.tax_direction === direction)
    .reduce((total, line) => total + Number(line.tax_amount ?? 0), 0);
}
