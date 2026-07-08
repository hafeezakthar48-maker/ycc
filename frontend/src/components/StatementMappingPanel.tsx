import {
  Alert,
  Button,
  Card,
  Col,
  Input,
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
  FileSearchOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined
} from "@ant-design/icons";
import { useEffect, useMemo, useState } from "react";
import { fetchDefaultStatementMappingSet } from "../services/dashboardApi";
import type { StatementMappingRule, StatementMappingSetResponse, StatementRuleSource, StatementType } from "../types/statementMapping";

const { Paragraph, Text, Title } = Typography;
const { Search } = Input;

const statementLabels: Record<StatementType, string> = {
  balance_sheet: "资产负债表",
  income_statement: "利润表",
  cash_flow_statement: "现金流量表",
  equity_statement: "所有者权益变动表"
};

const statementTypes = Object.keys(statementLabels) as StatementType[];

const sourceLabels: Record<StatementRuleSource, string> = {
  account_balance: "科目余额",
  account_activity: "期间发生额",
  formula: "公式",
  cash_flow_item: "现金流项目",
  period_close_result: "期末处理"
};

const sourceColors: Record<StatementRuleSource, string> = {
  account_balance: "blue",
  account_activity: "cyan",
  formula: "purple",
  cash_flow_item: "green",
  period_close_result: "orange"
};

function normalSideLabel(value: StatementMappingRule["normal_side"]) {
  if (value === "debit") {
    return "借方";
  }
  if (value === "credit") {
    return "贷方";
  }
  return "无方向";
}

function formatTime(value: string | null | undefined) {
  if (!value) {
    return "-";
  }
  return value.replace("T", " ").replace("Z", "");
}

function sourceText(rule: StatementMappingRule) {
  const accounts = rule.account_prefixes.join(" / ");
  const cashItems = rule.cash_flow_item_codes.join(" / ");
  return accounts || cashItems || "公式或期末处理";
}

function ruleFormula(rule: StatementMappingRule) {
  if (rule.formula) {
    return rule.formula;
  }
  if (rule.source_type === "account_balance") {
    return `${normalSideLabel(rule.normal_side)}余额`;
  }
  if (rule.source_type === "account_activity") {
    return `${normalSideLabel(rule.normal_side)}发生额`;
  }
  return sourceLabels[rule.source_type];
}

export default function StatementMappingPanel() {
  const [payload, setPayload] = useState<StatementMappingSetResponse | null>(null);
  const [activeStatement, setActiveStatement] = useState<StatementType>("balance_sheet");
  const [searchText, setSearchText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function loadMapping() {
    setIsLoading(true);
    setError(null);
    fetchDefaultStatementMappingSet()
      .then(setPayload)
      .catch((mappingError) => {
        setError(mappingError instanceof Error ? mappingError.message : "报表映射读取失败");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    fetchDefaultStatementMappingSet()
      .then((result) => {
        if (!cancelled) {
          setPayload(result);
        }
      })
      .catch((mappingError) => {
        if (!cancelled) {
          setError(mappingError instanceof Error ? mappingError.message : "报表映射读取失败");
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
  }, []);

  const allRules = payload?.rules ?? [];
  const enabledRuleCount = allRules.filter((rule) => rule.enabled).length;
  const sourceSummary = useMemo(
    () => Object.entries(sourceLabels).map(([source, label]) => ({
      source: source as StatementRuleSource,
      label,
      count: allRules.filter((rule) => rule.source_type === source).length
    })),
    [allRules]
  );
  const filteredRules = useMemo(() => {
    const keyword = searchText.trim().toLowerCase();
    if (!keyword) {
      return allRules;
    }
    return allRules.filter((rule) => [
      rule.line_code,
      rule.line_name,
      sourceLabels[rule.source_type],
      sourceText(rule),
      ruleFormula(rule)
    ].some((value) => value.toLowerCase().includes(keyword)));
  }, [allRules, searchText]);

  const activeRules = filteredRules.filter((rule) => rule.statement_type === activeStatement);

  const columns: TableColumnsType<StatementMappingRule> = [
    {
      title: "项目编码",
      dataIndex: "line_code",
      key: "line_code",
      width: 130,
      fixed: "left",
      sorter: (a, b) => a.line_code.localeCompare(b.line_code),
      render: (value) => <Tag color="blue">{value}</Tag>
    },
    {
      title: "项目名称",
      dataIndex: "line_name",
      key: "line_name",
      width: 180,
      sorter: (a, b) => a.display_order - b.display_order,
      render: (value) => <Text strong>{value}</Text>
    },
    {
      title: "来源",
      dataIndex: "source_type",
      key: "source_type",
      width: 140,
      filters: Object.entries(sourceLabels).map(([value, text]) => ({ value, text })),
      onFilter: (value, rule) => rule.source_type === value,
      render: (value: StatementRuleSource) => <Tag color={sourceColors[value]}>{sourceLabels[value]}</Tag>
    },
    {
      title: "科目/项目",
      key: "source",
      width: 240,
      ellipsis: true,
      render: (_, rule) => <Text type="secondary">{sourceText(rule)}</Text>
    },
    {
      title: "规则口径",
      key: "formula",
      width: 240,
      ellipsis: true,
      render: (_, rule) => ruleFormula(rule)
    },
    {
      title: "方向",
      dataIndex: "normal_side",
      key: "normal_side",
      width: 96,
      render: (value: StatementMappingRule["normal_side"]) => normalSideLabel(value)
    },
    {
      title: "符号",
      dataIndex: "sign",
      key: "sign",
      align: "right",
      width: 80,
      render: (value: number) => (value > 0 ? "+1" : "-1")
    },
    {
      title: "状态",
      dataIndex: "enabled",
      key: "enabled",
      width: 110,
      render: (value: boolean) => <Tag color={value ? "green" : "default"}>{value ? "启用" : "停用"}</Tag>
    }
  ];

  return (
    <section id="statement-mapping-panel" className="statement-mapping-panel statement-mapping-workbench">
      <Card className="statement-mapping-hero">
        <div className="statement-mapping-toolbar">
          <div>
            <Text className="eyebrow">报表映射</Text>
            <Title level={3}>报表口径映射工作台</Title>
            <Paragraph type="secondary">
              统一查看四表映射、科目取数口径、公式规则和校验追溯入口，支撑月结报表生成前的口径复核。
            </Paragraph>
          </div>
          <Space wrap>
            <Tag color="blue">{payload?.mapping_set.base_currency ?? "CNY"}</Tag>
            <Button icon={<ReloadOutlined />} loading={isLoading} onClick={loadMapping}>
              重新读取
            </Button>
            <Button icon={<CloudDownloadOutlined />}>
              导出映射
            </Button>
            <Button type="primary" icon={<SafetyCertificateOutlined />} href="#statement-validation-panel">
              查看校验
            </Button>
          </Space>
        </div>
      </Card>

      {error ? <Alert type="warning" showIcon message={error} /> : null}

      <Row gutter={[16, 16]} className="statement-mapping-summary-grid">
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" title="映射集概览" className="statement-mapping-metric">
            <Text strong>{payload?.mapping_set.mapping_set_name ?? "正在读取映射集"}</Text>
            <Text type="secondary">{payload?.mapping_set.mapping_set_id ?? "default"}</Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="statement-mapping-metric">
            <Statistic title="四表映射" value={statementTypes.length} suffix="张" prefix={<FileSearchOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="statement-mapping-metric">
            <Statistic title="启用规则" value={enabledRuleCount} suffix={`/${allRules.length}`} prefix={<CheckCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="statement-mapping-metric">
            <Statistic title="最后更新" value={formatTime(payload?.mapping_set.updated_at)} />
          </Card>
        </Col>
      </Row>

      <div className="statement-mapping-layout">
        <Card className="statement-mapping-card statement-mapping-main" title="四表映射">
          <div className="statement-mapping-filterbar">
            <Search
              allowClear
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              onSearch={setSearchText}
              placeholder="搜索项目编码、项目名称、科目或公式"
            />
            <Text type="secondary">
              当前 {statementLabels[activeStatement]}：{activeRules.length} 条规则
            </Text>
          </div>
          <Tabs
            activeKey={activeStatement}
            onChange={(key) => setActiveStatement(key as StatementType)}
            items={statementTypes.map((type) => {
              const statementRules = filteredRules.filter((rule) => rule.statement_type === type);
              return {
                key: type,
                label: `${statementLabels[type]} (${statementRules.length})`,
                children: (
                  <Table
                    className="statement-mapping-rules-table"
                    rowKey="rule_id"
                    columns={columns}
                    dataSource={statementRules}
                    loading={isLoading}
                    pagination={{ pageSize: 8, showSizeChanger: false }}
                    scroll={{ x: 1120 }}
                    locale={{ emptyText: isLoading ? "正在读取报表映射" : "暂无匹配的映射规则" }}
                  />
                )
              };
            })}
          />
        </Card>

        <Card className="statement-mapping-card" title="规则来源">
          <div className="statement-mapping-source-list">
            {sourceSummary.map((item) => (
              <div key={item.source}>
                <span>
                  <Tag color={sourceColors[item.source]}>{item.label}</Tag>
                </span>
                <strong>{item.count}</strong>
              </div>
            ))}
          </div>
        </Card>

        <Card className="statement-mapping-card statement-mapping-trace-card" title="校验追溯入口">
          <Space orientation="vertical" size={10}>
            <Text type="secondary">
              报表生成后可在取数追溯中核对映射规则、来源科目、现金流项目和最终金额。
            </Text>
            <Button icon={<SafetyCertificateOutlined />} href="#statement-validation-panel">
              前往取数追溯
            </Button>
          </Space>
        </Card>
      </div>
    </section>
  );
}
