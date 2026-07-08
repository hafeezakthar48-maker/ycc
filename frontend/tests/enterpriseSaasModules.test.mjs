import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

const layout = readFileSync(new URL("../src/components/DashboardLayout.tsx", import.meta.url), "utf8");
const styles = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");
const workspaceUrl = new URL("../src/components/SaasModuleWorkspace.tsx", import.meta.url);
const workspace = existsSync(workspaceUrl) ? readFileSync(workspaceUrl, "utf8") : "";

test("第二阶段业务模块使用统一 SaaS 工作区外壳", () => {
  assert.ok(workspace, "缺少 SaasModuleWorkspace 组件");
  assert.match(layout, /SaasModuleWorkspace/);
  assert.match(workspace, /interface SaasModuleWorkspaceProps/);
  for (const prop of ["summaryItems", "statusItems", "primaryActions", "children"]) {
    assert.ok(workspace.includes(prop), `工作区组件缺少 ${prop}`);
  }
});

test("四个高频业务模块拥有专业工作台标题和运营摘要", () => {
  for (const label of [
    "发票处理中心",
    "税务风险驾驶舱",
    "报表交付中心",
    "数据运营中心",
    "待识别票据",
    "风险闭环",
    "报表口径",
    "数据质量"
  ]) {
    assert.ok(layout.includes(label), `缺少模块工作台文案：${label}`);
  }
});

test("模块工作区提供少点击动作、状态队列和专业布局样式", () => {
  for (const className of [
    "module-workspace",
    "module-workspace__header",
    "module-summary-grid",
    "module-action-bar",
    "module-status-list",
    "module-workspace__body"
  ]) {
    assert.ok(styles.includes(className), `缺少模块工作区样式：${className}`);
  }
  assert.match(styles, /@media \(max-width: 1180px\)[\s\S]*module-workspace__header/);
});

test("数据运营中心旧核算表单在 SaaS 内容列内自动换行", () => {
  assert.match(styles, /\.period-close-toolbar\s*\{[\s\S]*repeat\(auto-fit, minmax\(120px, 1fr\)\)/, "期间结账类工具栏需要按可用宽度自动换行");
  assert.match(styles, /\.fixed-asset-form\s*\{[\s\S]*repeat\(auto-fit, minmax\(140px, 1fr\)\)/, "固定资产表单需要按可用宽度自动换行");
  assert.match(styles, /\.fixed-asset-inventory-form\s*\{[\s\S]*repeat\(auto-fit, minmax\(140px, 1fr\)\)/, "固定资产盘点表单需要按可用宽度自动换行");
});
