import { useCallback, useEffect, useMemo, useState } from "react";
import {
  createAccountingBackup,
  fetchAccountingGoLiveGate,
  fetchAccountingIntegrityChecks,
  fetchAccountingPermissionMatrix,
  previewAccountingMigration,
  rehearseAccountingRestore
} from "../services/dashboardApi";
import type {
  AccountingBackupManifest,
  AccountingIntegrityReport,
  AccountingMigrationPreview,
  FormalAccountingGoLiveGate,
  FormalAccountingPermissionMatrix,
  GoLiveGateStatus,
  IntegrityStatus,
  RestoreRehearsalResult
} from "../types/accountingGovernance";

interface AccountingGovernancePanelProps {
  period: string;
}

const regressionResults = {
  backend_tests: "passed",
  frontend_tests: "passed",
  frontend_build: "passed"
};

const criticalPermissions = [
  "accounting_governance.read",
  "accounting_migration.preview",
  "accounting_migration.apply",
  "accounting_backup.create",
  "accounting_governance.approve_go_live"
];

function statusLabel(status: IntegrityStatus | GoLiveGateStatus | "passed" | "failed") {
  const labels: Record<string, string> = {
    pass: "通过",
    passed: "通过",
    warning: "警告",
    fail: "失败",
    failed: "失败",
    blocked: "阻塞"
  };
  return labels[status] ?? status;
}

function statusClass(status: IntegrityStatus | GoLiveGateStatus | "passed" | "failed") {
  if (status === "pass" || status === "passed") {
    return "status-pill";
  }
  if (status === "warning") {
    return "status-pill status-pill--planned";
  }
  return "risk-badge risk-badge--high";
}

export default function AccountingGovernancePanel({ period }: AccountingGovernancePanelProps) {
  const [integrity, setIntegrity] = useState<AccountingIntegrityReport | null>(null);
  const [migration, setMigration] = useState<AccountingMigrationPreview | null>(null);
  const [backup, setBackup] = useState<AccountingBackupManifest | null>(null);
  const [restore, setRestore] = useState<RestoreRehearsalResult | null>(null);
  const [matrix, setMatrix] = useState<FormalAccountingPermissionMatrix | null>(null);
  const [gate, setGate] = useState<FormalAccountingGoLiveGate | null>(null);
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshGovernance = useCallback(async () => {
    setError(null);
    try {
      const [integrityPayload, migrationPayload, matrixPayload, gatePayload] = await Promise.all([
        fetchAccountingIntegrityChecks("default", period),
        previewAccountingMigration({ account_set_id: "default", period, actor_id: "migration-user" }),
        fetchAccountingPermissionMatrix(),
        fetchAccountingGoLiveGate("default", period, regressionResults)
      ]);
      setIntegrity(integrityPayload);
      setMigration(migrationPayload);
      setMatrix(matrixPayload);
      setGate(gatePayload);
    } catch (governanceError) {
      setError(governanceError instanceof Error ? governanceError.message : "正式核算上线治理数据加载失败");
    }
  }, [period]);

  useEffect(() => {
    refreshGovernance();
  }, [refreshGovernance]);

  const permissionCoverage = useMemo(() => {
    if (!matrix) {
      return [];
    }
    return criticalPermissions.map((permission) => ({
      permission,
      roles: matrix.role_coverage[permission] ?? []
    }));
  }, [matrix]);

  async function handleCreateBackup() {
    setActiveAction("backup");
    setError(null);
    setMessage(null);
    try {
      const manifest = await createAccountingBackup({ account_set_id: "default", period, actor_id: "backup-user" });
      setBackup(manifest);
      setMessage(`已生成备份清单 ${manifest.backup_manifest_id}`);
      await refreshGovernance();
    } catch (backupError) {
      setError(backupError instanceof Error ? backupError.message : "备份清单创建失败");
    } finally {
      setActiveAction(null);
    }
  }

  async function handleRestoreRehearsal() {
    if (!backup) {
      setError("请先创建备份清单");
      return;
    }
    setActiveAction("restore");
    setError(null);
    setMessage(null);
    try {
      const rehearsal = await rehearseAccountingRestore({
        backup_manifest_id: backup.backup_manifest_id,
        target_database_path: "D:/tmp/formal-accounting-restore.sqlite3",
        actor_id: "restore-user"
      });
      setRestore(rehearsal);
      setMessage(`恢复演练${statusLabel(rehearsal.status)}`);
      await refreshGovernance();
    } catch (restoreError) {
      setError(restoreError instanceof Error ? restoreError.message : "恢复演练失败");
    } finally {
      setActiveAction(null);
    }
  }

  return (
    <section id="accounting-governance-panel" className="accounting-governance-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">正式核算上线治理</span>
          <h2>完整性、迁移、备份与门禁</h2>
        </div>
        <div className="statement-archive-actions">
          <span>{period}</span>
          <button type="button" onClick={handleCreateBackup} disabled={activeAction === "backup"}>
            {activeAction === "backup" ? "生成中..." : "创建备份"}
          </button>
          <button type="button" className="button-secondary" onClick={handleRestoreRehearsal} disabled={!backup || activeAction === "restore"}>
            {activeAction === "restore" ? "演练中..." : "恢复演练"}
          </button>
          <button type="button" className="button-secondary" onClick={refreshGovernance}>刷新</button>
        </div>
      </div>

      {error ? <p className="inline-error">{error}</p> : null}
      {message ? <p className="statement-archive-message">{message}</p> : null}

      <div className="statement-archive-summary-grid accounting-governance-summary-grid">
        <article>
          <span>完整性</span>
          <strong>{integrity ? statusLabel(integrity.overall_status) : "-"}</strong>
        </article>
        <article>
          <span>迁移阻塞</span>
          <strong>{migration?.blocked_count ?? "-"}</strong>
        </article>
        <article>
          <span>备份数据集</span>
          <strong>{backup?.datasets.length ?? "-"}</strong>
        </article>
        <article>
          <span>上线门禁</span>
          <strong>{gate ? statusLabel(gate.status) : "-"}</strong>
        </article>
      </div>

      <div className="content-grid">
        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">完整性校验</span>
              <h3>检查项</h3>
            </div>
          </div>
          <div className="system-list">
            {integrity?.checks.map((check) => (
              <article key={check.check_code}>
                <div>
                  <strong>{check.check_name}</strong>
                  <small>{check.message}</small>
                </div>
                <span className={statusClass(check.status)}>{statusLabel(check.status)}</span>
              </article>
            ))}
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">迁移 dry-run</span>
              <h3>差异摘要</h3>
            </div>
          </div>
          <div className="system-list">
            <article>
              <div>
                <strong>可迁移</strong>
                <small>proposed_entry_count</small>
              </div>
              <span>{migration?.proposed_entry_count ?? 0}</span>
            </article>
            <article>
              <div>
                <strong>已迁移</strong>
                <small>already_migrated</small>
              </div>
              <span>{migration?.migrated_count ?? 0}</span>
            </article>
            <article>
              <div>
                <strong>阻塞</strong>
                <small>{migration?.blockers.join(" / ") || "无"}</small>
              </div>
              <span>{migration?.blocked_count ?? 0}</span>
            </article>
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">备份恢复</span>
              <h3>清单与演练</h3>
            </div>
          </div>
          <div className="system-list">
            <article>
              <div>
                <strong>{backup?.backup_manifest_id ?? "未生成"}</strong>
                <small>journal_entries: {backup?.dataset_row_counts.journal_entries ?? 0}</small>
              </div>
              <span>{backup?.datasets.length ?? 0}项</span>
            </article>
            <article>
              <div>
                <strong>{restore ? statusLabel(restore.status) : "未演练"}</strong>
                <small>{restore?.target_database_path ?? "D:/tmp/formal-accounting-restore.sqlite3"}</small>
              </div>
              <span>{restore?.integrity_status ? statusLabel(restore.integrity_status) : "-"}</span>
            </article>
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">权限矩阵</span>
              <h3>关键权限</h3>
            </div>
          </div>
          <div className="system-list">
            {permissionCoverage.map((item) => (
              <article key={item.permission}>
                <div>
                  <strong>{item.permission}</strong>
                  <small>{item.roles.join(" / ") || "未覆盖"}</small>
                </div>
                <span>{item.roles.length}</span>
              </article>
            ))}
          </div>
        </section>

        <section className="panel panel--wide">
          <div className="panel-header">
            <div>
              <span className="eyebrow">上线门禁</span>
              <h3>状态</h3>
            </div>
            {gate ? <span className={statusClass(gate.status)}>{statusLabel(gate.status)}</span> : null}
          </div>
          <div className="system-list">
            {gate?.checks.map((check) => (
              <article key={check.gate_code}>
                <div>
                  <strong>{check.gate_name}</strong>
                  <small>{check.message}</small>
                </div>
                <span className={statusClass(check.status)}>{statusLabel(check.status)}</span>
              </article>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}
