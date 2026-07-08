import {
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  Input,
  Row,
  Segmented,
  Space,
  Statistic,
  Table,
  Tag,
  Typography
} from "antd";
import type { TableColumnsType } from "antd";
import {
  CheckCircleOutlined,
  FileDoneOutlined,
  LockOutlined,
  ReloadOutlined,
  UnlockOutlined
} from "@ant-design/icons";
import { useEffect, useMemo, useState } from "react";
import {
  closePeriod,
  generatePeriodCloseActions,
  reopenPeriod,
  runPeriodCloseChecks
} from "../services/dashboardApi";
import type {
  PeriodCloseActionResult,
  PeriodCloseActionType,
  PeriodCloseCheckItem,
  PeriodCloseType
} from "../types/periodClose";

const { Paragraph, Text, Title } = Typography;

interface PeriodClosePanelProps {
  period: string;
}

const closeActions: Array<{ type: PeriodCloseActionType; label: string; group: string }> = [
  { type: "fixed_asset_depreciation", label: "固定资产折旧", group: "资产" },
  { type: "payroll_accrual", label: "工资计提", group: "薪酬" },
  { type: "tax_accrual", label: "税费计提", group: "税务" },
  { type: "tax_surtax_accrual", label: "附加税计提", group: "税务" },
  { type: "accrual_amortization_posting", label: "预提摊销", group: "费用" },
  { type: "fx_revaluation", label: "外币重估", group: "汇兑" },
  { type: "inventory_cost_rollforward", label: "存货成本结转", group: "成本" },
  { type: "profit_loss_carryforward", label: "损益结转", group: "结转" },
  { type: "bad_debt_provision", label: "坏账准备", group: "往来" },
  { type: "year_end_profit_distribution", label: "年终利润分配", group: "年结" }
];

const defaultActions: PeriodCloseActionType[] = [
  "fixed_asset_depreciation",
  "payroll_accrual",
  "tax_accrual",
  "tax_surtax_accrual",
  "accrual_amortization_posting",
  "fx_revaluation",
  "inventory_cost_rollforward",
  "profit_loss_carryforward",
  "bad_debt_provision"
];

const checkStatusLabels: Record<PeriodCloseCheckItem["status"], string> = {
  passed: "通过",
  warning: "提醒",
  failed: "阻断"
};

const checkStatusColors: Record<PeriodCloseCheckItem["status"], string> = {
  passed: "green",
  warning: "orange",
  failed: "red"
};

const resultStatusLabels: Record<PeriodCloseActionResult["status"], string> = {
  skipped: "跳过",
  generated: "已生成",
  existing: "已存在",
  failed: "失败"
};

const resultStatusColors: Record<PeriodCloseActionResult["status"], string> = {
  skipped: "default",
  generated: "green",
  existing: "blue",
  failed: "red"
};

function money(value: string | number) {
  const amount = Number(value);
  if (Number.isNaN(amount)) {
    return String(value);
  }
  return `¥${amount.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function actionLabel(actionType: PeriodCloseActionType) {
  return closeActions.find((item) => item.type === actionType)?.label ?? actionType;
}

function actionGroup(actionType: PeriodCloseActionType) {
  return closeActions.find((item) => item.type === actionType)?.group ?? "其他";
}

export default function PeriodClosePanel({ period }: PeriodClosePanelProps) {
  const [selectedPeriod, setSelectedPeriod] = useState(period);
  const [closeType, setCloseType] = useState<PeriodCloseType>("month");
  const [selectedActions, setSelectedActions] = useState<PeriodCloseActionType[]>(defaultActions);
  const [checks, setChecks] = useState<PeriodCloseCheckItem[]>([]);
  const [results, setResults] = useState<PeriodCloseActionResult[]>([]);
  const [periodStatus, setPeriodStatus] = useState<"open" | "closed">("open");
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  const blockerCount = useMemo(
    () => checks.filter((item) => item.status === "failed" && item.severity === "blocker").length,
    [checks]
  );

  const warningCount = useMemo(
    () => checks.filter((item) => item.status === "warning").length,
    [checks]
  );

  const generatedCount = useMemo(
    () => results.filter((item) => item.status === "generated" || item.status === "existing").length,
    [results]
  );

  const failedResultCount = useMemo(
    () => results.filter((item) => item.status === "failed").length,
    [results]
  );

  useEffect(() => {
    setSelectedPeriod(period);
  }, [period]);

  useEffect(() => {
    setSelectedActions((current) => {
      if (closeType === "year" && !current.includes("year_end_profit_distribution")) {
        return [...current, "year_end_profit_distribution"];
      }
      if (closeType === "month" && current.includes("year_end_profit_distribution")) {
        return current.filter((action) => action !== "year_end_profit_distribution");
      }
      return current;
    });
  }, [closeType]);

  function handleActionSelection(values: Array<string | number | boolean>) {
    setSelectedActions(values.map(String) as PeriodCloseActionType[]);
  }

  function handleChecks() {
    setIsBusy(true);
    setError(null);
    runPeriodCloseChecks({ account_set_id: "default", period: selectedPeriod })
      .then((payload) => setChecks(payload.items))
      .catch((checkError) => setError(checkError instanceof Error ? checkError.message : "结账检查失败"))
      .finally(() => setIsBusy(false));
  }

  function handleGenerate() {
    setIsBusy(true);
    setError(null);
    generatePeriodCloseActions({
      account_set_id: "default",
      period: selectedPeriod,
      actions: selectedActions,
      generated_by: "finance-user"
    })
      .then((payload) => setResults(payload.results))
      .catch((generateError) => setError(generateError instanceof Error ? generateError.message : "期末分录生成失败"))
      .finally(() => setIsBusy(false));
  }

  function handleClose() {
    setIsBusy(true);
    setError(null);
    closePeriod({ account_set_id: "default", period: selectedPeriod, operator: "finance-user" })
      .then((payload) => setPeriodStatus(payload.status === "closed" ? "closed" : "open"))
      .catch((closeError) => setError(closeError instanceof Error ? closeError.message : "期间关闭失败"))
      .finally(() => setIsBusy(false));
  }

  function handleReopen() {
    setIsBusy(true);
    setError(null);
    reopenPeriod({ account_set_id: "default", period: selectedPeriod, operator: "finance-user" })
      .then((payload) => setPeriodStatus(payload.status === "closed" ? "closed" : "open"))
      .catch((reopenError) => setError(reopenError instanceof Error ? reopenError.message : "期间重开失败"))
      .finally(() => setIsBusy(false));
  }

  const resultColumns: TableColumnsType<PeriodCloseActionResult> = [
    {
      title: "结账动作",
      dataIndex: "action_type",
      key: "action_type",
      fixed: "left",
      width: 190,
      render: (value: PeriodCloseActionType) => (
        <Space orientation="vertical" size={0}>
          <Text strong>{actionLabel(value)}</Text>
          <Text type="secondary">{actionGroup(value)}</Text>
        </Space>
      )
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 120,
      filters: Object.entries(resultStatusLabels).map(([value, text]) => ({ value, text })),
      onFilter: (value, result) => result.status === value,
      render: (value: PeriodCloseActionResult["status"]) => (
        <Tag color={resultStatusColors[value]}>{resultStatusLabels[value]}</Tag>
      )
    },
    {
      title: "金额",
      dataIndex: "amount",
      key: "amount",
      align: "right",
      width: 140,
      render: (value: string | number) => money(value)
    },
    {
      title: "正式分录",
      dataIndex: "journal_entry_ids",
      key: "journal_entry_ids",
      width: 230,
      render: (value: string[]) => value.length ? value.join(", ") : "-"
    },
    {
      title: "处理说明",
      dataIndex: "message",
      key: "message",
      width: 280
    }
  ];

  return (
    <section id="period-close-panel" className="period-close-panel period-close-workbench">
      <Card className="period-close-hero">
        <div className="period-close-hero-toolbar">
          <div>
            <Text className="eyebrow">期间结账</Text>
            <Title level={3}>期间结账工作台</Title>
            <Paragraph type="secondary">
              将结账控制、检查清单、结账动作、生成结果、关闭期间和重开期间放到同一张结账看板，便于月结与年结留痕。
            </Paragraph>
          </div>
          <Space wrap>
            <Tag color="blue">{selectedPeriod}</Tag>
            <Tag color={periodStatus === "closed" ? "green" : "orange"}>
              {periodStatus === "closed" ? "已关闭" : "打开"}
            </Tag>
            <Button icon={<ReloadOutlined />} loading={isBusy} onClick={handleChecks}>
              执行检查
            </Button>
            <Button type="primary" icon={<FileDoneOutlined />} loading={isBusy} disabled={selectedActions.length === 0} onClick={handleGenerate}>
              生成期末分录
            </Button>
          </Space>
        </div>
      </Card>

      {error ? <Alert type="warning" showIcon title={error} /> : null}

      <Card className="period-close-card" title="结账控制">
        <div className="period-close-toolbar period-close-controlbar">
          <label>
            <span>期间</span>
            <Input value={selectedPeriod} onChange={(event) => setSelectedPeriod(event.target.value)} />
          </label>
          <label>
            <span>类型</span>
            <Segmented
              block
              value={closeType}
              options={[
                { label: "月结", value: "month" },
                { label: "年结", value: "year" }
              ]}
              onChange={(value) => setCloseType(value as PeriodCloseType)}
            />
          </label>
          <Space wrap>
            <Button icon={<CheckCircleOutlined />} onClick={handleChecks} loading={isBusy}>
              执行检查
            </Button>
            <Button type="primary" icon={<LockOutlined />} onClick={handleClose} loading={isBusy} disabled={blockerCount > 0 || periodStatus === "closed"}>
              关闭期间
            </Button>
            <Button icon={<UnlockOutlined />} onClick={handleReopen} loading={isBusy} disabled={periodStatus !== "closed"}>
              重开期间
            </Button>
          </Space>
        </div>
      </Card>

      <Row gutter={[16, 16]} className="period-close-summary-grid">
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="period-close-metric">
            <Statistic title="阻断项" value={blockerCount} prefix={<LockOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="period-close-metric">
            <Statistic title="检查清单" value={checks.length} suffix={`项 / ${warningCount} 提醒`} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="period-close-metric">
            <Statistic title="生成结果" value={generatedCount} suffix={`/${results.length || 0}`} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="period-close-metric">
            <Statistic title="失败动作" value={failedResultCount} />
          </Card>
        </Col>
      </Row>

      <div className="period-close-layout">
        <Card className="period-close-card period-close-main" title="生成结果">
          <Table
            className="period-close-result-table"
            rowKey="action_type"
            columns={resultColumns}
            dataSource={results}
            loading={isBusy}
            pagination={{ pageSize: 6, showSizeChanger: false }}
            scroll={{ x: 960 }}
            locale={{ emptyText: "暂无生成结果" }}
          />
        </Card>

        <Card className="period-close-card" title="结账动作">
          <Checkbox.Group value={selectedActions} onChange={handleActionSelection} className="period-close-action-grid">
            {closeActions.map((action) => (
              <Checkbox
                key={action.type}
                value={action.type}
                disabled={closeType === "month" && action.type === "year_end_profit_distribution"}
              >
                <Space size={6} wrap>
                  <span>{action.label}</span>
                  <Tag>{action.group}</Tag>
                </Space>
              </Checkbox>
            ))}
          </Checkbox.Group>
        </Card>

        <Card className="period-close-card period-close-check-card" title="检查清单">
          <div className="period-close-check-grid">
            {checks.length ? checks.map((item) => (
              <article className={`period-close-check period-close-check--${item.status}`} key={item.check_code}>
                <Tag color={checkStatusColors[item.status]}>{checkStatusLabels[item.status]}</Tag>
                <strong>{item.check_name}</strong>
                <Text type="secondary">{item.message}</Text>
              </article>
            )) : (
              <Text type="secondary">暂无检查结果</Text>
            )}
          </div>
        </Card>
      </div>
    </section>
  );
}
