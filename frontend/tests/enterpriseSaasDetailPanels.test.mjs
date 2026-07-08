import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const invoicePanel = readFileSync(new URL("../src/components/InvoiceOcrPanel.tsx", import.meta.url), "utf8");
const riskPanel = readFileSync(new URL("../src/components/RiskPanel.tsx", import.meta.url), "utf8");
const styles = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");

test("发票管理内部面板升级为 Ant Design 工作台", () => {
  assert.match(invoicePanel, /from "antd"/);
  for (const component of ["Alert", "Card", "Progress", "Table", "Tabs", "Upload"]) {
    assert.ok(invoicePanel.includes(component), `发票面板缺少 ${component}`);
  }
  for (const label of ["发票工作流", "识别队列", "字段置信度", "合规复核", "引用依据", "生成凭证草稿"]) {
    assert.ok(invoicePanel.includes(label), `发票面板缺少文案：${label}`);
  }
});

test("税务风险闭环内部面板升级为可运营的 Ant Design 表格", () => {
  assert.match(riskPanel, /from "antd"/);
  for (const component of ["Alert", "Button", "Progress", "Table", "Tag"]) {
    assert.ok(riskPanel.includes(component), `风险面板缺少 ${component}`);
  }
  for (const label of ["风险闭环工作台", "闭环进度", "负责人", "到期日", "处理记录", "复核记录", "复核关闭"]) {
    assert.ok(riskPanel.includes(label), `风险面板缺少文案：${label}`);
  }
  assert.match(riskPanel, /scroll=\{\{ x:/, "风险闭环表格需要表内横向滚动，不能撑宽页面");
  assert.match(styles, /\.risk-closure-table[\s\S]*overflow-x: hidden/, "风险闭环表格外层需要裁剪内部宽表，避免形成页面级横向溢出");
});

test("细节面板有专业 SaaS 密度和响应式样式", () => {
  for (const className of [
    "invoice-workbench",
    "invoice-workbench__input",
    "invoice-confidence-table",
    "risk-closure-workbench",
    "risk-closure-toolbar"
  ]) {
    assert.ok(styles.includes(className), `缺少细节面板样式：${className}`);
  }
  assert.match(styles, /\.module-workspace__content > \*[\s\S]*min-width: 0/, "模块内容子项需要可收缩，避免平板端被宽表格撑开");
  assert.match(styles, /\.saas-grid > \*[\s\S]*min-width: 0/, "SaaS 网格卡片需要可收缩，避免平板端页面级横向溢出");
});
