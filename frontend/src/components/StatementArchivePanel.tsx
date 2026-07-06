import { useCallback, useEffect, useMemo, useState } from "react";
import {
  createStatementSnapshot,
  exportStatementSnapshot,
  listStatementSnapshots,
  lockStatementSnapshot
} from "../services/dashboardApi";
import type { StatementArchiveStatus, StatementSnapshot, StatementValidationStatus } from "../types/statementArchive";

interface StatementArchivePanelProps {
  period: string;
}

const archiveStatusLabels: Record<StatementArchiveStatus, string> = {
  draft: "草稿",
  locked: "已锁定",
  archived: "已归档",
  demo_only: "演示数据"
};

const validationStatusLabels: Record<StatementValidationStatus, string> = {
  passed: "校验通过",
  warning: "有提示",
  failed: "未通过"
};

function formatTime(value: string | null | undefined) {
  if (!value) {
    return "-";
  }
  return value.replace("T", " ").replace("Z", "");
}

function shortHash(value: string) {
  return value ? value.slice(0, 12) : "-";
}

function sourceLabel(source: string) {
  if (source === "formal_journal_entries") {
    return "正式分录";
  }
  if (source === "reviewed_vouchers") {
    return "已审核凭证";
  }
  return "样例数据";
}

export default function StatementArchivePanel({ period }: StatementArchivePanelProps) {
  const [snapshots, setSnapshots] = useState<StatementSnapshot[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshSnapshots = useCallback(() => {
    setIsLoading(true);
    setError(null);
    listStatementSnapshots("default", period)
      .then((payload) => {
        setSnapshots(payload.items);
      })
      .catch((archiveError) => {
        setError(archiveError instanceof Error ? archiveError.message : "报表归档读取失败");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [period]);

  useEffect(() => {
    refreshSnapshots();
  }, [refreshSnapshots]);

  const summary = useMemo(() => {
    const lockedCount = snapshots.filter((snapshot) => snapshot.locked).length;
    const latest = snapshots[0] ?? null;
    return {
      total: snapshots.length,
      lockedCount,
      latestVersion: latest ? `V${latest.version}` : "-",
      latestHash: latest ? shortHash(latest.content_hash) : "-"
    };
  }, [snapshots]);

  function runAction(actionId: string, action: () => Promise<unknown>, successMessage: string) {
    setActiveAction(actionId);
    setError(null);
    setMessage(null);
    action()
      .then(() => {
        setMessage(successMessage);
        refreshSnapshots();
      })
      .catch((archiveError) => {
        setError(archiveError instanceof Error ? archiveError.message : "报表归档操作失败");
      })
      .finally(() => {
        setActiveAction(null);
      });
  }

  function handleCreateSnapshot() {
    runAction(
      "create",
      () => createStatementSnapshot({
        period,
        account_set_id: "default",
        operator: "财务主管",
        created_by: "finance-user"
      }),
      "已生成新的报表快照"
    );
  }

  function handleLockSnapshot(snapshotId: string) {
    runAction(
      `lock:${snapshotId}`,
      () => lockStatementSnapshot(snapshotId, { locked_by: "finance-manager" }),
      "快照已锁定归档"
    );
  }

  function handleExportSnapshot(snapshotId: string, format: "xlsx" | "pdf") {
    runAction(
      `export:${format}:${snapshotId}`,
      () => exportStatementSnapshot(snapshotId, format),
      format === "xlsx" ? "Excel 文件已开始下载" : "PDF 文件已开始下载"
    );
  }

  return (
    <section id="statement-archive-panel" className="statement-archive-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">报表归档</span>
          <h2>快照锁定与正式导出</h2>
        </div>
        <div className="statement-archive-actions">
          <span>{period}</span>
          <button
            type="button"
            onClick={handleCreateSnapshot}
            disabled={isLoading || activeAction === "create"}
          >
            {activeAction === "create" ? "生成中..." : "生成快照"}
          </button>
          <button type="button" className="button-secondary" onClick={refreshSnapshots} disabled={isLoading}>
            刷新
          </button>
        </div>
      </div>

      {error ? <p className="inline-error">{error}</p> : null}
      {message ? <p className="statement-archive-message">{message}</p> : null}

      <div className="statement-archive-summary-grid">
        <article>
          <span>归档版本</span>
          <strong>{summary.total}</strong>
        </article>
        <article>
          <span>已锁定</span>
          <strong>{summary.lockedCount}</strong>
        </article>
        <article>
          <span>最新版本</span>
          <strong>{summary.latestVersion}</strong>
        </article>
        <article>
          <span>内容哈希</span>
          <strong>{summary.latestHash}</strong>
        </article>
      </div>

      <div className="voucher-table-wrap">
        <table className="voucher-table statement-archive-table">
          <thead>
            <tr>
              <th>版本</th>
              <th>来源</th>
              <th>校验</th>
              <th>状态</th>
              <th>哈希</th>
              <th>创建/锁定</th>
              <th>动作</th>
            </tr>
          </thead>
          <tbody>
            {snapshots.length ? snapshots.map((snapshot) => (
              <tr key={snapshot.snapshot_id}>
                <td>
                  <strong>V{snapshot.version}</strong>
                  <small>{snapshot.period}</small>
                </td>
                <td>{sourceLabel(snapshot.source)}</td>
                <td>
                  <span className={`statement-archive-status statement-archive-status--${snapshot.validation_status}`}>
                    {validationStatusLabels[snapshot.validation_status]}
                  </span>
                </td>
                <td>
                  <span className={`statement-archive-status statement-archive-status--${snapshot.archive_status}`}>
                    {archiveStatusLabels[snapshot.archive_status]}
                  </span>
                </td>
                <td>{shortHash(snapshot.content_hash)}</td>
                <td>
                  <span>{formatTime(snapshot.created_at)}</span>
                  <small>{snapshot.locked ? `锁定 ${formatTime(snapshot.locked_at)}` : "未锁定"}</small>
                </td>
                <td>
                  <div className="statement-archive-row-actions">
                    <button
                      type="button"
                      className="button-secondary"
                      onClick={() => handleLockSnapshot(snapshot.snapshot_id)}
                      disabled={snapshot.locked || activeAction === `lock:${snapshot.snapshot_id}`}
                    >
                      {snapshot.locked ? "已锁定" : "锁定"}
                    </button>
                    <button
                      type="button"
                      className="button-secondary"
                      onClick={() => handleExportSnapshot(snapshot.snapshot_id, "xlsx")}
                      disabled={activeAction === `export:xlsx:${snapshot.snapshot_id}`}
                    >
                      Excel
                    </button>
                    <button
                      type="button"
                      className="button-secondary"
                      onClick={() => handleExportSnapshot(snapshot.snapshot_id, "pdf")}
                      disabled={activeAction === `export:pdf:${snapshot.snapshot_id}`}
                    >
                      PDF
                    </button>
                  </div>
                </td>
              </tr>
            )) : (
              <tr>
                <td colSpan={7}>{isLoading ? "正在读取报表快照" : "暂无报表快照"}</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
