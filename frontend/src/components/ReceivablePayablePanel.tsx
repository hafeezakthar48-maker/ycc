import {
  Alert,
  Button,
  Card,
  Col,
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
  ReloadOutlined,
  SafetyCertificateOutlined,
  WalletOutlined
} from "@ant-design/icons";
import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchCounterpartyAging, fetchCounterpartyBalances } from "../services/dashboardApi";
import type {
  AgingBucket,
  CounterpartyAgingResponse,
  CounterpartyBalanceItem,
  CounterpartyBalanceResponse,
  OpenItemType
} from "../types/receivablePayable";

const { Paragraph, Text, Title } = Typography;

interface ReceivablePayablePanelProps {
  period: string;
}

const openItemOptions = [
  { label: "应收", value: "receivable" },
  { label: "应付", value: "payable" }
];

function money(value: string | number) {
  const amount = Number(value);
  if (Number.isNaN(amount)) {
    return String(value);
  }
  return `¥${amount.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function periodEndDate(period: string) {
  const [yearText, monthText] = period.split("-");
  const year = Number(yearText);
  const month = Number(monthText);
  const endDate = new Date(year, month, 0);
  return `${endDate.getFullYear()}-${String(endDate.getMonth() + 1).padStart(2, "0")}-${String(endDate.getDate()).padStart(2, "0")}`;
}

function typeLabel(openItemType: OpenItemType) {
  return openItemType === "receivable" ? "应收" : "应付";
}

function counterpartyTypeLabel(type: CounterpartyBalanceItem["counterparty_type"]) {
  return type === "customer" ? "客户" : "供应商";
}

function agingRangeLabel(bucket: AgingBucket) {
  if (bucket.day_to == null) {
    return `${bucket.day_from} 天以上`;
  }
  return `${bucket.day_from}-${bucket.day_to} 天`;
}

export default function ReceivablePayablePanel({ period }: ReceivablePayablePanelProps) {
  const [openItemType, setOpenItemType] = useState<OpenItemType>("receivable");
  const [balances, setBalances] = useState<CounterpartyBalanceResponse | null>(null);
  const [aging, setAging] = useState<CounterpartyAgingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const asOfDate = useMemo(() => periodEndDate(period), [period]);

  const loadReceivablePayable = useCallback(
    async (shouldApply: () => boolean = () => true) => {
      setError(null);
      setIsLoading(true);
      try {
        const [balancePayload, agingPayload] = await Promise.all([
          fetchCounterpartyBalances("default", period, openItemType),
          fetchCounterpartyAging("default", period, openItemType, asOfDate)
        ]);
        if (!shouldApply()) {
          return;
        }
        setBalances(balancePayload);
        setAging(agingPayload);
      } catch (rpError) {
        if (shouldApply()) {
          setError(rpError instanceof Error ? rpError.message : "往来核算读取失败");
        }
      } finally {
        if (shouldApply()) {
          setIsLoading(false);
        }
      }
    },
    [asOfDate, openItemType, period]
  );

  useEffect(() => {
    let active = true;
    void loadReceivablePayable(() => active);
    return () => {
      active = false;
    };
  }, [loadReceivablePayable]);

  const balanceItems = useMemo(
    () => [...(balances?.items ?? [])].sort((left, right) => Number(right.base_balance) - Number(left.base_balance)),
    [balances]
  );

  const agingBuckets = useMemo(() => aging?.buckets ?? [], [aging]);

  const overdueAmount = useMemo(
    () => agingBuckets
      .filter((bucket) => bucket.day_from > 30)
      .reduce((total, bucket) => total + Number(bucket.amount || 0), 0),
    [agingBuckets]
  );

  const balanceColumns: TableColumnsType<CounterpartyBalanceItem> = [
    {
      title: "往来对象",
      dataIndex: "counterparty_name",
      key: "counterparty_name",
      fixed: "left",
      width: 220,
      render: (_, item) => (
        <Space orientation="vertical" size={0}>
          <Text strong>{item.counterparty_name}</Text>
          <Text type="secondary">{counterpartyTypeLabel(item.counterparty_type)} · {item.counterparty_code}</Text>
        </Space>
      )
    },
    {
      title: "类型",
      dataIndex: "open_item_type",
      key: "open_item_type",
      width: 96,
      render: (value: OpenItemType) => (
        <Tag color={value === "receivable" ? "blue" : "purple"}>{typeLabel(value)}</Tag>
      )
    },
    {
      title: "币种",
      dataIndex: "currency",
      key: "currency",
      width: 90
    },
    {
      title: "原币余额",
      dataIndex: "original_balance",
      key: "original_balance",
      align: "right",
      width: 150,
      render: (value: string | number) => money(value)
    },
    {
      title: "本位币余额",
      dataIndex: "base_balance",
      key: "base_balance",
      align: "right",
      width: 160,
      render: (value: string | number) => <Text strong>{money(value)}</Text>
    },
    {
      title: "未清项",
      dataIndex: "open_item_count",
      key: "open_item_count",
      align: "right",
      width: 120
    }
  ];

  const agingColumns: TableColumnsType<AgingBucket> = [
    {
      title: "账龄",
      dataIndex: "bucket_code",
      key: "bucket_code",
      fixed: "left",
      width: 150,
      render: (_, bucket) => (
        <Space orientation="vertical" size={0}>
          <Text strong>{bucket.bucket_code}</Text>
          <Text type="secondary">{agingRangeLabel(bucket)}</Text>
        </Space>
      )
    },
    {
      title: "金额",
      dataIndex: "amount",
      key: "amount",
      align: "right",
      width: 150,
      render: (value: string | number) => money(value)
    },
    {
      title: "未清项",
      dataIndex: "open_item_count",
      key: "open_item_count",
      align: "right",
      width: 110
    }
  ];

  return (
    <section id="receivable-payable-panel" className="receivable-payable-panel receivable-payable-workbench">
      <Card className="receivable-payable-hero">
        <div className="receivable-payable-toolbar">
          <div>
            <Text className="eyebrow">往来核算</Text>
            <Title level={3}>往来核算工作台</Title>
            <Paragraph type="secondary">
              将应收应付余额台账、账龄分析、未清项数量和逾期金额集中到同一视图，支撑回款跟进、付款排程和坏账准备复核。
            </Paragraph>
          </div>
          <Space wrap>
            <Tag color="blue">{period}</Tag>
            <Segmented
              value={openItemType}
              options={openItemOptions}
              onChange={(value) => setOpenItemType(value as OpenItemType)}
            />
            <Button icon={<ReloadOutlined />} loading={isLoading} onClick={() => void loadReceivablePayable()}>
              刷新
            </Button>
          </Space>
        </div>
      </Card>

      {error ? <Alert type="warning" showIcon message={error} /> : null}

      <Row gutter={[16, 16]} className="receivable-payable-summary-grid">
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="receivable-payable-metric">
            <Statistic title={`${typeLabel(openItemType)}余额`} value={money(balances?.total_base_balance ?? 0)} prefix={<WalletOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="receivable-payable-metric">
            <Statistic title="往来对象" value={balances?.item_count ?? 0} suffix="个" />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="receivable-payable-metric">
            <Statistic title="逾期金额" value={money(overdueAmount)} prefix={<SafetyCertificateOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="receivable-payable-metric">
            <Statistic title="截止日" value={isLoading ? "读取中" : asOfDate} />
          </Card>
        </Col>
      </Row>

      <div className="receivable-payable-layout">
        <Card
          className="receivable-payable-card receivable-payable-main"
          title="余额台账"
          extra={<Tag color={openItemType === "receivable" ? "blue" : "purple"}>{typeLabel(openItemType)}</Tag>}
        >
          <Table
            className="receivable-payable-ledger-table"
            rowKey={(item) => `${item.counterparty_type}-${item.counterparty_code}-${item.currency}`}
            columns={balanceColumns}
            dataSource={balanceItems}
            loading={isLoading}
            pagination={{ pageSize: 6, showSizeChanger: false }}
            scroll={{ x: 920 }}
            locale={{ emptyText: `当前期间暂无${typeLabel(openItemType)}未清项` }}
          />
        </Card>

        <Card className="receivable-payable-card" title="账龄分析">
          <Table
            className="receivable-payable-ledger-table receivable-payable-aging-table"
            rowKey="bucket_code"
            columns={agingColumns}
            dataSource={agingBuckets}
            loading={isLoading}
            pagination={false}
            scroll={{ x: 540 }}
            locale={{ emptyText: "暂无账龄分析" }}
          />
        </Card>

        <Card className="receivable-payable-card" title="核销提示">
          <div className="receivable-payable-insight-list">
            <article>
              <Tag color="blue">{typeLabel(openItemType)}</Tag>
              <Text>{balanceItems.length ? `重点跟进 ${balanceItems[0].counterparty_name}` : "暂无需要跟进的往来对象"}</Text>
            </article>
            <article>
              <Tag color={overdueAmount > 0 ? "orange" : "green"}>账龄</Tag>
              <Text>{overdueAmount > 0 ? `31 天以上余额 ${money(overdueAmount)}` : "暂无 31 天以上逾期余额"}</Text>
            </article>
            <article>
              <Tag>期间</Tag>
              <Text>以 {asOfDate} 作为账龄截止日，当前视图用于月结前复核。</Text>
            </article>
          </div>
        </Card>
      </div>
    </section>
  );
}
