import {
  AlertOutlined,
  ArrowUpOutlined,
  CheckCircleOutlined,
  CloudDownloadOutlined,
  DollarOutlined,
  FilterOutlined,
  LineChartOutlined,
  PieChartOutlined,
  SearchOutlined,
  WalletOutlined
} from "@ant-design/icons";
import { Button, Card, Col, Input, Progress, Row, Select, Space, Statistic, Table, Tag, Typography } from "antd";
import type { TableColumnsType } from "antd";
import { useMemo, useState } from "react";
import CashFlowChart from "../charts/CashFlowChart";
import ExpensePieChart from "../charts/ExpensePieChart";
import TrendChart from "../charts/TrendChart";
import type { DashboardOverview, ManagementReport, MetricCard, RiskItem, TrendChartSeries } from "../types/dashboard";
import type { HomeDashboard, HomeMetric } from "../types/homeDashboard";

const { Text, Title } = Typography;

interface HomeDashboardPanelProps {
  dashboard: HomeDashboard;
  overview: DashboardOverview;
  report: ManagementReport;
  onOpenDataEntry: () => void;
  onOpenAiAdvisor: () => void;
}

const statusColorMap: Record<string, string> = {
  normal: "success",
  warning: "warning",
  danger: "error"
};

export default function HomeDashboardPanel({
  dashboard,
  overview,
  report,
  onOpenDataEntry,
  onOpenAiAdvisor
}: HomeDashboardPanelProps) {
  const [riskKeyword, setRiskKeyword] = useState("");
  const [riskLevel, setRiskLevel] = useState("all");
  const flatHomeMetrics = dashboard.sections.flatMap((section) => section.metrics);
  const costValue = formatLatestSeriesValue(overview.trend_series, "成本");
  const taxRate = findHomeMetric(flatHomeMetrics, "税")?.value ?? "3.8%";
  const riskStatus = overview.risks.length >= 3 ? "危险" : overview.risks.length > 0 ? "预警" : "正常";

  const cockpitMetrics = [
    {
      title: "收入",
      value: findOverviewMetric(overview.metrics, "收入")?.value ?? "--",
      note: "本期营业收入",
      icon: <DollarOutlined />,
      status: "normal"
    },
    {
      title: "成本",
      value: costValue,
      note: "按趋势数据估算",
      icon: <ArrowUpOutlined />,
      status: "warning"
    },
    {
      title: "利润",
      value: findOverviewMetric(overview.metrics, "净利润")?.value ?? "--",
      note: "当前期间净利润",
      icon: <LineChartOutlined />,
      status: "normal"
    },
    {
      title: "现金流",
      value: findOverviewMetric(overview.metrics, "现金流")?.value ?? "--",
      note: "经营现金流",
      icon: <WalletOutlined />,
      status: "warning"
    },
    {
      title: "税负率",
      value: taxRate,
      note: "收入 × 税负率估算",
      icon: <PieChartOutlined />,
      status: "normal"
    },
    {
      title: "风险等级",
      value: riskStatus,
      note: `${overview.risks.length} 项风险待处理`,
      icon: <AlertOutlined />,
      status: riskStatus === "危险" ? "danger" : riskStatus === "预警" ? "warning" : "normal"
    }
  ];

  const filteredRisks = useMemo(() => {
    return overview.risks.filter((risk) => {
      const matchesKeyword = `${risk.title}${risk.description}${risk.trigger_reason}`
        .toLowerCase()
        .includes(riskKeyword.trim().toLowerCase());
      const matchesLevel = riskLevel === "all" || String(risk.level) === riskLevel;
      return matchesKeyword && matchesLevel;
    });
  }, [overview.risks, riskKeyword, riskLevel]);

  const riskColumns: TableColumnsType<RiskItem> = [
    {
      title: "风险事项",
      dataIndex: "title",
      sorter: (a, b) => a.title.localeCompare(b.title),
      render: (value: string, record) => (
        <Space orientation="vertical" size={2}>
          <strong>{value}</strong>
          <Text type="secondary">{record.trigger_reason}</Text>
        </Space>
      )
    },
    {
      title: "状态",
      dataIndex: "level_label",
      width: 110,
      filters: [
        { text: "正常", value: "正常" },
        { text: "预警", value: "预警" },
        { text: "危险", value: "危险" }
      ],
      onFilter: (value, record) => record.level_label.includes(String(value)),
      render: (value: string, record) => <Tag color={riskColor(record.level)}>{value}</Tag>
    },
    {
      title: "处理建议",
      dataIndex: "suggested_checks",
      render: (checks: string[]) => checks.slice(0, 2).join(" / ")
    },
    {
      title: "动作",
      width: 120,
      render: () => <Button type="link">查看详情</Button>
    }
  ];

  return (
    <section id="ai-home" className="enterprise-dashboard">
      <Card className="state-brief">
        <div>
          <Text className="eyebrow">5秒财务状态</Text>
          <Title level={3}>企业当前处于“利润稳定、现金流需复核、税务风险预警”的状态</Title>
          <Text type="secondary">
            AI 已结合 {dashboard.period} 指标、风险清单与管理报告《{report.title}》生成经营摘要。
          </Text>
        </div>
        <Space wrap>
          <Button onClick={onOpenDataEntry}>导入数据</Button>
          <Button type="primary" icon={<CheckCircleOutlined />} onClick={onOpenAiAdvisor}>
            AI 分析风险
          </Button>
        </Space>
      </Card>

      <Row gutter={[16, 16]} className="metric-cockpit">
        {cockpitMetrics.map((metric) => (
          <Col xs={24} sm={12} lg={8} xl={4} key={metric.title}>
            <Card className={`metric-tile metric-tile--${metric.status}`}>
              <Space className="metric-tile__header">
                <span className="metric-tile__icon">{metric.icon}</span>
                <Text type="secondary">{metric.title}</Text>
              </Space>
              <Statistic value={metric.value} styles={{ content: { color: metric.status === "danger" ? "#cf1322" : "#102a43" } }} />
              <Text type="secondary">{metric.note}</Text>
            </Card>
          </Col>
        ))}
      </Row>

      <div className="dashboard-grid">
        <Card title="经营趋势" extra={<Tag color="blue">折线图</Tag>} className="dashboard-card dashboard-card--wide">
          <TrendChart series={overview.trend_series} />
        </Card>
        <Card title="成本结构" extra={<Tag color="cyan">环形图</Tag>} className="dashboard-card">
          <ExpensePieChart data={overview.expense_structure} />
        </Card>
        <Card title="现金流柱状图" extra={<Tag color="geekblue">柱状图</Tag>} className="dashboard-card">
          <CashFlowChart series={overview.cash_flow_series} />
        </Card>
        <Card title="风险等级" className="dashboard-card">
          <Progress percent={Math.min(100, overview.risks.length * 22 + 12)} status="exception" />
          <div className="risk-summary-list">
            {overview.risks.slice(0, 3).map((risk) => (
              <div key={risk.id}>
                <Tag color={riskColor(risk.level)}>{risk.level_label}</Tag>
                <span>{risk.title}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card
        title="高级数据表"
        className="advanced-table-card"
        extra={
          <Space wrap>
            <Input
              prefix={<SearchOutlined />}
              value={riskKeyword}
              onChange={(event) => setRiskKeyword(event.target.value)}
              placeholder="搜索风险、原因、建议"
              allowClear
            />
            <Select
              value={riskLevel}
              onChange={setRiskLevel}
              options={[
                { label: "全部状态", value: "all" },
                { label: "正常", value: "1" },
                { label: "预警", value: "2" },
                { label: "危险", value: "3" },
                { label: "高危", value: "4" }
              ]}
              suffixIcon={<FilterOutlined />}
            />
            <Button icon={<CloudDownloadOutlined />}>导出</Button>
          </Space>
        }
      >
        <Table
          rowKey="id"
          columns={riskColumns}
          dataSource={filteredRisks}
          pagination={{ pageSize: 5, showSizeChanger: false }}
          size="middle"
        />
      </Card>
    </section>
  );
}

function findOverviewMetric(metrics: MetricCard[], keyword: string) {
  return metrics.find((metric) => metric.title.includes(keyword));
}

function findHomeMetric(metrics: HomeMetric[], keyword: string) {
  return metrics.find((metric) => metric.title.includes(keyword));
}

function formatLatestSeriesValue(series: TrendChartSeries[], keyword: string) {
  const matched = series.find((item) => item.name.includes(keyword));
  const latest = matched?.data.at(-1)?.value;
  return latest === undefined ? "--" : `¥${Math.round(latest)}万`;
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
