import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("会计档案面板展示文档、案卷和下载入口", async () => {
  const panel = await readFile(resolve("src/components/AccountingArchivePanel.tsx"), "utf8");
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");
  const voucherPanel = await readFile(resolve("src/components/VoucherCenterPanel.tsx"), "utf8");
  const styles = await readFile(resolve("src/styles.css"), "utf8");

  assert.match(panel, /accounting-archive-panel/);
  assert.match(panel, /fetchAccountingArchiveDocuments/);
  assert.match(panel, /createAccountingArchiveCase/);
  assert.match(panel, /downloadAccountingArchivePackage/);
  assert.match(panel, /from "antd"/);
  for (const component of ["Alert", "Button", "Card", "Statistic", "Table", "Tabs", "Tag"]) {
    assert.ok(panel.includes(component), `会计档案工作台缺少 Ant Design 组件：${component}`);
  }
  for (const label of [
    "电子凭证与档案案卷工作台",
    "档案台账",
    "案卷编制",
    "归档包下载",
    "验真状态",
    "OCR 状态",
    "保管期限",
    "哈希校验",
    "创建案卷"
  ]) {
    assert.ok(panel.includes(label), `会计档案工作台缺少文案：${label}`);
  }
  assert.match(panel, /sha256_hash/);
  assert.match(panel, /verification_status/);
  assert.match(panel, /scroll=\{\{ x:/, "会计档案台账需要表内横向滚动");
  assert.doesNotMatch(panel, /<table/, "会计档案工作台不应继续使用原生 table");
  for (const className of [
    "accounting-archive-workbench",
    "accounting-archive-toolbar",
    "accounting-archive-summary-grid",
    "accounting-archive-layout",
    "accounting-archive-ledger-table"
  ]) {
    assert.ok(styles.includes(className), `缺少会计档案工作台样式：${className}`);
  }
  assert.match(styles, /\.accounting-archive-ledger-table\s*\{[\s\S]*overflow-x: hidden/, "会计档案台账外层需要裁剪内部宽表，避免页面级横向溢出");
  assert.match(styles, /\.accounting-archive-ledger-table \.ant-table-content[\s\S]*overflow-x: auto/, "会计档案台账内容层需要保留局部横向滚动");
  assert.match(layout, /AccountingArchivePanel/);
  assert.match(voucherPanel, /archive_document_id/);
  assert.match(voucherPanel, /sha256_hash/);
  assert.match(voucherPanel, /storage_status/);
});
