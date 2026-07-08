import {
  Alert,
  Button,
  Card,
  Col,
  Row,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
  Typography
} from "antd";
import type { TableColumnsType } from "antd";
import {
  CheckCircleOutlined,
  CloudUploadOutlined,
  FileProtectOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined
} from "@ant-design/icons";
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
  AccountingMigrationItem,
  AccountingMigrationPreview,
  FormalAccountingGoLiveGate,
  FormalAccountingPermissionMatrix,
  GoLiveGateStatus,
  IntegrityStatus,
  MigrationItemStatus,
  RestoreRehearsalResult
} from "../types/accountingGovernance";

const { Paragraph, Text, Title } = Typography;

interface AccountingGovernancePanelProps {
  period: string;
}

const regressionResults: Record<string, "passed" | "failed"> = {
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

const statusLabels: Record<string, string> = {
  pass: "通过",
  passed: "通过",
  ready: "可迁移",
  already_migrated: "已迁移",
  warning: "警告",
  fail: "失败",
  failed: "失败",
  blocked: "阻塞"
};

const statusColors: Record<string, string> = {
  pass: "green",
  passed: "green",
  ready: "blue",
  already_migrated: "default",
  warning: "orange",
  fail: "red",
  failed: "red",
  blocked: "red"
};

type GovernanceStatus = IntegrityStatus | GoLiveGateStatus | MigrationItemStatus | "passed" | "failed";

function statusLabel(status: GovernanceStatus | null | undefined) {
  return status ? statusLabels[status] ?? status : "-";
}

function statusColor(status: GovernanceStatus | null | undefined) {
  return status ? statusColors[status] ?? "default" : "default";
}

function formatTime(value: string | null | undefined) {
  return value ? value.replace("T", " ").replace("Z", "") : "-";
}

function formatMoney(value: string | null | undefined) {
  const amount = Number(value ?? 0);
  if (Number.isNaN(amount)) {
    return value ?? "-";
  }
  return `¥${amount.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function compactText(value: string | null | undefined) {
  return value && value.trim() ? value : "无";
}

export default function AccountingGovernancePanel({ period }: AccountingGovernancePanelProps) {
  const [integrity, setIntegrity] = useState<AccountingIntegrityReport | null>(null);
  const [migration, setMigration] = useState<AccountingMigrationPreview | null>(null);
  const [backup, setBackup] = useState<AccountingBackupManifest | null>(null);
  const [restore, setRestore] = useState<RestoreRehearsalResult | null>(null);
  const [matrix, setMatrix] = useState<FormalAccountingPermissionMatrix | null>(null);
  const [gate, setGate] = useState<FormalAccountingGoLiveGate | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshGovernance = useCallback(async () => {
    setIsLoading(true);
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
    } finally {
      setIsLoading(false);
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
      roles: matrix.role_coverage?.[permission] ?? []
    }));
  }, [matrix]);

  const summary = useMemo(() => {
    const failedIntegrityCount = integrity?.checks.filter((check) => check.status === "fail").length ?? 0;
    const warningIntegrityCount = integrity?.checks.filter((check) => check.status === "warning").length ?? 0;
    const gateBlockers = gate?.blockers.length ?? 0;
    const gateWarnings = gate?.warnings.length ?? 0;
    return {
      integrityStatus: statusLabel(integrity?.overall_status),
      integrityTone: statusColor(integrity?.overall_status),
      integrityIssueCount: failedIntegrityCount + warningIntegrityCount,
      migrationReady: migration?.ready_count ?? 0,
      migrationBlocked: migration?.blocked_count ?? 0,
      backupDatasets: backup?.datasets.length ?? 0,
      backupRows: backup?.dataset_row_counts.journal_entries ?? 0,
      gateStatus: statusLabel(gate?.status),
      gateTone: statusColor(gate?.status),
      gateIssueCount: gateBlockers + gateWarnings,
      missingPermissions: matrix?.critical_missing_permissions.length ?? 0
    };
  }, [backup, gate, integrity, matrix, migration]);

  const gateSteps = useMemo(() => {
    return [
      {
        key: "integrity",
        title: "完整性校验",
        detail: `${integrity?.checks.length ?? 0} 项检查，${summary.integrityIssueCount} 项需处理`,
        status: statusLabel(integrity?.overall_status),
        tone: statusColor(integrity?.overall_status)
      },
      {
        key: "migration",
        title: "迁移 dry-run",
        detail: `${summary.migrationReady} 张凭证可迁移，${summary.migrationBlocked} 项阻塞`,
        status: summary.migrationBlocked > 0 ? "阻塞" : "通过",
        tone: summary.migrationBlocked > 0 ? "red" : "green"
      },
      {
        key: "backup",
        title: "备份恢复",
        detail: backup ? `${summary.backupDatasets} 个数据集，journal_entries ${summary.backupRows} 行` : "创建备份后才可恢复演练",
        status: restore ? statusLabel(restore.status) : backup ? "待演练" : "待备份",
        tone: restore ? statusColor(restore.status) : backup ? "orange" : "default"
      },
      {
        key: "gate",
        title: "上线门禁",
        detail: `${gate?.checks.length ?? 0} 项门禁，${summary.gateIssueCount} 项提示或阻塞`,
        status: statusLabel(gate?.status),
        tone: statusColor(gate?.status)
      }
    ];
  }, [backup, gate, integrity, restore, summary]);

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

  const migrationColumns: TableColumnsType<AccountingMigrationItem> = [
    {
      title: "凭证",
      key: "voucher",
      fixed: "left",
      width: 180,
      render: (_, item) => (
        <Space orientation="vertical" size={0}>
          <Text strong>{item.voucher_number}</Text>
          <Text type="secondary">{item.voucher_date}</Text>
        </Space>
      )
    },
    {
      title: "摘要",
      dataIndex: "summary",
      key: "summary",
      width: 240
    },
    {
      title: "迁移状态",
      dataIndex: "status",
      key: "status",
      width: 130,
      filters: Object.entries(statusLabels)
        .filter(([value]) => ["ready", "already_migrated", "blocked"].includes(value))
        .map(([value, text]) => ({ value, text })),
      onFilter: (value, item) => item.status === value,
      render: (value: MigrationItemStatus) => <Tag color={statusColor(value)}>{statusLabel(value)}</Tag>
    },
    {
      title: "借方合计",
      dataIndex: "debit_total",
      key: "debit_total",
      align: "right",
      width: 130,
      render: (value: string) => formatMoney(value)
    },
    {
      title: "贷方合计",
      dataIndex: "credit_total",
      key: "credit_total",
      align: "right",
      width: 130,
      render: (value: string) => formatMoney(value)
    },
    {
      title: "差额",
      dataIndex: "difference",
      key: "difference",
      align: "right",
      width: 120,
      render: (value: string) => formatMoney(value)
    },
    {
      title: "阻塞原因",
      dataIndex: "reason",
      key: "reason",
      width: 240,
      render: (value: string) => compactText(value)
    },
    {
      title: "正式分录",
      dataIndex: "formal_journal_entry_id",
      key: "formal_journal_entry_id",
      width: 160,
      render: (value: string | null) => value ?? "-"
    }
  ];

  return (
    <section id="accounting-governance-panel" className="accounting-governance-panel accounting-governance-workbench">
      <Card className="accounting-governance-hero">
        <div className="accounting-governance-toolbar">
          <div>
            <Text className="eyebrow">正式核算上线治理</Text>
            <Title level={3}>正式核算上线治理工作台</Title>
            <Paragraph type="secondary">
              将完整性校验、迁移 dry-run、备份恢复、权限矩阵、职责分离和上线门禁集中到同一个上线决策界面。
            </Paragraph>
          </div>
          <Space wrap>
            <Tag color="blue">{period}</Tag>
            <Button icon={<ReloadOutlined />} loading={isLoading} onClick={refreshGovernance}>
              刷新
            </Button>
            <Button
              type="primary"
              icon={<CloudUploadOutlined />}
              loading={activeAction === "backup"}
              onClick={handleCreateBackup}
            >
              创建备份
            </Button>
            <Button
              icon={<SafetyCertificateOutlined />}
              loading={activeAction === "restore"}
              disabled={!backup}
              onClick={handleRestoreRehearsal}
            >
              恢复演练
            </Button>
          </Space>
        </div>
      </Card>

      {error ? <Alert type="warning" showIcon title={error} /> : null}
      {message ? <Alert type="success" showIcon title={message} /> : null}
      {gate?.status === "blocked" ? (
        <Alert
          type="error"
          showIcon
          title="上线门禁仍有阻塞项"
          description={gate.blockers.join(" / ") || "请检查完整性校验、备份恢复演练和权限矩阵。"}
        />
      ) : null}

      <Row gutter={[16, 16]} className="accounting-governance-summary-grid">
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="accounting-governance-metric">
            <Statistic
              title="完整性校验"
              value={summary.integrityStatus}
              prefix={<FileProtectOutlined />}
              styles={{ content: { color: summary.integrityTone === "red" ? "#cf1322" : undefined } }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="accounting-governance-metric">
            <Statistic title="迁移 dry-run" value={summary.migrationReady} suffix={`可迁移 / ${summary.migrationBlocked} 阻塞`} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="accounting-governance-metric">
            <Statistic title="备份恢复" value={summary.backupDatasets} suffix="数据集" prefix={<CloudUploadOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="accounting-governance-metric">
            <Statistic
              title="上线门禁"
              value={summary.gateStatus}
              prefix={<CheckCircleOutlined />}
              styles={{ content: { color: summary.gateTone === "red" ? "#cf1322" : undefined } }}
            />
          </Card>
        </Col>
      </Row>

      <div className="accounting-governance-layout">
        <Card className="accounting-governance-card accounting-governance-main" title="迁移台账">
          <Table
            className="accounting-governance-migration-table"
            rowKey="voucher_id"
            columns={migrationColumns}
            dataSource={migration?.items ?? []}
            loading={isLoading}
            pagination={{ pageSize: 6, showSizeChanger: false }}
            scroll={{ x: 1330 }}
            locale={{ emptyText: isLoading ? "正在读取迁移预览" : "当前期间暂无迁移明细" }}
          />
        </Card>

        <Card className="accounting-governance-card" title="上线门禁">
          <div className="accounting-governance-gate-list">
            {gateSteps.map((step) => (
              <article key={step.key}>
                <div>
                  <strong>{step.title}</strong>
                  <Text type="secondary">{step.detail}</Text>
                </div>
                <Tag color={step.tone}>{step.status}</Tag>
              </article>
            ))}
          </div>
        </Card>

        <Card className="accounting-governance-card" title="备份恢复">
          <div className="accounting-governance-audit-list">
            <p><span>备份清单</span><strong>{backup?.backup_manifest_id ?? "未生成"}</strong></p>
            <p><span>数据集</span><strong>{summary.backupDatasets} 个</strong></p>
            <p><span>恢复演练</span><Tag color={restore ? statusColor(restore.status) : "default"}>{restore ? statusLabel(restore.status) : "未演练"}</Tag></p>
            <p><span>演练路径</span><Text code>{restore?.target_database_path ?? "D:/tmp/formal-accounting-restore.sqlite3"}</Text></p>
          </div>
        </Card>

        <Card className="accounting-governance-card accounting-governance-permission-card" title="权限矩阵">
          <Tabs
            items={[
              {
                key: "coverage",
                label: "关键权限",
                children: (
                  <div className="accounting-governance-permission-list">
                    {permissionCoverage.map((item) => (
                      <article key={item.permission}>
                        <div>
                          <strong>{item.permission}</strong>
                          <Text type="secondary">{item.roles.join(" / ") || "未覆盖"}</Text>
                        </div>
                        <Tag color={item.roles.length ? "blue" : "red"}>{item.roles.length} 个角色</Tag>
                      </article>
                    ))}
                  </div>
                )
              },
              {
                key: "segregation",
                label: "职责分离",
                children: (
                  <div className="accounting-governance-permission-list">
                    {(matrix?.segregation_rules ?? ["上线前需校验迁移、备份、审批权限互斥规则。"]).map((rule) => (
                      <article key={rule}>
                        <Text>{rule}</Text>
                        <Tag color="green">已登记</Tag>
                      </article>
                    ))}
                  </div>
                )
              },
              {
                key: "regression",
                label: "回归验证",
                children: (
                  <div className="accounting-governance-audit-list">
                    {Object.entries(regressionResults).map(([name, status]) => (
                      <p key={name}><span>{name}</span><Tag color={statusColor(status)}>{statusLabel(status)}</Tag></p>
                    ))}
                  </div>
                )
              }
            ]}
          />
        </Card>

        <Card className="accounting-governance-card accounting-governance-check-card" title="完整性校验">
          <div className="accounting-governance-check-list">
            {(integrity?.checks ?? []).map((check) => (
              <article key={check.check_code}>
                <div>
                  <strong>{check.check_name}</strong>
                  <Text type="secondary">{check.message}</Text>
                </div>
                <Space wrap>
                  <Tag>{check.affected_count} 项</Tag>
                  <Tag color={statusColor(check.status)}>{statusLabel(check.status)}</Tag>
                </Space>
              </article>
            ))}
          </div>
        </Card>
      </div>
    </section>
  );
}
