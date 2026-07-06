import { FormEvent, useEffect, useState } from "react";
import { reviewAuditSubject } from "../services/dashboardApi";
import type { AuditRequest, AuditResponse, AuditVoucherLine } from "../types/audit";

const cleanSample: AuditRequest = {
  audit_subject: "voucher",
  voucher_date: "2026-06-30",
  summary: "办公服务费；交易对方：上海云智科技有限公司",
  counterparty: "上海云智科技有限公司",
  invoice_number: "12345678",
  amount: 1000,
  tax_amount: 60,
  total_amount_with_tax: 1060,
  lines: [
    { account_code: "6602", account_name: "管理费用", direction: "借", amount: 1000, explanation: "办公服务费" },
    { account_code: "22210101", account_name: "应交税费-应交增值税（进项税额）", direction: "借", amount: 60, explanation: "进项税额" },
    { account_code: "2202", account_name: "应付账款", direction: "贷", amount: 1060, explanation: "应付未付款" }
  ]
};

const riskSample: AuditRequest = {
  ...cleanSample,
  summary: "办公服务费",
  invoice_number: "",
  total_amount_with_tax: 1099,
  lines: [
    { account_code: "6602", account_name: "管理费用", direction: "借", amount: 1000, explanation: "办公服务费" },
    { account_code: "22210101", account_name: "应交税费-应交增值税（进项税额）", direction: "借", amount: 60, explanation: "进项税额" },
    { account_code: "2202", account_name: "应付账款", direction: "贷", amount: 1099, explanation: "应付未付款" }
  ]
};

function money(value: number) {
  return value.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function ratingClass(rating: string) {
  if (rating === "通过") {
    return "qa-risk--low";
  }
  if (rating === "高风险") {
    return "qa-risk--high";
  }
  return "qa-risk--medium";
}

function checkClass(status: string) {
  if (status === "pass") {
    return "audit-check--pass";
  }
  if (status === "fail") {
    return "audit-check--fail";
  }
  return "audit-check--warn";
}

export default function AuditReviewPanel() {
  const [form, setForm] = useState<AuditRequest>(riskSample);
  const [result, setResult] = useState<AuditResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  async function runReview(nextForm = form) {
    setIsBusy(true);
    setError(null);
    try {
      setResult(await reviewAuditSubject(nextForm));
      setForm(nextForm);
    } catch (reviewError) {
      setError(reviewError instanceof Error ? reviewError.message : "自动审核失败");
    } finally {
      setIsBusy(false);
    }
  }

  useEffect(() => {
    runReview(riskSample);
  }, []);

  function updateField(key: keyof AuditRequest, value: string) {
    setForm((current) => {
      if (key === "amount" || key === "tax_amount" || key === "total_amount_with_tax") {
        const numericValue = Number(value);
        return { ...current, [key]: Number.isFinite(numericValue) ? numericValue : 0 };
      }
      return { ...current, [key]: value };
    });
  }

  function updateLine(index: number, key: keyof AuditVoucherLine, value: string) {
    setForm((current) => {
      const lines = current.lines.map((line, lineIndex) => {
        if (lineIndex !== index) {
          return line;
        }
        if (key === "amount") {
          const numericValue = Number(value);
          return { ...line, amount: Number.isFinite(numericValue) ? numericValue : 0 };
        }
        return { ...line, [key]: value };
      });
      return { ...current, lines };
    });
  }

  function loadSample(sample: AuditRequest) {
    setForm(sample);
    runReview(sample);
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    runReview();
  }

  return (
    <section id="audit-review" className="audit-section">
      <div className="section-heading">
        <div>
          <span className="eyebrow">AI 自动审核</span>
          <h2>凭证、发票与税额错误识别</h2>
        </div>
        <div className="qa-status-strip">
          <span>逐项检查</span>
          <span>错误定位</span>
          <span>人工复核</span>
        </div>
      </div>

      <form className="audit-form" onSubmit={handleSubmit}>
        <label>
          凭证日期
          <input type="date" value={form.voucher_date} onChange={(event) => updateField("voucher_date", event.target.value)} />
        </label>
        <label>
          摘要
          <input value={form.summary} onChange={(event) => updateField("summary", event.target.value)} />
        </label>
        <label>
          交易对方
          <input value={form.counterparty} onChange={(event) => updateField("counterparty", event.target.value)} />
        </label>
        <label>
          发票号码
          <input value={form.invoice_number} onChange={(event) => updateField("invoice_number", event.target.value)} />
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
        <div className="audit-actions">
          <button type="submit" disabled={isBusy}>{isBusy ? "审核中..." : "运行审核"}</button>
          <button type="button" className="button-secondary" onClick={() => loadSample(cleanSample)} disabled={isBusy}>正常样本</button>
          <button type="button" className="button-secondary" onClick={() => loadSample(riskSample)} disabled={isBusy}>异常样本</button>
        </div>
      </form>

      <div className="audit-line-editor">
        {form.lines.map((line, index) => (
          <article className="audit-line-row" key={`${index}-${line.account_code}`}>
            <input value={line.direction} onChange={(event) => updateLine(index, "direction", event.target.value)} aria-label="方向" />
            <input value={line.account_code} onChange={(event) => updateLine(index, "account_code", event.target.value)} aria-label="科目编码" />
            <input value={line.account_name} onChange={(event) => updateLine(index, "account_name", event.target.value)} aria-label="科目名称" />
            <input type="number" min={0} step={0.01} value={line.amount} onChange={(event) => updateLine(index, "amount", event.target.value)} aria-label="金额" />
            <input value={line.explanation} onChange={(event) => updateLine(index, "explanation", event.target.value)} aria-label="说明" />
          </article>
        ))}
      </div>

      {error ? <p className="inline-error">{error}</p> : null}

      {result ? (
        <div className="audit-result-grid">
          <section className="panel audit-score-panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">审核结论</span>
                <h3>{result.score} 分</h3>
              </div>
              <div className={`qa-risk ${ratingClass(result.rating)}`}>{result.rating}</div>
            </div>
            <div className="audit-check-grid">
              {result.checks.map((check) => (
                <article className={`audit-check ${checkClass(check.status)}`} key={check.id}>
                  <strong>{check.title}</strong>
                  <span>{check.status === "pass" ? "通过" : check.status === "fail" ? "失败" : "警告"}</span>
                  <p>{check.evidence}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">错误清单</span>
                <h3>自动找错结果</h3>
              </div>
              <strong className="risk-count">{result.findings.length}</strong>
            </div>
            <div className="invoice-risk-list">
              {result.findings.length > 0 ? (
                result.findings.map((finding) => (
                  <article className="ecommerce-risk" key={finding.id}>
                    <strong>{finding.title}</strong>
                    <span>{"★".repeat(finding.severity)}{"☆".repeat(5 - finding.severity)}</span>
                    <p>{finding.description}</p>
                    <small>{finding.evidence}</small>
                    <small>{finding.suggestion}</small>
                  </article>
                ))
              ) : (
                <p className="muted">未发现基础审核错误。</p>
              )}
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">审核建议</span>
                <h3>下一步动作</h3>
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
                <h3>审核规则来源</h3>
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
