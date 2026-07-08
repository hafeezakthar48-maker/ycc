import { Alert, Button, Card, Progress, Space, Table, Tag, Typography } from "antd";
import type { TableColumnsType } from "antd";
import { useEffect, useMemo, useState } from "react";
import {
  addRiskProcessRecord,
  addRiskReviewRecord,
  assignRiskOwner,
  fetchRiskClosures
} from "../services/riskClosureApi";
import type { RiskItem } from "../types/dashboard";
import type { RiskClosureItem, RiskClosureListResponse, RiskClosureStatus } from "../types/riskClosure";

const { Paragraph, Text } = Typography;

interface RiskPanelProps {
  risks: RiskItem[];
  period: string;
}

const statusLabel: Record<RiskClosureStatus, string> = {
  open: "待分派",
  assigned: "已分派",
  processing: "处理中",
  resolved: "待复核",
  closed: "已关闭"
};

const statusTone: Record<RiskClosureStatus, string> = {
  open: "default",
  assigned: "blue",
  processing: "processing",
  resolved: "warning",
  closed: "success"
};

function toOpenClosure(period: string, risk: RiskItem): RiskClosureItem {
  return {
    period,
    risk,
    status: "open",
    owner: null,
    due_date: null,
    process_records: [],
    review_records: []
  };
}

function riskColor(level: number) {
  if (level >= 4) {
    return "red";
  }
  if (level >= 3) {
    return "orange";
  }
  return "green";
}

export default function RiskPanel({ risks, period }: RiskPanelProps) {
  const [closureResponse, setClosureResponse] = useState<RiskClosureListResponse | null>(null);
  const [busyRiskId, setBusyRiskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fallbackItems = useMemo(() => risks.map((risk) => toOpenClosure(period, risk)), [period, risks]);
  const items = closureResponse?.items ?? fallbackItems;
  const openCount = closureResponse?.open_count ?? items.filter((item) => item.status !== "closed").length;
  const closedCount = closureResponse?.closed_count ?? items.filter((item) => item.status === "closed").length;
  const closureProgress = items.length ? Math.round(closedCount / items.length * 100) : 0;

  async function reloadClosures() {
    const response = await fetchRiskClosures(period);
    setClosureResponse(response);
  }

  useEffect(() => {
    let cancelled = false;

    fetchRiskClosures(period)
      .then((response) => {
        if (!cancelled) {
          setClosureResponse(response);
          setError(null);
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setClosureResponse(null);
          setError(loadError instanceof Error ? loadError.message : "风险闭环加载失败");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [period]);

  async function runRiskAction(riskId: string, action: () => Promise<RiskClosureItem>) {
    setBusyRiskId(riskId);
    setError(null);
    try {
      await action();
      await reloadClosures();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "风险闭环操作失败");
    } finally {
      setBusyRiskId(null);
    }
  }

  const columns: TableColumnsType<RiskClosureItem> = [
    {
      title: "风险事项",
      dataIndex: ["risk", "title"],
      sorter: (a, b) => a.risk.title.localeCompare(b.risk.title),
      render: (_value, item) => (
        <Space orientation="vertical" size={2}>
          <strong>{item.risk.title}</strong>
          <Text type="secondary">{item.risk.trigger_reason}</Text>
        </Space>
      )
    },
    {
      title: "风险等级",
      dataIndex: ["risk", "level"],
      width: 112,
      sorter: (a, b) => a.risk.level - b.risk.level,
      render: (_value, item) => <Tag color={riskColor(item.risk.level)}>{item.risk.level_label}</Tag>
    },
    {
      title: "闭环状态",
      dataIndex: "status",
      width: 112,
      filters: Object.entries(statusLabel).map(([value, text]) => ({ text, value })),
      onFilter: (value, item) => item.status === value,
      render: (value: RiskClosureStatus) => <Tag color={statusTone[value]}>{statusLabel[value]}</Tag>
    },
    {
      title: "负责人",
      dataIndex: "owner",
      width: 120,
      render: (value: string | null) => value ?? <Text type="secondary">未分派</Text>
    },
    {
      title: "到期日",
      dataIndex: "due_date",
      width: 120,
      render: (value: string | null) => value ?? "-"
    },
    {
      title: "记录",
      width: 126,
      render: (_value, item) => (
        <Space orientation="vertical" size={0}>
          <Text>处理记录 {item.process_records.length}</Text>
          <Text type="secondary">复核记录 {item.review_records.length}</Text>
        </Space>
      )
    },
    {
      title: "操作",
      width: 230,
      render: (_value, item) => (
        <Space wrap>
          <Button
            size="small"
            loading={busyRiskId === item.risk.id}
            disabled={item.status === "closed"}
            onClick={() => runRiskAction(
              item.risk.id,
              () => assignRiskOwner(item.risk.id, {
                period,
                owner: "财务主管",
                due_date: "2026-07-10",
                note: "先复核触发原因和建议检查资料。"
              })
            )}
          >
            分派
          </Button>
          <Button
            size="small"
            loading={busyRiskId === item.risk.id}
            disabled={item.status === "closed"}
            onClick={() => runRiskAction(
              item.risk.id,
              () => addRiskProcessRecord(item.risk.id, {
                period,
                handler: item.owner ?? "财务主管",
                action: "已完成初步复核",
                note: "已核对触发原因，并形成后续处理建议。",
                next_status: "processing"
              })
            )}
          >
            处理
          </Button>
          <Button
            size="small"
            type="primary"
            loading={busyRiskId === item.risk.id}
            disabled={item.status === "closed"}
            onClick={() => runRiskAction(
              item.risk.id,
              () => addRiskReviewRecord(item.risk.id, {
                period,
                reviewer: "内控复核员",
                conclusion: "复核记录完整，准予关闭。",
                next_status: "closed"
              })
            )}
          >
            复核关闭
          </Button>
        </Space>
      )
    }
  ];

  return (
    <section className="risk-closure-workbench">
      <Card
        title="风险闭环工作台"
        extra={<Tag color={openCount ? "orange" : "green"}>{period}</Tag>}
      >
        <div className="risk-closure-toolbar">
          <div>
            <Text className="eyebrow">闭环进度</Text>
            <Progress percent={closureProgress} status={openCount ? "active" : "success"} />
          </div>
          <Space wrap>
            <Tag color="orange">未关闭 {openCount}</Tag>
            <Tag color="green">已关闭 {closedCount}</Tag>
            <Tag>总计 {items.length}</Tag>
          </Space>
        </div>

        {error ? <Alert type="warning" showIcon message={error} /> : null}

        <Table
          className="risk-closure-table"
          rowKey={(item) => item.risk.id}
          columns={columns}
          dataSource={items}
          pagination={{ pageSize: 5, showSizeChanger: false }}
          scroll={{ x: 980 }}
          expandable={{
            expandedRowRender: (item) => (
              <div className="risk-closure-detail">
                <Paragraph>{item.risk.description}</Paragraph>
                <div>
                  <strong>建议检查资料</strong>
                  <ul>
                    {item.risk.suggested_checks.map((checkItem) => (
                      <li key={checkItem}>{checkItem}</li>
                    ))}
                  </ul>
                </div>
                <Paragraph>{item.risk.compliance_note}</Paragraph>
              </div>
            )
          }}
        />
      </Card>
    </section>
  );
}
