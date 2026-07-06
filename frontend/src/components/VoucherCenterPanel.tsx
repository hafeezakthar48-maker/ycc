import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  createVoucherCenterRecord,
  downloadVoucherCenterCsv,
  fetchVoucherCenter,
  importVoucherCenterRecords,
  postVoucherCenterRecord,
  reviewVoucherCenterRecord,
  unpostVoucherCenterRecord,
  unreviewVoucherCenterRecord,
  updateVoucherCenterRecord,
  uploadVoucherCenterAttachment
} from "../services/dashboardApi";
import type { VoucherCenterCreateRequest, VoucherCenterLine, VoucherCenterRecord } from "../types/voucherCenter";

const defaultVoucher: VoucherCenterCreateRequest = {
  voucher_date: "2026-06-30",
  summary: "办公服务费",
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

const importExample = JSON.stringify(
  [
    { ...defaultVoucher, summary: "导入凭证一" },
    { ...defaultVoucher, summary: "导入凭证二", invoice_number: "87654321" }
  ],
  null,
  2
);

function money(value: number | string) {
  return Number(value).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function reviewLabel(voucher: VoucherCenterRecord) {
  return voucher.status === "reviewed" ? "已审核" : "草稿";
}

function postingLabel(voucher: VoucherCenterRecord) {
  return voucher.posting_status === "posted" ? "已过账" : "未过账";
}

function formalJournalLabel(voucher: VoucherCenterRecord) {
  if (voucher.journal_reversal_entry_id) {
    return `冲销分录 ${voucher.journal_reversal_entry_id}`;
  }
  return voucher.journal_entry_id ? `正式分录 ${voucher.journal_entry_id}` : "未正式过账";
}

function toRequest(voucher: VoucherCenterRecord): VoucherCenterCreateRequest {
  return {
    voucher_date: voucher.voucher_date,
    summary: voucher.summary,
    counterparty: voucher.counterparty,
    invoice_number: voucher.invoice_number,
    amount: Number(voucher.amount),
    tax_amount: Number(voucher.tax_amount),
    total_amount_with_tax: Number(voucher.total_amount_with_tax),
    lines: voucher.lines.map((line) => ({ ...line, amount: Number(line.amount) }))
  };
}

export default function VoucherCenterPanel() {
  const [form, setForm] = useState<VoucherCenterCreateRequest>(defaultVoucher);
  const [vouchers, setVouchers] = useState<VoucherCenterRecord[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [importText, setImportText] = useState(importExample);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  const selectedVoucher = useMemo(
    () => vouchers.find((voucher) => voucher.id === selectedId) ?? null,
    [selectedId, vouchers]
  );

  async function reload(nextSelectedId = selectedId) {
    const response = await fetchVoucherCenter();
    setVouchers(response.vouchers);
    if (nextSelectedId && response.vouchers.some((voucher) => voucher.id === nextSelectedId)) {
      setSelectedId(nextSelectedId);
    } else {
      setSelectedId(response.vouchers[0]?.id ?? null);
    }
  }

  useEffect(() => {
    reload();
  }, []);

  function updateField(key: keyof VoucherCenterCreateRequest, value: string) {
    setForm((current) => {
      if (key === "amount" || key === "tax_amount" || key === "total_amount_with_tax") {
        const numericValue = Number(value);
        return { ...current, [key]: Number.isFinite(numericValue) ? numericValue : 0 };
      }
      return { ...current, [key]: value };
    });
  }

  function updateLine(index: number, key: keyof VoucherCenterLine, value: string) {
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

  function selectVoucher(voucher: VoucherCenterRecord) {
    setSelectedId(voucher.id);
    setForm(toRequest(voucher));
  }

  async function runAction(action: () => Promise<VoucherCenterRecord | void>, nextSelectedId?: string) {
    setIsBusy(true);
    setError(null);
    try {
      const result = await action();
      await reload(nextSelectedId ?? (result && "id" in result ? result.id : selectedId));
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "凭证中心操作失败");
    } finally {
      setIsBusy(false);
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    runAction(() => createVoucherCenterRecord(form));
  }

  function handleUpdate() {
    if (!selectedVoucher) {
      setError("请先选择要修改的凭证。");
      return;
    }
    runAction(() => updateVoucherCenterRecord(selectedVoucher.id, form), selectedVoucher.id);
  }

  function handleReview() {
    if (!selectedVoucher) {
      setError("请先选择要审核的凭证。");
      return;
    }
    runAction(() => reviewVoucherCenterRecord(selectedVoucher.id, "财务主管"), selectedVoucher.id);
  }

  function handleUnreview() {
    if (!selectedVoucher) {
      setError("请先选择要反审核的凭证。");
      return;
    }
    runAction(() => unreviewVoucherCenterRecord(selectedVoucher.id), selectedVoucher.id);
  }

  function handlePost() {
    if (!selectedVoucher) {
      setError("请先选择要过账的凭证。");
      return;
    }
    runAction(() => postVoucherCenterRecord(selectedVoucher.id, "财务主管"), selectedVoucher.id);
  }

  function handleUnpost() {
    if (!selectedVoucher) {
      setError("请先选择要反过账的凭证。");
      return;
    }
    runAction(() => unpostVoucherCenterRecord(selectedVoucher.id, "财务主管"), selectedVoucher.id);
  }

  function handleImport() {
    setIsBusy(true);
    setError(null);
    try {
      const parsed = JSON.parse(importText) as VoucherCenterCreateRequest[];
      importVoucherCenterRecords(parsed)
        .then((result) => reload(result.vouchers[0]?.id))
        .catch((importError) => setError(importError instanceof Error ? importError.message : "导入凭证失败"))
        .finally(() => setIsBusy(false));
    } catch {
      setError("JSON 格式不正确，请检查导入内容。");
      setIsBusy(false);
    }
  }

  function handleUpload() {
    if (!selectedVoucher || !file) {
      setError("请先选择凭证和附件。");
      return;
    }
    runAction(() => uploadVoucherCenterAttachment(selectedVoucher.id, file), selectedVoucher.id);
  }

  return (
    <section id="voucher-center" className="voucher-center-section">
      <div className="section-heading">
        <div>
          <span className="eyebrow">凭证中心</span>
          <h2>新增、修改、审核、反审核与导入导出</h2>
        </div>
        <div className="qa-status-strip">
          <span>自动编号</span>
          <span>AI检查</span>
          <span>附件记录</span>
        </div>
      </div>

      <form className="voucher-center-form" onSubmit={handleSubmit}>
        <label>凭证日期<input type="date" value={form.voucher_date} onChange={(event) => updateField("voucher_date", event.target.value)} /></label>
        <label>摘要<input value={form.summary} onChange={(event) => updateField("summary", event.target.value)} /></label>
        <label>交易对方<input value={form.counterparty} onChange={(event) => updateField("counterparty", event.target.value)} /></label>
        <label>发票号码<input value={form.invoice_number} onChange={(event) => updateField("invoice_number", event.target.value)} /></label>
        <label>不含税金额<input type="number" min={0} step={0.01} value={form.amount} onChange={(event) => updateField("amount", event.target.value)} /></label>
        <label>税额<input type="number" min={0} step={0.01} value={form.tax_amount} onChange={(event) => updateField("tax_amount", event.target.value)} /></label>
        <label>价税合计<input type="number" min={0} step={0.01} value={form.total_amount_with_tax} onChange={(event) => updateField("total_amount_with_tax", event.target.value)} /></label>
        <div className="voucher-center-actions">
          <button type="submit" disabled={isBusy}>新增</button>
          <button type="button" className="button-secondary" onClick={handleUpdate} disabled={isBusy}>修改</button>
          <button type="button" className="button-secondary" onClick={handleReview} disabled={isBusy}>审核</button>
          <button type="button" className="button-secondary" onClick={handleUnreview} disabled={isBusy}>反审核</button>
          <button type="button" className="button-secondary" onClick={handlePost} disabled={isBusy}>过账</button>
          <button type="button" className="button-secondary" onClick={handleUnpost} disabled={isBusy}>反过账</button>
          <button type="button" className="button-secondary" onClick={downloadVoucherCenterCsv} disabled={isBusy}>导出 CSV</button>
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

      <div className="voucher-center-grid">
        <section className="panel voucher-list-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">凭证列表</span>
              <h3>{vouchers.length} 张凭证</h3>
            </div>
          </div>
          <div className="voucher-list">
            {vouchers.length > 0 ? vouchers.map((voucher) => (
              <button
                type="button"
                className={`voucher-list-item ${selectedId === voucher.id ? "voucher-list-item--active" : ""}`}
                key={voucher.id}
                onClick={() => selectVoucher(voucher)}
              >
                <strong>{voucher.voucher_number}</strong>
                <span>{reviewLabel(voucher)} · {postingLabel(voucher)} · {voucher.voucher_date}</span>
                <small>{voucher.summary} · {money(voucher.total_amount_with_tax)} · {formalJournalLabel(voucher)}</small>
              </button>
            )) : <p className="muted">暂无凭证，请先新增或导入。</p>}
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">AI检查凭证错误</span>
              <h3>{selectedVoucher?.audit_result?.rating ?? "等待凭证"}</h3>
            </div>
            <strong className="risk-count">{selectedVoucher?.audit_result?.score ?? 0}分</strong>
          </div>
          {selectedVoucher?.audit_result ? (
            <div className="invoice-risk-list">
              {selectedVoucher.audit_result.findings.length > 0 ? selectedVoucher.audit_result.findings.map((finding) => (
                <article className="ecommerce-risk" key={finding.id}>
                  <strong>{finding.title}</strong>
                  <span>{"★".repeat(finding.severity)}{"☆".repeat(5 - finding.severity)}</span>
                  <p>{finding.description}</p>
                  <small>{finding.suggestion}</small>
                </article>
              )) : <p className="muted">AI 审核未发现基础错误。</p>}
            </div>
          ) : <p className="muted">选择凭证后查看 AI 审核结果。</p>}
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">附件上传</span>
              <h3>OCR识别附件入口</h3>
            </div>
          </div>
          <div className="voucher-attachment-box">
            <input type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
            <button type="button" onClick={handleUpload} disabled={isBusy}>上传附件</button>
            {selectedVoucher?.attachments.length ? (
              selectedVoucher.attachments.map((attachment) => (
                <small key={attachment.id}>
                  {attachment.filename} · {attachment.ocr_status} · {attachment.storage_status}
                  {attachment.archive_document_id ? ` · ${attachment.archive_document_id}` : ""}
                  {attachment.sha256_hash ? ` · ${attachment.sha256_hash.slice(0, 12)}` : ""}
                </small>
              ))
            ) : <p className="muted">暂无附件。</p>}
          </div>
        </section>

        <section className="panel voucher-import-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">导入</span>
              <h3>JSON 批量导入</h3>
            </div>
          </div>
          <textarea value={importText} onChange={(event) => setImportText(event.target.value)} rows={10} />
          <button type="button" onClick={handleImport} disabled={isBusy}>导入 JSON</button>
        </section>
      </div>
    </section>
  );
}
