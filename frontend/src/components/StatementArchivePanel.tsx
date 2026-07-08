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
  CloudDownloadOutlined,
  FileDoneOutlined,
  FileExcelOutlined,
  FilePdfOutlined,
  LockOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined
} from "@ant-design/icons";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  createStatementSnapshot,
  exportStatementSnapshot,
  listStatementSnapshots,
  lockStatementSnapshot
} from "../services/dashboardApi";
import type { StatementArchiveStatus, StatementSnapshot, StatementValidationStatus } from "../types/statementArchive";

const { Paragraph, Text, Title } = Typography;

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

const archiveStatusColors: Record<StatementArchiveStatus, string> = {
  draft: "orange",
  locked: "blue",
  archived: "green",
  demo_only: "default"
};

const validationStatusColors: Record<StatementValidationStatus, string> = {
  passed: "green",
  warning: "orange",
  failed: "red"
};

function formatTime(value: string | null | undefined) {
  if (!value) {
    return "-";
  }
  return value.replace("T", " ").replace("Z", "");
}

function shortHash(value: string | null | undefined) {
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
    const passedCount = snapshots.filter((snapshot) => snapshot.validation_status === "passed").length;
    const latest = snapshots[0] ?? null;
    return {
      total: snapshots.length,
      lockedCount,
      passedCount,
      latestVersion: latest ? `V${latest.version}` : "-",
      latestHash: latest ? shortHash(latest.content_hash) : "-",
      latestStatus: latest ? archiveStatusLabels[latest.archive_status] : "待生成",
      latestCreator: latest?.created_by ?? "-"
    };
  }, [snapshots]);

  const deliverySteps = useMemo(() => {
    const latest = snapshots[0] ?? null;
    return [
      {
        key: "snapshot",
        title: "快照版本",
        status: latest ? "已生成" : "待生成",
        tone: latest ? "green" : "orange",
        detail: latest ? `${latest.company_name} ${latest.period} ${summary.latestVersion}` : "生成快照后进入正式交付流程"
      },
      {
        key: "hash",
        title: "哈希校验",
        status: latest?.content_hash ? "已记录" : "待记录",
        tone: latest?.content_hash ? "blue" : "default",
        detail: `内容哈希 ${summary.latestHash}`
      },
      {
        key: "lock",
        title: "锁定状态",
        status: latest?.locked ? "已锁定" : "待锁定",
        tone: latest?.locked ? "green" : "orange",
        detail: latest?.locked ? `锁定人 ${latest.locked_by ?? "-"}，${formatTime(latest.locked_at)}` : "锁定后保留审计线索"
      },
      {
        key: "export",
        title: "正式交付",
        status: latest?.locked ? "可导出" : "待锁定",
        tone: latest?.locked ? "blue" : "default",
        detail: "支持 Excel 与 PDF 报表包导出"
      }
    ];
  }, [snapshots, summary.latestHash, summary.latestVersion]);

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

  const columns: TableColumnsType<StatementSnapshot> = [
    {
      title: "快照版本",
      key: "version",
      width: 130,
      fixed: "left",
      sorter: (a, b) => b.version - a.version,
      render: (_, snapshot) => (
        <Space orientation="vertical" size={0}>
          <Text strong>V{snapshot.version}</Text>
          <Text type="secondary">{snapshot.period}</Text>
        </Space>
      )
    },
    {
      title: "来源",
      dataIndex: "source",
      key: "source",
      width: 140,
      render: (value: string) => sourceLabel(value)
    },
    {
      title: "校验",
      dataIndex: "validation_status",
      key: "validation_status",
      width: 120,
      filters: Object.entries(validationStatusLabels).map(([value, text]) => ({ value, text })),
      onFilter: (value, snapshot) => snapshot.validation_status === value,
      render: (value: StatementValidationStatus) => (
        <Tag color={validationStatusColors[value]}>{validationStatusLabels[value]}</Tag>
      )
    },
    {
      title: "锁定状态",
      dataIndex: "archive_status",
      key: "archive_status",
      width: 130,
      filters: Object.entries(archiveStatusLabels).map(([value, text]) => ({ value, text })),
      onFilter: (value, snapshot) => snapshot.archive_status === value,
      render: (value: StatementArchiveStatus) => (
        <Tag color={archiveStatusColors[value]}>{archiveStatusLabels[value]}</Tag>
      )
    },
    {
      title: "哈希校验",
      dataIndex: "content_hash",
      key: "content_hash",
      width: 150,
      render: (value: string) => <Text code>{shortHash(value)}</Text>
    },
    {
      title: "审计信息",
      key: "audit",
      width: 260,
      render: (_, snapshot) => (
        <Space orientation="vertical" size={0}>
          <Text>{snapshot.created_by} 创建于 {formatTime(snapshot.created_at)}</Text>
          <Text type="secondary">
            {snapshot.locked ? `${snapshot.locked_by ?? "-"} 锁定于 ${formatTime(snapshot.locked_at)}` : "未锁定"}
          </Text>
        </Space>
      )
    },
    {
      title: "动作",
      key: "actions",
      width: 280,
      render: (_, snapshot) => (
        <Space wrap>
          <Button
            size="small"
            icon={<LockOutlined />}
            loading={activeAction === `lock:${snapshot.snapshot_id}`}
            disabled={snapshot.locked}
            onClick={() => handleLockSnapshot(snapshot.snapshot_id)}
          >
            {snapshot.locked ? "已锁定" : "锁定归档"}
          </Button>
          <Button
            size="small"
            icon={<FileExcelOutlined />}
            loading={activeAction === `export:xlsx:${snapshot.snapshot_id}`}
            onClick={() => handleExportSnapshot(snapshot.snapshot_id, "xlsx")}
          >
            Excel
          </Button>
          <Button
            size="small"
            icon={<FilePdfOutlined />}
            loading={activeAction === `export:pdf:${snapshot.snapshot_id}`}
            onClick={() => handleExportSnapshot(snapshot.snapshot_id, "pdf")}
          >
            PDF
          </Button>
        </Space>
      )
    }
  ];

  return (
    <section id="statement-archive-panel" className="statement-archive-panel statement-archive-workbench">
      <Card className="statement-archive-hero">
        <div className="statement-archive-toolbar">
          <div>
            <Text className="eyebrow">报表归档</Text>
            <Title level={3}>归档与正式交付工作台</Title>
            <Paragraph type="secondary">
              将快照版本、锁定状态、哈希校验、审计信息和导出报表包集中到同一个正式交付界面。
            </Paragraph>
          </div>
          <Space wrap>
            <Tag color="blue">{period}</Tag>
            <Button icon={<ReloadOutlined />} loading={isLoading} onClick={refreshSnapshots}>
              刷新
            </Button>
            <Button type="primary" icon={<FileDoneOutlined />} loading={activeAction === "create"} onClick={handleCreateSnapshot}>
              生成快照
            </Button>
          </Space>
        </div>
      </Card>

      {error ? <Alert type="warning" showIcon message={error} /> : null}
      {message ? <Alert type="success" showIcon message={message} /> : null}

      <Row gutter={[16, 16]} className="statement-archive-summary-grid">
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="statement-archive-metric">
            <Statistic title="快照版本" value={summary.total} suffix="个" prefix={<FileDoneOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="statement-archive-metric">
            <Statistic title="锁定状态" value={summary.lockedCount} suffix={`/${summary.total}`} prefix={<LockOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="statement-archive-metric">
            <Statistic title="校验通过" value={summary.passedCount} suffix={`/${summary.total}`} prefix={<SafetyCertificateOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="statement-archive-metric">
            <Statistic title="最新版本" value={summary.latestVersion} />
          </Card>
        </Col>
      </Row>

      <div className="statement-archive-layout">
        <Card className="statement-archive-card statement-archive-main" title="归档台账">
          <Table
            className="statement-archive-ledger-table"
            rowKey="snapshot_id"
            columns={columns}
            dataSource={snapshots}
            loading={isLoading}
            pagination={{ pageSize: 6, showSizeChanger: false }}
            scroll={{ x: 1210 }}
            locale={{ emptyText: isLoading ? "正在读取报表快照" : "暂无报表快照" }}
          />
        </Card>

        <Card className="statement-archive-card" title="正式交付">
          <div className="statement-archive-delivery-list">
            {deliverySteps.map((step) => (
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

        <Card className="statement-archive-card" title="审计信息">
          <div className="statement-archive-audit-list">
            <p><span>最新状态</span><strong>{summary.latestStatus}</strong></p>
            <p><span>创建人</span><strong>{summary.latestCreator}</strong></p>
            <p><span>哈希校验</span><Text code>{summary.latestHash}</Text></p>
          </div>
        </Card>

        <Card className="statement-archive-card statement-archive-export-card" title="导出报表包">
          <Tabs
            items={[
              {
                key: "excel",
                label: "Excel",
                children: (
                  <Paragraph type="secondary">
                    适合正式报送、管理层复核和后续数据加工，导出时保留当前快照版本和哈希线索。
                  </Paragraph>
                )
              },
              {
                key: "pdf",
                label: "PDF",
                children: (
                  <Paragraph type="secondary">
                    适合签批、归档和审计留痕，锁定快照后建议同步导出 PDF 归档件。
                  </Paragraph>
                )
              }
            ]}
          />
          <Button icon={<CloudDownloadOutlined />} href="#statement-archive-panel">
            从归档台账选择版本导出
          </Button>
        </Card>
      </div>
    </section>
  );
}
