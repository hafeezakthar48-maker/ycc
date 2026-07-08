import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

const packageJson = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));
const dashboardLayout = readFileSync(new URL("../src/components/DashboardLayout.tsx", import.meta.url), "utf8");
const homeDashboardPanel = readFileSync(new URL("../src/components/HomeDashboardPanel.tsx", import.meta.url), "utf8");
const indexHtml = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const aiAdvisorUrl = new URL("../src/components/AIFinanceAdvisor.tsx", import.meta.url);
const aiAdvisor = existsSync(aiAdvisorUrl) ? readFileSync(aiAdvisorUrl, "utf8") : "";

test("企业级 SaaS UI 接入 Ant Design 组件库", () => {
  assert.ok(packageJson.dependencies.antd, "缺少 antd 依赖");
  assert.ok(packageJson.dependencies["@ant-design/icons"], "缺少 @ant-design/icons 依赖");
  assert.match(dashboardLayout, /from "antd"/);
});

test("固定导航包含第一阶段商业 SaaS 信息架构", () => {
  for (const label of [
    "首页 Dashboard",
    "智能财务分析",
    "发票管理",
    "税务风险检测",
    "财务报表",
    "数据分析",
    "AI 财务顾问",
    "企业设置"
  ]) {
    assert.ok(dashboardLayout.includes(label), `缺少导航项：${label}`);
  }
});

test("顶部全局栏包含搜索、消息、AI 助手与用户入口", () => {
  for (const label of ["搜索发票、凭证、报表、风险", "消息提醒", "AI助手", "财务经理"]) {
    assert.ok(dashboardLayout.includes(label), `缺少顶部入口：${label}`);
  }
});

test("首页驾驶舱覆盖核心指标与风险提醒", () => {
  for (const label of ["收入", "成本", "利润", "现金流", "税负率", "风险等级", "5秒财务状态"]) {
    assert.ok(homeDashboardPanel.includes(label), `缺少驾驶舱元素：${label}`);
  }
});

test("首页提供趋势图、环形图、柱状图和高级数据表区域", () => {
  for (const label of ["经营趋势", "成本结构", "现金流柱状图", "高级数据表"]) {
    assert.ok(homeDashboardPanel.includes(label), `缺少数据展示：${label}`);
  }
});

test("AI 财务顾问采用历史会话与卡片式回答", () => {
  for (const label of ["历史对话", "分析今年税务风险", "风险等级", "问题原因", "政策依据", "优化建议", "执行方案"]) {
    assert.ok(aiAdvisor.includes(label), `缺少 AI 顾问元素：${label}`);
  }
});

test("主框架将 AI 财务顾问接入 Drawer 与页面区域", () => {
  assert.match(dashboardLayout, /AIFinanceAdvisor/);
  assert.match(dashboardLayout, /open=\{isAiDrawerOpen\}/);
});

test("应用入口声明内嵌 favicon 以避免浏览器 404", () => {
  assert.match(indexHtml, /rel="icon"/);
  assert.match(indexHtml, /data:image\/svg\+xml/);
});
