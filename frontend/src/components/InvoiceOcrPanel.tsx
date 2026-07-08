import {
  CheckCircleOutlined,
  CloudUploadOutlined,
  FileTextOutlined,
  SafetyCertificateOutlined
} from "@ant-design/icons";
import { Alert, Button, Card, Col, Input, Progress, Row, Space, Statistic, Table, Tabs, Tag, Typography, Upload } from "antd";
import type { TableColumnsType, UploadProps } from "antd";
import { useState } from "react";
import { recognizeInvoiceText, uploadInvoiceFile } from "../services/dashboardApi";
import type { InvoiceField, InvoiceOcrResponse, InvoiceRiskItem } from "../types/invoiceOcr";

const { Paragraph, Text } = Typography;
const { TextArea } = Input;
const { Dragger } = Upload;

const sampleInvoiceText = `增值税电子普通发票
发票代码：044032300111
发票号码：12345678
开票日期：2026年06月30日
购买方名称：示例制造企业
购买方纳税人识别号：91310000MA1TEST001
销售方名称：上海云智科技有限公司
销售方纳税人识别号：91310115MA1K000002
金额：1000.00
税额：60.00
价税合计（大写）：壹仟零陆拾元整 （小写）¥1060.00`;

function percent(value: number) {
  return Math.round(value * 100);
}

function statusLabel(status: string) {
  if (status === "text_parsed") {
    return "文本已解析";
  }
  if (status === "missing") {
    return "OCR 引擎未接入";
  }
  return status;
}

function riskLevelColor(level: number) {
  if (level >= 4) {
    return "red";
  }
  if (level >= 3) {
    return "orange";
  }
  return "green";
}

export default function InvoiceOcrPanel() {
  const [text, setText] = useState(sampleInvoiceText);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<InvoiceOcrResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  const fieldColumns: TableColumnsType<InvoiceField> = [
    {
      title: "字段",
      dataIndex: "label",
      width: 160,
      sorter: (a, b) => a.label.localeCompare(b.label)
    },
    {
      title: "识别值",
      dataIndex: "value",
      render: (value: string | null) => value ?? <Text type="secondary">未识别</Text>
    },
    {
      title: "字段置信度",
      dataIndex: "confidence",
      width: 180,
      sorter: (a, b) => a.confidence - b.confidence,
      render: (value: number) => <Progress percent={percent(value)} size="small" />
    }
  ];

  const riskColumns: TableColumnsType<InvoiceRiskItem> = [
    {
      title: "风险事项",
      dataIndex: "title",
      render: (value: string, record) => (
        <Space orientation="vertical" size={2}>
          <strong>{value}</strong>
          <Text type="secondary">{record.description}</Text>
        </Space>
      )
    },
    {
      title: "等级",
      dataIndex: "level",
      width: 96,
      render: (value: number) => <Tag color={riskLevelColor(value)}>L{value}</Tag>
    },
    {
      title: "处理建议",
      dataIndex: "suggestion"
    }
  ];

  const uploadProps: UploadProps = {
    accept: ".txt,.pdf,image/*",
    beforeUpload: (nextFile) => {
      setFile(nextFile);
      return false;
    },
    maxCount: 1,
    onRemove: () => {
      setFile(null);
    }
  };

  async function runTextRecognition(nextText = text) {
    const trimmed = nextText.trim();
    if (!trimmed) {
      setError("请先粘贴发票 OCR 文本。");
      return;
    }

    setIsBusy(true);
    setError(null);
    try {
      setResult(await recognizeInvoiceText(trimmed));
      setText(trimmed);
    } catch (ocrError) {
      setError(ocrError instanceof Error ? ocrError.message : "发票 OCR 识别失败");
    } finally {
      setIsBusy(false);
    }
  }

  async function runFileUpload() {
    if (!file) {
      setError("请选择发票图片、PDF 或文本文件。");
      return;
    }

    setIsBusy(true);
    setError(null);
    try {
      setResult(await uploadInvoiceFile(file));
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "发票文件上传识别失败");
    } finally {
      setIsBusy(false);
    }
  }

  const fields = result?.fields ?? [];
  const risks = result?.risks ?? [];
  const citations = result?.citations ?? [];
  const averageConfidence = fields.length
    ? Math.round(fields.reduce((sum, field) => sum + field.confidence, 0) / fields.length * 100)
    : 0;

  return (
    <section id="invoice-ocr" className="invoice-ocr-section invoice-workbench">
      <Card className="invoice-workbench__input" title="发票工作流" extra={<Tag color="blue">识别队列</Tag>}>
        <div className="invoice-workflow-steps">
          <span><CloudUploadOutlined /> 识别队列</span>
          <span><FileTextOutlined /> 字段置信度</span>
          <span><SafetyCertificateOutlined /> 合规复核</span>
          <span><CheckCircleOutlined /> 生成凭证草稿</span>
        </div>

        <Row gutter={[16, 16]}>
          <Col xs={24} xl={14}>
            <TextArea
              value={text}
              onChange={(event) => setText(event.target.value)}
              rows={9}
              placeholder="粘贴 OCR 文本或手动录入发票内容"
            />
          </Col>
          <Col xs={24} xl={10}>
            <Dragger {...uploadProps}>
              <p className="ant-upload-drag-icon"><CloudUploadOutlined /></p>
              <p className="ant-upload-text">拖入发票图片、PDF 或文本文件</p>
              <p className="ant-upload-hint">上传后可进入 OCR 队列，并与文本识别结果统一复核。</p>
            </Dragger>
            <Space wrap className="invoice-workbench__actions">
              <Button type="primary" loading={isBusy} onClick={() => runTextRecognition()}>
                识别文本
              </Button>
              <Button loading={isBusy} onClick={runFileUpload}>
                上传识别
              </Button>
              <Button>生成凭证草稿</Button>
            </Space>
            {file ? <Text type="secondary">已选择：{file.name}</Text> : null}
          </Col>
        </Row>
      </Card>

      {error ? <Alert type="error" showIcon message={error} /> : null}

      <Row gutter={[16, 16]} className="invoice-workbench__metrics">
        <Col xs={24} md={8}>
          <Card size="small">
            <Statistic title="字段置信度" value={averageConfidence} suffix="%" />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card size="small">
            <Statistic title="合规复核" value={risks.length} suffix="项" styles={{ content: { color: risks.length ? "#cf1322" : "#166534" } }} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card size="small">
            <Statistic title="引用依据" value={citations.length} suffix="条" />
          </Card>
        </Col>
      </Row>

      <Tabs
        className="invoice-workbench__tabs"
        items={[
          {
            key: "fields",
            label: "字段置信度",
            children: (
              <Card>
                <Table
                  className="invoice-confidence-table"
                  rowKey="key"
                  columns={fieldColumns}
                  dataSource={fields}
                  pagination={{ pageSize: 6, showSizeChanger: false }}
                  locale={{ emptyText: "识别后展示发票字段、识别值和置信度。" }}
                />
              </Card>
            )
          },
          {
            key: "risks",
            label: "合规复核",
            children: (
              <Card>
                {result ? (
                  <Alert
                    type={risks.length ? "warning" : "success"}
                    showIcon
                    message={risks.length ? `发现 ${risks.length} 项风险，建议进入税务风险驾驶舱闭环。` : "未发现基础字段和价税勾稽异常。"}
                  />
                ) : null}
                <Table
                  rowKey="id"
                  columns={riskColumns}
                  dataSource={risks}
                  pagination={false}
                  locale={{ emptyText: "暂无发票合规风险。" }}
                />
              </Card>
            )
          },
          {
            key: "citations",
            label: "引用依据",
            children: (
              <Card>
                <div className="invoice-citation-list">
                  {citations.length ? citations.map((citation) => (
                    <article key={`${citation.title}-${citation.published_date}`}>
                      <strong>{citation.title}</strong>
                      <Paragraph>
                        {citation.authority}
                        {citation.document_number ? ` · ${citation.document_number}` : ""}
                      </Paragraph>
                      <Text type="secondary">
                        发布/成文：{citation.published_date} · 状态：{citation.status} · 更新：{citation.updated_at}
                      </Text>
                      <a href={citation.source_url} target="_blank" rel="noreferrer">查看来源</a>
                    </article>
                  )) : (
                    <Text type="secondary">识别后展示发票法规、政策依据和来源链接。</Text>
                  )}
                </div>
              </Card>
            )
          }
        ]}
      />
    </section>
  );
}
