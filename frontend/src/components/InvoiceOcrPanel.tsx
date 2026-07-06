import { FormEvent, useState } from "react";
import { recognizeInvoiceText, uploadInvoiceFile } from "../services/dashboardApi";
import type { InvoiceOcrResponse } from "../types/invoiceOcr";

const sampleInvoiceText = `增值税电子普通发票
发票代码：044032300111
发票号码：12345678
开票日期：2026年06月30日
购买方名称：示例制造企业
购买方纳税人识别号：91310000MA1TEST001
销售方名称：上海云智科技有限公司
销售方纳税人识别号：91310115MA1K000002
金额：1000.00
税额：60.00
价税合计（大写）：壹仟零陆拾元整 （小写）¥1060.00`;

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function statusLabel(status: string) {
  if (status === "text_parsed") {
    return "文本已解析";
  }
  if (status === "missing") {
    return "OCR 引擎未接入";
  }
  return status;
}

export default function InvoiceOcrPanel() {
  const [text, setText] = useState(sampleInvoiceText);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<InvoiceOcrResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  async function runTextRecognition(nextText = text) {
    const trimmed = nextText.trim();
    if (!trimmed) {
      setError("请先粘贴发票 OCR 文本。");
      return;
    }

    setIsBusy(true);
    setError(null);
    try {
      setResult(await recognizeInvoiceText(trimmed));
      setText(trimmed);
    } catch (ocrError) {
      setError(ocrError instanceof Error ? ocrError.message : "发票 OCR 识别失败");
    } finally {
      setIsBusy(false);
    }
  }

  async function runFileUpload() {
    if (!file) {
      setError("请选择发票图片、PDF 或文本文件。");
      return;
    }

    setIsBusy(true);
    setError(null);
    try {
      setResult(await uploadInvoiceFile(file));
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "发票文件上传识别失败");
    } finally {
      setIsBusy(false);
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    runTextRecognition();
  }

  return (
    <section id="invoice-ocr" className="invoice-ocr-section">
      <div className="section-heading">
        <div>
          <span className="eyebrow">OCR 发票识别</span>
          <h2>发票字段提取与合规风险复核</h2>
        </div>
        <div className="qa-status-strip">
          <span>字段置信度</span>
          <span>价税勾稽</span>
          <span>法规引用</span>
        </div>
      </div>

      <form className="invoice-ocr-form" onSubmit={handleSubmit}>
        <label>
          发票文本
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={9}
            placeholder="粘贴 OCR 文本或手动录入发票内容"
          />
        </label>
        <div className="invoice-upload-box">
          <label>
            发票文件
            <input
              type="file"
              accept=".txt,.pdf,image/*"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <div className="invoice-actions">
            <button type="submit" disabled={isBusy}>{isBusy ? "识别中..." : "识别文本"}</button>
            <button type="button" className="button-secondary" onClick={runFileUpload} disabled={isBusy}>
              上传识别
            </button>
          </div>
          {file ? <p className="muted">已选择：{file.name}</p> : null}
        </div>
      </form>

      {error ? <p className="inline-error">{error}</p> : null}

      {result ? (
        <div className="invoice-result-grid">
          <section className="panel invoice-fields-panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">{statusLabel(result.engine_status)}</span>
                <h3>{result.invoice_type ?? "等待有效发票字段"}</h3>
              </div>
            </div>
            {result.fields.length > 0 ? (
              <div className="invoice-field-grid">
                {result.fields.map((field) => (
                  <article className="invoice-field-card" key={field.key}>
                    <span>{field.label}</span>
                    <strong>{field.value ?? "未识别"}</strong>
                    <small>置信度 {percent(field.confidence)}</small>
                  </article>
                ))}
              </div>
            ) : (
              <p className="muted">当前文件未产生可用字段。</p>
            )}
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">风险提示</span>
                <h3>发票合规检查</h3>
              </div>
              <strong className="risk-count">{result.risks.length}</strong>
            </div>
            <div className="invoice-risk-list">
              {result.warnings.map((warning) => (
                <article className="invoice-warning" key={warning}>{warning}</article>
              ))}
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
                <p className="muted">未发现基础字段和价税勾稽异常。</p>
              )}
            </div>
          </section>

          <section className="panel qa-citation-panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">引用依据</span>
                <h3>发票法规来源</h3>
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
