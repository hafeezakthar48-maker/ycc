import { useCallback, useEffect, useMemo, useState } from "react";
import {
  createAccountingArchiveCase,
  downloadAccountingArchivePackage,
  fetchAccountingArchiveDocuments
} from "../services/dashboardApi";
import type { ArchiveDocument, ArchiveOcrStatus, ArchiveVerificationStatus } from "../types/accountingArchive";

interface AccountingArchivePanelProps {
  period: string;
}

const ocrStatusLabels: Record<ArchiveOcrStatus, string> = {
  not_required: "无需识别",
  text_parsed: "文本已解析",
  engine_required: "待 OCR 引擎",
  failed: "识别失败"
};

const verificationStatusLabels: Record<ArchiveVerificationStatus, string> = {
  not_required: "无需验真",
  pending_external: "待外部验真",
  verified: "已验真",
  failed: "验真失败"
};

function shortHash(value: string) {
  return value ? value.slice(0, 12) : "-";
}

function formatBytes(value: number) {
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

function formatTime(value: string) {
  return value ? value.replace("T", " ").replace("Z", "") : "-";
}

function sourceLabel(document: ArchiveDocument) {
  if (document.source_type === "voucher") {
    return `凭证 ${document.source_id.slice(0, 10)}`;
  }
  if (document.source_type === "statement_snapshot") {
    return "报表快照";
  }
  return document.source_type;
}

export default function AccountingArchivePanel({ period }: AccountingArchivePanelProps) {
  const [documents, setDocuments] = useState<ArchiveDocument[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [lastCaseId, setLastCaseId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshDocuments = useCallback(() => {
    setIsLoading(true);
    setError(null);
    fetchAccountingArchiveDocuments("default", period)
      .then((payload) => {
        setDocuments(payload.documents);
        setSelectedIds((current) =>
          current.filter((documentId) => payload.documents.some((document) => document.archive_document_id === documentId))
        );
      })
      .catch((archiveError) => {
        setError(archiveError instanceof Error ? archiveError.message : "会计档案读取失败");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [period]);

  useEffect(() => {
    refreshDocuments();
  }, [refreshDocuments]);

  const summary = useMemo(() => ({
    total: documents.length,
    selected: selectedIds.length,
    pendingVerification: documents.filter((document) => document.verification_status === "pending_external").length,
    engineRequired: documents.filter((document) => document.ocr_status === "engine_required").length
  }), [documents, selectedIds.length]);

  function toggleDocument(documentId: string) {
    setSelectedIds((current) =>
      current.includes(documentId)
        ? current.filter((item) => item !== documentId)
        : [...current, documentId]
    );
  }

  function toggleAllDocuments() {
    setSelectedIds((current) =>
      current.length === documents.length ? [] : documents.map((document) => document.archive_document_id)
    );
  }

  async function handleCreateCase() {
    if (selectedIds.length === 0) {
      setError("请先选择要归档的文档。");
      return;
    }
    setActiveAction("create");
    setError(null);
    setMessage(null);
    try {
      const archiveCase = await createAccountingArchiveCase({
        account_set_id: "default",
        period,
        case_type: "voucher",
        title: `${period} 凭证档案`,
        document_ids: selectedIds,
        created_by: "finance-manager"
      });
      setLastCaseId(archiveCase.archive_case_id);
      setMessage(`已创建 ${archiveCase.document_count} 份文档的档案案卷。`);
    } catch (archiveError) {
      setError(archiveError instanceof Error ? archiveError.message : "会计档案案卷创建失败");
    } finally {
      setActiveAction(null);
    }
  }

  async function handleDownloadPackage() {
    if (!lastCaseId) {
      return;
    }
    setActiveAction("download");
    setError(null);
    setMessage(null);
    try {
      const download = await downloadAccountingArchivePackage(lastCaseId);
      setMessage(`${download.filename} 已开始下载。`);
    } catch (archiveError) {
      setError(archiveError instanceof Error ? archiveError.message : "会计档案包下载失败");
    } finally {
      setActiveAction(null);
    }
  }

  return (
    <section id="accounting-archive-panel" className="accounting-archive-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">会计档案</span>
          <h2>电子凭证与档案案卷</h2>
        </div>
        <div className="statement-archive-actions accounting-archive-actions">
          <span>{period}</span>
          <button type="button" onClick={handleCreateCase} disabled={activeAction === "create" || selectedIds.length === 0}>
            {activeAction === "create" ? "建案中..." : "创建案卷"}
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={handleDownloadPackage}
            disabled={!lastCaseId || activeAction === "download"}
          >
            {activeAction === "download" ? "下载中..." : "下载归档包"}
          </button>
          <button type="button" className="button-secondary" onClick={refreshDocuments} disabled={isLoading}>
            刷新
          </button>
        </div>
      </div>

      {error ? <p className="inline-error">{error}</p> : null}
      {message ? <p className="statement-archive-message">{message}</p> : null}

      <div className="statement-archive-summary-grid accounting-archive-summary-grid">
        <article>
          <span>文档数</span>
          <strong>{summary.total}</strong>
        </article>
        <article>
          <span>已选择</span>
          <strong>{summary.selected}</strong>
        </article>
        <article>
          <span>待验真</span>
          <strong>{summary.pendingVerification}</strong>
        </article>
        <article>
          <span>待 OCR</span>
          <strong>{summary.engineRequired}</strong>
        </article>
      </div>

      <div className="voucher-table-wrap">
        <table className="voucher-table accounting-archive-table">
          <thead>
            <tr>
              <th>
                <input
                  type="checkbox"
                  checked={documents.length > 0 && selectedIds.length === documents.length}
                  onChange={toggleAllDocuments}
                  aria-label="选择全部档案文档"
                />
              </th>
              <th>文件</th>
              <th>来源</th>
              <th>OCR</th>
              <th>验真</th>
              <th>存储</th>
              <th>保管</th>
              <th>哈希</th>
              <th>创建时间</th>
            </tr>
          </thead>
          <tbody>
            {documents.length ? documents.map((document) => (
              <tr key={document.archive_document_id}>
                <td>
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(document.archive_document_id)}
                    onChange={() => toggleDocument(document.archive_document_id)}
                    aria-label={`选择 ${document.filename}`}
                  />
                </td>
                <td>
                  <strong>{document.filename}</strong>
                  <small>{document.document_type} · {formatBytes(document.size)}</small>
                </td>
                <td>{sourceLabel(document)}</td>
                <td>
                  <span className={`statement-archive-status statement-archive-status--${document.ocr_status}`}>
                    {ocrStatusLabels[document.ocr_status]}
                  </span>
                </td>
                <td>
                  <span className={`statement-archive-status statement-archive-status--${document.verification_status}`}>
                    {verificationStatusLabels[document.verification_status]}
                  </span>
                </td>
                <td>{document.storage_status}</td>
                <td>{document.retention_years} 年</td>
                <td>{shortHash(document.sha256_hash)}</td>
                <td>{formatTime(document.created_at)}</td>
              </tr>
            )) : (
              <tr>
                <td colSpan={9}>{isLoading ? "正在读取会计档案" : "当前期间暂无会计档案文档"}</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
