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
  FileSearchOutlined,
  FolderAddOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined
} from "@ant-design/icons";
import { type Key, useCallback, useEffect, useMemo, useState } from "react";
import {
  createAccountingArchiveCase,
  downloadAccountingArchivePackage,
  fetchAccountingArchiveDocuments
} from "../services/dashboardApi";
import type {
  ArchiveDocument,
  ArchiveOcrStatus,
  ArchiveStatus,
  ArchiveStorageStatus,
  ArchiveVerificationStatus
} from "../types/accountingArchive";

const { Paragraph, Text, Title } = Typography;

interface AccountingArchivePanelProps {
  period: string;
}

const archiveStatusLabels: Record<ArchiveStatus, string> = {
  draft: "草稿",
  indexed: "已索引",
  archived: "已归档",
  locked: "已锁定"
};

const storageStatusLabels: Record<ArchiveStorageStatus, string> = {
  metadata_only: "仅元数据",
  stored: "已存储"
};

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

const ocrStatusColors: Record<ArchiveOcrStatus, string> = {
  not_required: "default",
  text_parsed: "green",
  engine_required: "orange",
  failed: "red"
};

const verificationStatusColors: Record<ArchiveVerificationStatus, string> = {
  not_required: "default",
  pending_external: "orange",
  verified: "green",
  failed: "red"
};

const archiveStatusColors: Record<ArchiveStatus, string> = {
  draft: "orange",
  indexed: "blue",
  archived: "green",
  locked: "purple"
};

function shortHash(value: string | null | undefined) {
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

function formatTime(value: string | null | undefined) {
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

  const summary = useMemo(() => {
    const pendingVerification = documents.filter((document) => document.verification_status === "pending_external").length;
    const engineRequired = documents.filter((document) => document.ocr_status === "engine_required").length;
    const storedCount = documents.filter((document) => document.storage_status === "stored").length;
    const totalSize = documents.reduce((total, document) => total + document.size, 0);
    const latest = documents[0] ?? null;
    return {
      total: documents.length,
      selected: selectedIds.length,
      pendingVerification,
      engineRequired,
      storedCount,
      totalSize,
      latestHash: shortHash(latest?.sha256_hash),
      latestCreator: latest?.uploaded_by ?? "-"
    };
  }, [documents, selectedIds.length]);

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

  const columns: TableColumnsType<ArchiveDocument> = [
    {
      title: "文件",
      dataIndex: "filename",
      key: "filename",
      width: 260,
      fixed: "left",
      sorter: (a, b) => a.filename.localeCompare(b.filename),
      render: (value: string, document) => (
        <Space orientation="vertical" size={0}>
          <Text strong>{value}</Text>
          <Text type="secondary">{document.document_type} · {formatBytes(document.size)}</Text>
        </Space>
      )
    },
    {
      title: "来源",
      key: "source",
      width: 150,
      render: (_, document) => sourceLabel(document)
    },
    {
      title: "OCR 状态",
      dataIndex: "ocr_status",
      key: "ocr_status",
      width: 140,
      filters: Object.entries(ocrStatusLabels).map(([value, text]) => ({ value, text })),
      onFilter: (value, document) => document.ocr_status === value,
      render: (value: ArchiveOcrStatus) => <Tag color={ocrStatusColors[value]}>{ocrStatusLabels[value]}</Tag>
    },
    {
      title: "验真状态",
      dataIndex: "verification_status",
      key: "verification_status",
      width: 140,
      filters: Object.entries(verificationStatusLabels).map(([value, text]) => ({ value, text })),
      onFilter: (value, document) => document.verification_status === value,
      render: (value: ArchiveVerificationStatus) => (
        <Tag color={verificationStatusColors[value]}>{verificationStatusLabels[value]}</Tag>
      )
    },
    {
      title: "归档状态",
      dataIndex: "archive_status",
      key: "archive_status",
      width: 130,
      render: (value: ArchiveStatus) => <Tag color={archiveStatusColors[value]}>{archiveStatusLabels[value]}</Tag>
    },
    {
      title: "存储",
      dataIndex: "storage_status",
      key: "storage_status",
      width: 120,
      render: (value: ArchiveStorageStatus) => storageStatusLabels[value]
    },
    {
      title: "保管期限",
      dataIndex: "retention_years",
      key: "retention_years",
      align: "right",
      width: 110,
      render: (value: number) => `${value} 年`
    },
    {
      title: "哈希校验",
      dataIndex: "sha256_hash",
      key: "sha256_hash",
      width: 150,
      render: (value: string) => <Text code>{shortHash(value)}</Text>
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 190,
      render: (value: string) => formatTime(value)
    }
  ];

  const rowSelection = {
    selectedRowKeys: selectedIds,
    onChange: (nextSelectedRowKeys: Key[]) => {
      setSelectedIds(nextSelectedRowKeys.map(String));
    }
  };

  return (
    <section id="accounting-archive-panel" className="accounting-archive-panel accounting-archive-workbench">
      <Card className="accounting-archive-hero">
        <div className="accounting-archive-toolbar">
          <div>
            <Text className="eyebrow">会计档案</Text>
            <Title level={3}>电子凭证与档案案卷工作台</Title>
            <Paragraph type="secondary">
              将电子凭证、OCR 状态、验真状态、哈希校验、保管期限和归档包下载集中到案卷编制界面。
            </Paragraph>
          </div>
          <Space wrap>
            <Tag color="blue">{period}</Tag>
            <Button icon={<ReloadOutlined />} loading={isLoading} onClick={refreshDocuments}>
              刷新
            </Button>
            <Button
              type="primary"
              icon={<FolderAddOutlined />}
              loading={activeAction === "create"}
              disabled={selectedIds.length === 0}
              onClick={handleCreateCase}
            >
              创建案卷
            </Button>
            <Button
              icon={<CloudDownloadOutlined />}
              loading={activeAction === "download"}
              disabled={!lastCaseId}
              onClick={handleDownloadPackage}
            >
              下载归档包
            </Button>
          </Space>
        </div>
      </Card>

      {error ? <Alert type="warning" showIcon message={error} /> : null}
      {message ? <Alert type="success" showIcon message={message} /> : null}

      <Row gutter={[16, 16]} className="accounting-archive-summary-grid">
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="accounting-archive-metric">
            <Statistic title="档案文档" value={summary.total} suffix="份" prefix={<FileDoneOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="accounting-archive-metric">
            <Statistic title="案卷编制" value={summary.selected} suffix="已选" prefix={<FolderAddOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="accounting-archive-metric">
            <Statistic title="待验真" value={summary.pendingVerification} prefix={<SafetyCertificateOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="accounting-archive-metric">
            <Statistic title="待 OCR" value={summary.engineRequired} prefix={<FileSearchOutlined />} />
          </Card>
        </Col>
      </Row>

      <div className="accounting-archive-layout">
        <Card className="accounting-archive-card accounting-archive-main" title="档案台账">
          <Table
            className="accounting-archive-ledger-table"
            rowKey="archive_document_id"
            rowSelection={rowSelection}
            columns={columns}
            dataSource={documents}
            loading={isLoading}
            pagination={{ pageSize: 8, showSizeChanger: false }}
            scroll={{ x: 1390 }}
            locale={{ emptyText: isLoading ? "正在读取会计档案" : "当前期间暂无会计档案文档" }}
          />
        </Card>

        <Card className="accounting-archive-card" title="案卷编制">
          <div className="accounting-archive-case-list">
            <article>
              <strong>已选择文档</strong>
              <Tag color={summary.selected ? "blue" : "default"}>{summary.selected} 份</Tag>
            </article>
            <article>
              <strong>归档包下载</strong>
              <Tag color={lastCaseId ? "green" : "orange"}>{lastCaseId ? "可下载" : "待建案"}</Tag>
            </article>
            <article>
              <strong>存储状态</strong>
              <Tag color={summary.storedCount === summary.total && summary.total ? "green" : "orange"}>
                {summary.storedCount}/{summary.total}
              </Tag>
            </article>
          </div>
        </Card>

        <Card className="accounting-archive-card" title="哈希校验">
          <div className="accounting-archive-audit-list">
            <p><span>最新哈希</span><Text code>{summary.latestHash}</Text></p>
            <p><span>上传人</span><strong>{summary.latestCreator}</strong></p>
            <p><span>总容量</span><strong>{formatBytes(summary.totalSize)}</strong></p>
          </div>
        </Card>

        <Card className="accounting-archive-card accounting-archive-help-card" title="保管期限">
          <Tabs
            items={[
              {
                key: "voucher",
                label: "电子凭证",
                children: <Paragraph type="secondary">凭证附件、OCR 文本和验真结果进入同一案卷，便于审计追溯。</Paragraph>
              },
              {
                key: "package",
                label: "归档包下载",
                children: <Paragraph type="secondary">创建案卷后可下载归档包，包内保留文档清单、哈希摘要和保管期限。</Paragraph>
              }
            ]}
          />
        </Card>
      </div>
    </section>
  );
}
