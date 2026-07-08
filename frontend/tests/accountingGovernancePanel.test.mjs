import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("AI财务中心接入正式核算上线治理面板", async () => {
  const panel = await readFile(resolve("src/components/AccountingGovernancePanel.tsx"), "utf8");
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");
  const systemAdminPanel = await readFile(resolve("src/components/SystemAdminPanel.tsx"), "utf8");
  const styles = await readFile(resolve("src/styles.css"), "utf8");

  assert.match(panel, /accounting-governance-panel/);
  assert.match(panel, /fetchAccountingIntegrityChecks/);
  assert.match(panel, /previewAccountingMigration/);
  assert.match(panel, /createAccountingBackup/);
  assert.match(panel, /rehearseAccountingRestore/);
  assert.match(panel, /fetchAccountingGoLiveGate/);
  assert.match(panel, /accounting_migration.apply/);
  assert.match(panel, /from "antd"/);
  for (const component of ["Alert", "Button", "Card", "Statistic", "Table", "Tabs", "Tag"]) {
    assert.ok(panel.includes(component), `正式核算上线治理工作台缺少 Ant Design 组件：${component}`);
  }
  for (const label of [
    "正式核算上线治理工作台",
    "上线门禁",
    "完整性校验",
    "迁移 dry-run",
    "迁移台账",
    "备份恢复",
    "权限矩阵",
    "职责分离",
    "回归验证",
    "创建备份",
    "恢复演练"
  ]) {
    assert.ok(panel.includes(label), `正式核算上线治理工作台缺少文案：${label}`);
  }
  assert.match(panel, /scroll=\{\{ x:/, "迁移台账需要表内横向滚动");
  assert.doesNotMatch(panel, /<table/, "正式核算上线治理工作台不应继续使用原生 table");
  for (const className of [
    "accounting-governance-workbench",
    "accounting-governance-toolbar",
    "accounting-governance-summary-grid",
    "accounting-governance-layout",
    "accounting-governance-migration-table"
  ]) {
    assert.ok(styles.includes(className), `缺少正式核算上线治理工作台样式：${className}`);
  }
  assert.match(styles, /\.accounting-governance-migration-table\s*\{[\s\S]*overflow-x: hidden/, "迁移台账外层需要裁剪内部宽表，避免页面级横向溢出");
  assert.match(styles, /\.accounting-governance-migration-table \.ant-table-content[\s\S]*overflow-x: auto/, "迁移台账内容层需要保留局部横向滚动");
  assert.match(layout, /AccountingGovernancePanel/);
  assert.match(systemAdminPanel, /accounting_governance\.read/);
});
