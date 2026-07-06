import { FormEvent, useEffect, useState } from "react";
import { generateVoucherDraft } from "../services/dashboardApi";
import type { VoucherDraftRequest, VoucherDraftResponse, VoucherLine } from "../types/voucherDraft";

const defaultRequest: VoucherDraftRequest = {
  business_type: "expense_purchase",
  voucher_date: "2026-06-30",
  counterparty: "上海云智科技有限公司",
  amount: 1000,
  tax_amount: 60,
  total_amount_with_tax: 1060,
  payment_status: "unpaid",
  memo: "办公服务费"
};

const businessTypes = [
  { value: "expense_purchase", label: "费用采购" },
  { value: "inventory_purchase", label: "库存采购" },
  { value: "sales_revenue", label: "销售收入" }
];

const paymentStatusOptions = [
  { value: "unpaid", label: "未结算" },
  { value: "paid", label: "已银行结算" }
];

function money(value: number | string) {
  return Number(value).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function lineDebit(line: VoucherLine) {
  return line.direction === "借" ? money(line.amount) : "";
}

function lineCredit(line: VoucherLine) {
  return line.direction === "贷" ? money(line.amount) : "";
}

export default function VoucherDraftPanel() {
  const [form, setForm] = useState<VoucherDraftRequest>(defaultRequest);
  const [result, setResult] = useState<VoucherDraftResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  async function runDraft(nextForm = form) {
    setIsBusy(true);
    setError(null);
    try {
      setResult(await generateVoucherDraft(nextForm));
    } catch (draftError) {
      setError(draftError instanceof Error ? draftError.message : "凭证草稿生成失败");
    } finally {
      setIsBusy(false);
    }
  }

  useEffect(() => {
    runDraft(defaultRequest);
  }, []);

  function updateField(key: keyof VoucherDraftRequest, value: string) {
    setForm((current) => {
      if (key === "amount" || key === "tax_amount" || key === "total_amount_with_tax") {
        const numericValue = Number(value);
        return { ...current, [key]: Number.isFinite(numericValue) ? numericValue : 0 };
      }
      return { ...current, [key]: value };
    });
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    runDraft();
  }

  return (
    <section id="voucher-draft" className="voucher-section">
      <div className="section-heading">
        <div>
          <span className="eyebrow">AI 凭证草稿</span>
          <h2>从业务数据生成可复核分录</h2>
        </div>
        <div className="qa-status-strip">
          <span>借贷平衡</span>
          <span>人工复核</span>
          <span>不自动入账</span>
        </div>
      </div>

      <form className="voucher-form" onSubmit={handleSubmit}>
        <label>
          业务场景
          <select value={form.business_type} onChange={(event) => updateField("business_type", event.target.value)}>
            {businessTypes.map((item) => (
              <option value={item.value} key={item.value}>{item.label}</option>
            ))}
          </select>
        </label>
        <label>
          凭证日期
          <input type="date" value={form.voucher_date} onChange={(event) => updateField("voucher_date", event.target.value)} />
        </label>
        <label>
          交易对方
          <input value={form.counterparty} onChange={(event) => updateField("counterparty", event.target.value)} />
        </label>
        <label>
          不含税金额
          <input type="number" min={0} step={0.01} value={form.amount} onChange={(event) => updateField("amount", event.target.value)} />
        </label>
        <label>
          税额
          <input type="number" min={0} step={0.01} value={form.tax_amount} onChange={(event) => updateField("tax_amount", event.target.value)} />
        </label>
        <label>
          价税合计
          <input type="number" min={0} step={0.01} value={form.total_amount_with_tax} onChange={(event) => updateField("total_amount_with_tax", event.target.value)} />
        </label>
        <label>
          结算状态
          <select value={form.payment_status} onChange={(event) => updateField("payment_status", event.target.value)}>
            {paymentStatusOptions.map((item) => (
              <option value={item.value} key={item.value}>{item.label}</option>
            ))}
          </select>
        </label>
        <label>
          摘要
          <input value={form.memo} onChange={(event) => updateField("memo", event.target.value)} />
        </label>
        <button type="submit" disabled={isBusy}>{isBusy ? "生成中..." : "生成凭证草稿"}</button>
      </form>

      {error ? <p className="inline-error">{error}</p> : null}

      {result ? (
        <div className="voucher-result-grid">
          <section className="panel voucher-lines-panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">{result.scenario_label}</span>
                <h3>{result.summary}</h3>
              </div>
              <div className={`qa-risk ${result.balanced ? "qa-risk--low" : "qa-risk--high"}`}>
                {result.balanced ? "已平衡" : "未平衡"}
              </div>
            </div>
            <div className="voucher-table-wrap">
              <table className="voucher-table">
                <thead>
                  <tr>
                    <th>方向</th>
                    <th>科目编码</th>
                    <th>科目名称</th>
                    <th>借方</th>
                    <th>贷方</th>
                    <th>说明</th>
                  </tr>
                </thead>
                <tbody>
                  {result.lines.map((line) => (
                    <tr key={`${line.direction}-${line.account_code}-${line.account_name}`}>
                      <td>{line.direction}</td>
                      <td>{line.account_code}</td>
                      <td>{line.account_name}</td>
                      <td>{lineDebit(line)}</td>
                      <td>{lineCredit(line)}</td>
                      <td>{line.explanation}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td colSpan={3}>合计</td>
                    <td>{money(result.debit_total)}</td>
                    <td>{money(result.credit_total)}</td>
                    <td>{result.requires_human_review ? "需人工复核" : "可直接入账"}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">风险提示</span>
                <h3>制单复核点</h3>
              </div>
              <strong className="risk-count">{result.risks.length}</strong>
            </div>
            <div className="invoice-risk-list">
              {result.risks.length > 0 ? (
                result.risks.map((risk) => (
                  <article className="ecommerce-risk" key={risk.id}>
                    <strong>{risk.title}</strong>
                    <span>{"★".repeat(risk.level)}{"☆".repeat(5 - risk.level)}</span>
                    <p>{risk.description}</p>
                    <small>{risk.suggestion}</small>
                  </article>
                ))
              ) : (
                <p className="muted">未发现借贷平衡或价税勾稽异常。</p>
              )}
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">下一步</span>
                <h3>审核动作</h3>
              </div>
            </div>
            <ul className="suggestion-list">
              {result.suggestions.map((suggestion) => (
                <li key={suggestion}>{suggestion}</li>
              ))}
            </ul>
          </section>

          <section className="panel qa-citation-panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">引用依据</span>
                <h3>准则与税法来源</h3>
              </div>
            </div>
            <div className="qa-citations">
              {result.citations.map((citation) => (
                <article key={`${citation.title}-${citation.published_date}`}>
                  <strong>{citation.title}</strong>
                  <p>
                    {citation.authority}
                    {citation.document_number ? ` · ${citation.document_number}` : ""}
                  </p>
                  <small>
                    发布/成文：{citation.published_date} · 状态：{citation.status} · 更新：{citation.updated_at}
                  </small>
                  <a href={citation.source_url} target="_blank" rel="noreferrer">查看来源</a>
                </article>
              ))}
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}
