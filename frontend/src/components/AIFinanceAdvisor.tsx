import { BulbOutlined, CheckCircleOutlined, FileTextOutlined, SendOutlined, WarningOutlined } from "@ant-design/icons";
import { Button, Card, Input, Space, Tag, Timeline, Typography } from "antd";
import { useState } from "react";
import { askFinanceQuestion } from "../services/dashboardApi";
import type { FinanceQuestionResponse } from "../types/financeQa";

const { Text, Title, Paragraph } = Typography;
const { TextArea } = Input;

interface AdvisorMessage {
  role: "user" | "assistant";
  content: string;
  result?: FinanceQuestionResponse;
}

interface AIFinanceAdvisorProps {
  compact?: boolean;
}

const historyItems = [
  "分析今年税务风险",
  "检查现金流和利润背离",
  "生成本月财务复核清单",
  "解释发票异常原因"
];

const defaultQuestion = "分析今年税务风险";

export default function AIFinanceAdvisor({ compact = false }: AIFinanceAdvisorProps) {
  const [question, setQuestion] = useState(defaultQuestion);
  const [isBusy, setIsBusy] = useState(false);
  const [messages, setMessages] = useState<AdvisorMessage[]>([
    { role: "user", content: defaultQuestion },
    {
      role: "assistant",
      content: "已根据税负率、发票结构、费用波动和政策依据生成税务风险初步判断。"
    }
  ]);

  async function submitQuestion(nextQuestion = question) {
    const trimmed = nextQuestion.trim();
    if (!trimmed) {
      return;
    }
    setIsBusy(true);
    setMessages((current) => [...current, { role: "user", content: trimmed }]);
    try {
      const result = await askFinanceQuestion(trimmed);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: result.answer,
          result
        }
      ]);
    } catch {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: "AI 财务顾问暂时无法连接后端服务，已保留问题，可稍后重试。"
        }
      ]);
    } finally {
      setQuestion(trimmed);
      setIsBusy(false);
    }
  }

  return (
    <section className={compact ? "ai-advisor ai-advisor--compact" : "ai-advisor"}>
      <aside className="ai-advisor__history">
        <Text className="eyebrow">历史对话</Text>
        <div className="advisor-history-list" role="list">
          {historyItems.map((item) => (
            <Button key={item} type="text" block onClick={() => submitQuestion(item)}>
              {item}
            </Button>
          ))}
        </div>
      </aside>

      <div className="ai-advisor__chat">
        <div className="ai-advisor__header">
          <div>
            <Text className="eyebrow">AI 财务顾问</Text>
            <Title level={4}>像 ChatGPT 一样提问，按财务卡片交付结论</Title>
          </div>
          <Tag color="blue">企业版</Tag>
        </div>

        <div className="ai-advisor__messages">
          {messages.map((message, index) => (
            <div className={`ai-message ai-message--${message.role}`} key={`${message.role}-${index}`}>
              <Paragraph>{message.content}</Paragraph>
              {message.role === "assistant" ? <AdvisorResultCards result={message.result} /> : null}
            </div>
          ))}
        </div>

        <Space.Compact className="ai-advisor__composer">
          <TextArea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            autoSize={{ minRows: 2, maxRows: 4 }}
            placeholder="例如：分析今年税务风险"
          />
          <Button type="primary" icon={<SendOutlined />} loading={isBusy} onClick={() => submitQuestion()}>
            发送
          </Button>
        </Space.Compact>
      </div>
    </section>
  );
}

function AdvisorResultCards({ result }: { result?: FinanceQuestionResponse }) {
  const actionItems = result?.action_items.length ? result.action_items : [
    "复核本期销项税额与收入确认口径。",
    "核对异常费用发票和供应商抬头。",
    "形成税务风险处理任务并指定负责人。"
  ];

  return (
    <div className="advisor-card-grid">
      <Card size="small" title={<span><WarningOutlined /> 风险等级</span>}>
        <Tag color={result?.risk_level === "high" ? "red" : result?.risk_level === "medium" ? "orange" : "green"}>
          {result?.risk_level === "high" ? "危险" : result?.risk_level === "medium" ? "预警" : "正常"}
        </Tag>
        <Text type="secondary">置信度 {result ? `${Math.round(result.confidence * 100)}%` : "82%"}</Text>
      </Card>
      <Card size="small" title={<span><BulbOutlined /> 问题原因</span>}>
        <Paragraph>税负率、现金流和费用率出现偏离，需要结合发票、凭证和申报底稿复核。</Paragraph>
      </Card>
      <Card size="small" title={<span><FileTextOutlined /> 政策依据</span>}>
        <Paragraph>
          {result?.citations[0]?.title ?? "企业所得税、增值税及发票管理相关规定"}
        </Paragraph>
      </Card>
      <Card size="small" title={<span><CheckCircleOutlined /> 优化建议</span>}>
        <Timeline
          items={actionItems.slice(0, 3).map((item) => ({
            content: item
          }))}
        />
      </Card>
      <Card size="small" title="执行方案" className="advisor-card-grid__wide">
        <Paragraph>创建风险复核任务，关联证据链，完成负责人确认、处理记录、复核结论和报表归档。</Paragraph>
      </Card>
    </div>
  );
}
