# 企业级 AI 财务 SaaS UI 重设计实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有前端第一阶段升级为商业级 AI 财务助手 SaaS：固定导航、全局顶栏、企业驾驶舱、AI 财务顾问、高级数据表与核心财务工作流入口。

**Architecture:** 使用 Ant Design 作为企业 UI 基座，保留现有 React + TypeScript + Vite + ECharts 技术栈。第一阶段重构主框架与核心体验，已有业务面板继续作为模块详情挂载，避免重做时丢失现有财务功能。

**Tech Stack:** React 19、TypeScript、Vite、Ant Design、@ant-design/icons、ECharts。

## Global Constraints

- 始终使用简体中文回复；代码注释和新增文档使用中文。
- 不生成简单 Demo，必须按商业 SaaS 产品标准开发。
- 第一阶段只落地主框架、首页 Dashboard、AI 财务顾问、税务风险提醒、高级数据表基础体验。
- 左侧固定导航宽度为 240px，支持电脑端和平板端。
- 顶部包含全局搜索、消息提醒、AI 助手入口、用户头像。
- 首页必须让用户 5 秒内看懂收入、成本、利润、现金流、税负率、风险等级。
- 数据表必须具备筛选、搜索、排序、分页、导出入口。
- AI 财务助手必须采用类似 ChatGPT 的历史会话 + 聊天窗口结构，回答以卡片形式呈现。
- 不使用花哨渐变、大量动画、廉价网页感或老式后台管理风格。

---

### Task 1: UI 框架依赖与结构测试

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Create: `frontend/tests/enterpriseSaasLayout.test.mjs`

**Interfaces:**
- Produces: `antd` 与 `@ant-design/icons` 运行依赖。
- Produces: 企业 SaaS UI 结构测试，后续任务必须保持通过。

- [ ] **Step 1: Write the failing test**

创建 `frontend/tests/enterpriseSaasLayout.test.mjs`，测试内容：

```js
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const packageJson = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));
const dashboardLayout = readFileSync(new URL("../src/components/DashboardLayout.tsx", import.meta.url), "utf8");

test("企业级 SaaS UI 接入 Ant Design 组件库", () => {
  assert.ok(packageJson.dependencies.antd, "缺少 antd 依赖");
  assert.ok(packageJson.dependencies["@ant-design/icons"], "缺少 @ant-design/icons 依赖");
  assert.match(dashboardLayout, /from "antd"/);
});

test("固定导航包含第一阶段商业 SaaS 信息架构", () => {
  for (const label of ["首页 Dashboard", "智能财务分析", "发票管理", "税务风险检测", "财务报表", "数据分析", "AI 财务顾问", "企业设置"]) {
    assert.ok(dashboardLayout.includes(label), `缺少导航项：${label}`);
  }
});

test("顶部全局栏包含搜索、消息、AI 助手与用户入口", () => {
  for (const label of ["搜索发票、凭证、报表、风险", "消息提醒", "AI助手", "财务经理"]) {
    assert.ok(dashboardLayout.includes(label), `缺少顶部入口：${label}`);
  }
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node frontend/tests/enterpriseSaasLayout.test.mjs`

Expected: FAIL，原因是尚未安装 `antd`，且 `DashboardLayout.tsx` 尚未接入企业 SaaS 信息架构。

- [ ] **Step 3: Install UI dependencies**

Run: `npm --prefix frontend install antd @ant-design/icons`

Expected: `frontend/package.json` 和 `frontend/package-lock.json` 出现新增依赖。

- [ ] **Step 4: Add test command to npm test chain**

在 `frontend/package.json` 的 `test:nav` 开头加入：

```json
"node tests/enterpriseSaasLayout.test.mjs && ..."
```

- [ ] **Step 5: Run targeted test**

Run: `node frontend/tests/enterpriseSaasLayout.test.mjs`

Expected: 依赖断言通过；布局源码断言仍失败，等待 Task 2 实现。

### Task 2: 企业级 App Shell 与固定导航

**Files:**
- Modify: `frontend/src/main.tsx`
- Replace: `frontend/src/components/DashboardLayout.tsx`
- Modify: `frontend/src/styles.css`
- Test: `frontend/tests/enterpriseSaasLayout.test.mjs`

**Interfaces:**
- Consumes: `DashboardLayoutProps` 保持不变。
- Produces: 固定 240px 左侧导航、顶部全局栏、主内容容器、AI Drawer 状态。

- [ ] **Step 1: Write failing assertions**

在 `frontend/tests/enterpriseSaasLayout.test.mjs` 增加：

```js
test("主框架声明 240px 固定导航与 AI Drawer", () => {
  assert.match(dashboardLayout, /Sider width=\{240\}/);
  assert.match(dashboardLayout, /Drawer/);
  assert.match(dashboardLayout, /open=\{isAiDrawerOpen\}/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node frontend/tests/enterpriseSaasLayout.test.mjs`

Expected: FAIL，原因是当前布局还不是 Ant Design App Shell。

- [ ] **Step 3: Implement minimal shell**

在 `DashboardLayout.tsx` 中：
- 使用 `Layout`、`Menu`、`Input`、`Badge`、`Avatar`、`Button`、`Drawer`。
- 左侧导航固定 240px。
- 顶栏包含全局搜索、消息提醒、AI助手、用户头像。
- 保持 `onOpenDataEntry`、`overview`、`homeDashboard`、`report` 继续可用。

- [ ] **Step 4: Run targeted test**

Run: `node frontend/tests/enterpriseSaasLayout.test.mjs`

Expected: PASS。

### Task 3: 首页企业经营驾驶舱

**Files:**
- Replace: `frontend/src/components/HomeDashboardPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Modify: `frontend/src/styles.css`
- Test: `frontend/tests/enterpriseSaasLayout.test.mjs`

**Interfaces:**
- Consumes: `HomeDashboard`、`DashboardOverview`、`ManagementReport`。
- Produces: `HomeDashboardPanel({ dashboard, overview, report, onOpenDataEntry, onOpenAiAdvisor })`。

- [ ] **Step 1: Write failing assertions**

在测试中增加：

```js
const homeDashboardPanel = readFileSync(new URL("../src/components/HomeDashboardPanel.tsx", import.meta.url), "utf8");

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node frontend/tests/enterpriseSaasLayout.test.mjs`

Expected: FAIL，原因是首页尚未改造成企业驾驶舱。

- [ ] **Step 3: Implement dashboard cockpit**

重写 `HomeDashboardPanel.tsx`：
- 顶部 6 个指标卡：收入、成本、利润、现金流、税负率、风险等级。
- 中部：趋势图、环形图、柱状图。
- 右侧或下方：风险提醒、待办事项、AI 建议。
- 底部：高级数据表，支持搜索、筛选、排序、分页、导出按钮。

- [ ] **Step 4: Run targeted test**

Run: `node frontend/tests/enterpriseSaasLayout.test.mjs`

Expected: PASS。

### Task 4: AI 财务顾问体验

**Files:**
- Create: `frontend/src/components/AIFinanceAdvisor.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Modify: `frontend/src/styles.css`
- Test: `frontend/tests/enterpriseSaasLayout.test.mjs`

**Interfaces:**
- Produces: `AIFinanceAdvisor({ embedded?: boolean })`。
- Consumes: `askFinanceQuestion(question: string)`。

- [ ] **Step 1: Write failing assertions**

在测试中增加：

```js
const aiAdvisor = readFileSync(new URL("../src/components/AIFinanceAdvisor.tsx", import.meta.url), "utf8");

test("AI 财务顾问采用历史会话与卡片式回答", () => {
  for (const label of ["历史对话", "分析今年税务风险", "风险等级", "问题原因", "政策依据", "优化建议", "执行方案"]) {
    assert.ok(aiAdvisor.includes(label), `缺少 AI 顾问元素：${label}`);
  }
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node frontend/tests/enterpriseSaasLayout.test.mjs`

Expected: FAIL，原因是 `AIFinanceAdvisor.tsx` 不存在。

- [ ] **Step 3: Implement AI advisor**

新增 `AIFinanceAdvisor.tsx`：
- 左侧历史对话。
- 中间聊天窗口。
- 用户示例问题：“分析今年税务风险”。
- AI 回答用 `Card`、`Tag`、`Steps` 或分组卡片展示风险等级、问题原因、政策依据、优化建议、执行方案。

- [ ] **Step 4: Run targeted test**

Run: `node frontend/tests/enterpriseSaasLayout.test.mjs`

Expected: PASS。

### Task 5: 完整验证与视觉检查

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Modify: `frontend/src/components/HomeDashboardPanel.tsx`
- Create: `frontend/src/components/AIFinanceAdvisor.tsx`
- Modify: `frontend/src/styles.css`
- Test: all frontend tests and production build.

**Interfaces:**
- Produces: 可运行的第一阶段企业级 SaaS 前端。

- [ ] **Step 1: Run frontend tests**

Run: `npm --prefix frontend test`

Expected: PASS。

- [ ] **Step 2: Run production build**

Run: `npm --prefix frontend run build`

Expected: PASS；如果仅有 Vite chunk size warning，可以记录为非阻塞。

- [ ] **Step 3: Start dev server and inspect UI**

Run: `npm --prefix frontend run dev -- --port 5173`

Expected: 页面加载，左侧固定导航、顶部全局栏、首页驾驶舱、AI Drawer 可见。

- [ ] **Step 4: Capture desktop and tablet screenshots**

用 Playwright 或浏览器检查：
- Desktop: 1440px 宽。
- Tablet: 1024px 宽。

Expected: 文本不重叠，卡片不溢出，导航可用，核心指标 5 秒内可读。
