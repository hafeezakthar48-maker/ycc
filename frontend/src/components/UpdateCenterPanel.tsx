import { CloudSyncOutlined, ReloadOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Descriptions, List, Space, Tag, Typography } from "antd";
import { useEffect, useState } from "react";
import { checkApplicationUpdateNow, checkUpdateCenterNow, fetchUpdateCenterStatus } from "../services/dashboardApi";
import type { ApplicationUpdateCheckResult, UpdateCenterStatus, UpdateCheckResult } from "../types/updateCenter";

const { Text } = Typography;
const DEFAULT_MONTHLY_COPY = "每月 1 号自动更新";

export default function UpdateCenterPanel() {
  const [status, setStatus] = useState<UpdateCenterStatus | null>(null);
  const [lastResult, setLastResult] = useState<UpdateCheckResult | null>(null);
  const [lastAppResult, setLastAppResult] = useState<ApplicationUpdateCheckResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isChecking, setIsChecking] = useState(false);
  const [isCheckingApp, setIsCheckingApp] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshStatus() {
    setError(null);
    const response = await fetchUpdateCenterStatus();
    setStatus(response);
  }

  useEffect(() => {
    refreshStatus()
      .catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : "联网更新中心状态读取失败");
      })
      .finally(() => setIsLoading(false));
  }, []);

  async function handleCheckNow() {
    setIsChecking(true);
    setError(null);
    try {
      const result = await checkUpdateCenterNow();
      setLastResult(result);
      await refreshStatus();
    } catch (checkError) {
      setError(checkError instanceof Error ? checkError.message : "手动检查更新失败");
    } finally {
      setIsChecking(false);
    }
  }

  async function handleCheckApplicationNow() {
    setIsCheckingApp(true);
    setError(null);
    try {
      const result = await checkApplicationUpdateNow();
      setLastAppResult(result);
      await refreshStatus();
    } catch (checkError) {
      setError(checkError instanceof Error ? checkError.message : "软件本体更新检查失败");
    } finally {
      setIsCheckingApp(false);
    }
  }

  const scheduleCopy = status ? `每月 ${status.config.schedule_day} 号自动检查` : DEFAULT_MONTHLY_COPY;

  return (
    <Card
      title={
        <Space>
          <CloudSyncOutlined />
          联网更新中心
        </Space>
      }
      extra={
        <Button icon={<ReloadOutlined />} loading={isChecking} onClick={handleCheckNow}>
          立即检查更新
        </Button>
      }
      loading={isLoading}
    >
      <Space direction="vertical" size={16} className="update-center-panel">
        <Alert
          type={status?.online_status === "online" ? "success" : status?.online_status === "failed" ? "error" : "info"}
          showIcon
          message={lastResult?.message ?? "Codex 基础更新源按月检查法规、税率与政策数据包。"}
          description={`${DEFAULT_MONTHLY_COPY}，当前计划：${scheduleCopy}。软件不上传企业财务数据。`}
        />

        {error && <Alert type="error" showIcon message={error} />}

        <Descriptions bordered size="small" column={{ xs: 1, md: 2 }}>
          <Descriptions.Item label="更新源">{status?.config.provider ?? "codex"}</Descriptions.Item>
          <Descriptions.Item label="更新通道">{status?.config.update_channel ?? "stable"}</Descriptions.Item>
          <Descriptions.Item label="自动更新">
            <Tag color={status?.config.auto_update_enabled === false ? "default" : "blue"}>
              {status?.config.auto_update_enabled === false ? "已关闭" : "已开启"}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="政策包版本">{status?.current_policy_version ?? "local-bundled"}</Descriptions.Item>
          <Descriptions.Item label="下次检查">{formatDate(status?.next_scheduled_check)}</Descriptions.Item>
          <Descriptions.Item label="最近成功">{formatDate(status?.last_successful_update_at)}</Descriptions.Item>
        </Descriptions>

        <Card
          size="small"
          title="软件本体更新"
          extra={
            <Button size="small" loading={isCheckingApp} onClick={handleCheckApplicationNow}>
              检查软件更新
            </Button>
          }
        >
          <Descriptions size="small" column={{ xs: 1, md: 2 }}>
            <Descriptions.Item label="当前版本">{status?.current_app_version ?? "0.1.0"}</Descriptions.Item>
            <Descriptions.Item label="可用版本">{status?.available_app_version ?? "未发现"}</Descriptions.Item>
            <Descriptions.Item label="更新包">
              {status?.app_update_package_path ? "已下载，等待独立更新器安装" : "未下载"}
            </Descriptions.Item>
            <Descriptions.Item label="强制更新">
              <Tag color={status?.app_update_required ? "red" : "default"}>
                {status?.app_update_required ? "是" : "否"}
              </Tag>
            </Descriptions.Item>
          </Descriptions>
          {lastAppResult && (
            <Alert
              type={lastAppResult.status === "failed" ? "error" : "info"}
              showIcon
              message={lastAppResult.message}
            />
          )}
        </Card>

        <List
          size="small"
          header={<Text strong>最近更新日志</Text>}
          dataSource={status?.events.slice(0, 4) ?? []}
          locale={{ emptyText: "暂无更新日志" }}
          renderItem={(item) => (
            <List.Item>
              <Space direction="vertical" size={2}>
                <Space>
                  <Tag color={statusTagColor(item.status)}>{item.status}</Tag>
                  <Text>{item.message}</Text>
                </Space>
                <Text type="secondary">{formatDate(item.created_at)}</Text>
              </Space>
            </List.Item>
          )}
        />
      </Space>
    </Card>
  );
}

function statusTagColor(status: string) {
  if (status === "updated" || status === "up_to_date") {
    return "green";
  }
  if (status === "failed") {
    return "red";
  }
  return "blue";
}

function formatDate(value: string | null | undefined) {
  if (!value) {
    return "未记录";
  }
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}
