import {
  Alert,
  Button,
  Card,
  Col,
  Progress,
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
  CloudDownloadOutlined,
  FileProtectOutlined,
  LockOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined
} from "@ant-design/icons";
import { useEffect, useMemo, useState } from "react";
import { generateFinancialStatements } from "../services/dashboardApi";
import type {
  FinancialStatementBundle,
  MoneyValue,
  StatementLineItem,
  StatementLineTrace,
  StatementValidationItem
} from "../types/financialStatement";

const { Paragraph, Text, Title } = Typography;

interface FinancialStatementPanelProps {
  period: string;
}

interface StatementTableProps {
  title: string;
  period: string;
  items: StatementLineItem[];
  totals: Array<{ label: string; value: MoneyValue }>;
}

function money(value: MoneyValue) {
  return Number(value).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function sourceLabel(source: string) {
  if (source === "formal_journal_entries") {
    return "正式分录";
  }
  return source === "reviewed_vouchers" ? "已审核凭证" : "样例经营数据";
}

function validationLabel(status: string) {
  if (status === "passed") {
    return "通过";
  }
  return status === "failed" ? "未通过" : "提示";
}

function validationColor(status: string) {
  if (status === "passed") {
    return "green";
  }
  return status === "failed" ? "red" : "orange";
}

export default function FinancialStatementPanel({ period }: FinancialStatementPanelProps) {
  const [bundle, setBundle] = useState<FinancialStatementBundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const statementTables = useMemo(() => {
    if (!bundle) {
      return [
        { title: "资产负债表", period, items: [], totals: [] },
        { title: "利润表", period, items: [], totals: [] },
        { title: "现金流量表", period, items: [], totals: [] },
        { title: "所有者权益变动表", period, items: [], totals: [] }
      ];
    }
    return [
      {
        title: bundle.balance_sheet.title,
        period: bundle.balance_sheet.period,
        items: bundle.balance_sheet.items,
        totals: [
          { label: "资产合计", value: bundle.balance_sheet.total_assets },
          { label: "负债合计", value: bundle.balance_sheet.total_liabilities },
          { label: "所有者权益", value: bundle.balance_sheet.total_equity },
          { label: "负债和权益合计", value: bundle.balance_sheet.total_liabilities_and_equity }
        ]
      },
      {
        title: bundle.income_statement.title,
        period: bundle.income_statement.period,
        items: bundle.income_statement.items,
        totals: [
          { label: "营业收入", value: bundle.income_statement.total_revenue },
          { label: "营业成本", value: bundle.income_statement.total_cost },
          { label: "期间费用", value: bundle.income_statement.total_expense },
          { label: "净利润", value: bundle.income_statement.net_profit }
        ]
      },
      {
        title: bundle.cash_flow_statement.title,
        period: bundle.cash_flow_statement.period,
        items: bundle.cash_flow_statement.items,
        totals: [
          { label: "经营现金流", value: bundle.cash_flow_statement.operating_cash_flow_net },
          { label: "投资现金流", value: bundle.cash_flow_statement.investing_cash_flow_net },
          { label: "筹资现金流", value: bundle.cash_flow_statement.financing_cash_flow_net },
          { label: "现金净增加额", value: bundle.cash_flow_statement.net_cash_flow }
        ]
      },
      {
        title: bundle.equity_statement.title,
        period: bundle.equity_statement.period,
        items: bundle.equity_statement.items,
        totals: [
          { label: "期初权益", value: bundle.equity_statement.opening_equity },
          { label: "本期净利润", value: bundle.equity_statement.current_period_profit },
          { label: "期末权益", value: bundle.equity_statement.closing_equity }
        ]
      }
    ];
  }, [bundle, period]);

  const validationItems = bundle?.validation_items ?? [];
  const traceItems = bundle?.trace_items ?? [];
  const passedValidationCount = validationItems.filter((item) => item.status === "passed").length;
  const validationProgress = validationItems.length
    ? Math.round(passedValidationCount / validationItems.length * 100)
    : 0;

  const traceColumns: TableColumnsType<StatementLineTrace> = [
    {
      title: "报表项目",
      dataIndex: "line_code",
      key: "line_code",
      width: 120,
      render: (value) => <Tag color="blue">{value}</Tag>
    },
    {
      title: "取数规则",
      dataIndex: "formula",
      key: "formula",
      width: 220,
      ellipsis: true
    },
    {
      title: "数据来源",
      dataIndex: "source_type",
      key: "source_type",
      width: 140,
      render: (value) => sourceLabel(value)
    },
    {
      title: "来源科目/现金流项目",
      key: "source",
      width: 260,
      render: (_, item) => (
        item.source_account_codes.join(" / ") || item.cash_flow_item_codes.join(" / ") || "公式或样例数据"
      )
    },
    {
      title: "金额",
      dataIndex: "amount",
      key: "amount",
      align: "right",
      width: 140,
      render: (value) => money(value)
    }
  ];

  const validationColumns: TableColumnsType<StatementValidationItem> = [
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 110,
      render: (value) => <Tag color={validationColor(value)}>{validationLabel(value)}</Tag>
    },
    {
      title: "校验项",
      dataIndex: "validation_name",
      key: "validation_name",
      width: 180
    },
    {
      title: "结果说明",
      dataIndex: "message",
      key: "message",
      ellipsis: true
    }
  ];

  function loadStatements() {
    setIsLoading(true);
    setError(null);
    generateFinancialStatements({ period, account_set_id: "default", operator: "财务主管", include_trace: true })
      .then(setBundle)
      .catch((statementError) => {
        setError(statementError instanceof Error ? statementError.message : "财务报表生成失败");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    generateFinancialStatements({ period, account_set_id: "default", operator: "财务主管", include_trace: true })
      .then((payload) => {
        if (!cancelled) {
          setBundle(payload);
        }
      })
      .catch((statementError) => {
        if (!cancelled) {
          setError(statementError instanceof Error ? statementError.message : "财务报表生成失败");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [period]);

  return (
    <section id="financial-statements-panel" className="financial-statements-panel statement-delivery-workbench">
      <Card className="statement-delivery-hero">
        <div className="statement-delivery-toolbar">
          <div>
            <Text className="eyebrow">财务报表</Text>
            <Title level={3}>报表交付工作台</Title>
            <Paragraph type="secondary">
              将四表生成、平衡校验、取数追溯、管理层摘要和归档动作集中在一个月结交付界面。
            </Paragraph>
          </div>
          <Space wrap>
            <Tag color="blue">{period}</Tag>
            <Button icon={<ReloadOutlined />} loading={isLoading} onClick={loadStatements}>
              重新生成
            </Button>
            <Button icon={<CloudDownloadOutlined />} href="#statement-archive-panel">
              导出报表包
            </Button>
            <Button type="primary" icon={<LockOutlined />} href="#statement-archive-panel">
              归档锁定
            </Button>
          </Space>
        </div>
      </Card>

      {error ? <Alert type="warning" showIcon message={error} /> : null}

      <Row gutter={[16, 16]} className="financial-statement-summary-grid">
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="statement-delivery-metric">
            <Statistic title="报表来源" value={bundle ? sourceLabel(bundle.source) : "读取中"} prefix={<FileProtectOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="statement-delivery-metric">
            <Statistic title="平衡校验" value={bundle?.summary.asset_liability_balanced ? "已平衡" : "待复核"} prefix={<SafetyCertificateOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="statement-delivery-metric">
            <Statistic title="已审核凭证" value={bundle?.summary.reviewed_voucher_count ?? 0} suffix="张" />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="statement-delivery-metric">
            <Statistic title="生成报表" value={bundle?.summary.generated_statement_count ?? 0} suffix="张" />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="statement-delivery-metric">
            <Statistic title="本位币" value={bundle?.summary.base_currency ?? "CNY"} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="statement-delivery-metric">
            <Statistic title="外币分录" value={bundle?.summary.foreign_currency_line_count ?? 0} suffix="条" />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="statement-delivery-metric">
            <Statistic title="映射集" value={bundle?.mapping_set_id ?? "读取中"} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="statement-delivery-metric">
            <Statistic title="校验通过率" value={validationProgress} suffix="%" prefix={<CheckCircleOutlined />} />
          </Card>
        </Col>
      </Row>

      <div className="statement-delivery-layout">
        <Card className="statement-delivery-card statement-preview-card" title="四表预览">
          <Tabs
            className="statement-preview-tabs"
            items={statementTables.map((statement) => ({
              key: statement.title,
              label: statement.title,
              children: <StatementTable {...statement} />
            }))}
          />
        </Card>

        <Card className="statement-delivery-card" title="生成队列">
          <div className="statement-flow-list">
            <p><Tag color="green">已完成</Tag> 取数口径映射</p>
            <p><Tag color={bundle?.summary.asset_liability_balanced ? "green" : "orange"}>校验</Tag> 资产负债平衡复核</p>
            <p><Tag color={traceItems.length ? "blue" : "default"}>追溯</Tag> 生成 {traceItems.length} 条报表项目来源</p>
            <p><Tag color="purple">待办</Tag> 导出报表包并归档锁定</p>
          </div>
        </Card>

        <Card className="statement-delivery-card" title="平衡校验">
          <Progress
            percent={validationProgress}
            status={validationItems.some((item) => item.status === "failed") ? "exception" : "success"}
          />
          <Table
            rowKey="validation_code"
            columns={validationColumns}
            dataSource={validationItems}
            pagination={false}
            size="small"
            scroll={{ x: 620 }}
            locale={{ emptyText: isLoading ? "正在生成校验结果" : "暂无校验结果" }}
          />
        </Card>

        <Card className="statement-delivery-card statement-management-panel" title="管理层摘要">
          <Title level={5}>{bundle?.management_summary.title ?? "管理报表摘要"}</Title>
          <div className="statement-kpi-list">
            {Object.entries(bundle?.management_summary.key_metrics ?? {}).map(([label, value]) => (
              <Tag key={label}>{label} {value}</Tag>
            ))}
          </div>
          <div className="statement-summary-list">
            {(bundle?.management_summary.highlights ?? ["正在生成管理摘要"]).map((item) => (
              <p key={item}>{item}</p>
            ))}
          </div>
          <div className="statement-risk-list">
            {(bundle?.management_summary.risks ?? []).map((item) => (
              <p key={item}>{item}</p>
            ))}
          </div>
        </Card>

        <Card
          id="statement-validation-panel"
          className="statement-delivery-card statement-validation-panel"
          title="取数追溯"
        >
          <Table
            className="statement-trace-table"
            rowKey={(item) => `${item.rule_id}-${item.line_code}`}
            columns={traceColumns}
            dataSource={traceItems.slice(0, 20)}
            pagination={{ pageSize: 6, showSizeChanger: false }}
            scroll={{ x: 860 }}
            locale={{ emptyText: isLoading ? "正在生成取数追溯" : "暂无追溯数据" }}
          />
        </Card>
      </div>
    </section>
  );
}

function StatementTable({ period, items, totals }: StatementTableProps) {
  const columns: TableColumnsType<StatementLineItem> = [
    {
      title: "项目",
      dataIndex: "name",
      key: "name",
      width: 220,
      fixed: "left",
      render: (value, item) => (
        <Space orientation="vertical" size={0}>
          <Text strong>{value}</Text>
          <Text type="secondary">{item.code}</Text>
        </Space>
      )
    },
    {
      title: "金额",
      dataIndex: "amount",
      key: "amount",
      align: "right",
      width: 160,
      render: (value) => money(value)
    },
    {
      title: "取数口径",
      dataIndex: "formula",
      key: "formula",
      ellipsis: true,
      render: (value) => <Text type="secondary">{value}</Text>
    }
  ];

  return (
    <div className="statement-table-panel">
      <Text type="secondary">{period}</Text>
      <Table
        className="statement-table"
        rowKey="code"
        columns={columns}
        dataSource={items}
        pagination={{ pageSize: 6, showSizeChanger: false }}
        scroll={{ x: 760 }}
        locale={{ emptyText: "暂无报表项目" }}
        summary={() => (
          totals.length ? (
            <Table.Summary fixed>
              {totals.map((total) => (
                <Table.Summary.Row key={total.label}>
                  <Table.Summary.Cell index={0}>{total.label}</Table.Summary.Cell>
                  <Table.Summary.Cell index={1}>{money(total.value)}</Table.Summary.Cell>
                  <Table.Summary.Cell index={2}>自动汇总</Table.Summary.Cell>
                </Table.Summary.Row>
              ))}
            </Table.Summary>
          ) : null
        )}
      />
    </div>
  );
}
