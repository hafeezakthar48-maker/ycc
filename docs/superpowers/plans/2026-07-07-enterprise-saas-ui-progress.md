# 企业级 AI 财务 SaaS UI 进度记录

日期：2026-07-07

## 当前目标

把现有前端从普通网页/旧式后台逐步升级为商业级 AI 财务助手 SaaS，面向财务人员长期使用，风格参考 Microsoft Office 365、Notion、飞书、钉钉专业版、SAP、金蝶云星空、用友 BIP、Linear、ChatGPT 企业版。

## 已完成

1. 主框架已升级为企业 SaaS App Shell：
   - 左侧固定 240px 导航。
   - 顶部全局搜索、消息提醒、AI 助手入口、用户头像。
   - 首页 Dashboard 企业驾驶舱。
   - AI 财务顾问 Drawer 与页面区域。

2. 首页 Dashboard 已升级：
   - 收入、成本、利润、现金流、税负率、风险等级。
   - 趋势图、环形图、柱状图、高级数据表区域。
   - 5 秒内可读的经营状态摘要。

3. AI 财务顾问已升级：
   - 历史对话 + 聊天窗口。
   - “分析今年税务风险”示例问题。
   - 风险等级、问题原因、政策依据、优化建议、执行方案卡片化展示。

4. 发票管理与税务风险模块已升级：
   - `InvoiceOcrPanel.tsx` 改为 Ant Design 发票工作台。
   - `RiskPanel.tsx` 改为风险闭环工作台。
   - 风险闭环表格增加表内横向滚动与外层裁剪，避免页面级横向溢出。

5. 财务报表模块已升级：
   - `FinancialStatementPanel.tsx` 改为“报表交付工作台”。
   - 包含四表预览、生成队列、平衡校验、取数追溯、管理层摘要。
   - 保留 `generateFinancialStatements`、`trace_items`、`validation_items`、四张标准报表能力。
   - 修复 Ant Design v6 `Space direction` 弃用 warning。
   - 修复指标卡被旧 grid 样式压成竖条的问题。

## 新增/更新测试

已接入 `frontend/package.json` 的 `npm test` 链路：

- `frontend/tests/enterpriseSaasLayout.test.mjs`
- `frontend/tests/enterpriseSaasModules.test.mjs`
- `frontend/tests/enterpriseSaasDetailPanels.test.mjs`
- `frontend/tests/enterpriseSaasStatementWorkbench.test.mjs`

这些测试覆盖：

- 企业 SaaS 主框架。
- 四个高频业务模块工作区外壳。
- 发票与税务风险 Ant Design 工作台。
- 财务报表交付工作台。
- 桌面/平板端宽表不造成页面级横向溢出的关键 CSS 约束。

## 最近一次验证结果

已通过：

```powershell
npm --prefix frontend test
npm --prefix frontend run build
git diff --check
```

说明：

- `npm --prefix frontend run build` 仅有 Vite 大 chunk 提示，不是构建失败。
- `git diff --check` 仅提示既有打包文件 LF/CRLF 转换 warning，不是空白错误。

已通过 Playwright 浏览器验收：

- 桌面宽度：1440px。
- 平板宽度：1024px。
- 无页面级横向溢出。
- 无控制台 warning/error。
- 无异常网络错误。

截图：

- `output/playwright/enterprise-saas-detail-invoice-desktop.png`
- `output/playwright/enterprise-saas-detail-risk-desktop.png`
- `output/playwright/enterprise-saas-detail-tablet.png`
- `output/playwright/enterprise-saas-statement-workbench-desktop.png`
- `output/playwright/enterprise-saas-statement-workbench-tablet.png`

## 当前工作树注意事项

当前有多批未提交改动，包含：

- 企业 SaaS UI 改造相关前端文件。
- Windows 桌面安装包/启动入口相关后端与脚本文件。
- 新增 `backend/assets/`。
- 新增 SaaS UI 测试文件。

重要：不要回滚这些未提交改动；它们是本阶段持续开发成果。

## 下次建议继续做

优先级建议：

1. 报表映射面板升级为 Ant Design 工作台：
   - 当前 `StatementMappingPanel.tsx` 仍偏旧式按钮和原生表格。
   - 建议做成“报表口径映射工作台”，包含映射集概览、四表 Tabs、高级表格、规则来源、校验追溯入口。

2. 报表归档面板升级为 Ant Design 工作台：
   - 当前 `StatementArchivePanel.tsx` 仍偏旧式原生表格。
   - 建议做成“归档与正式交付工作台”，包含快照版本、锁定状态、导出动作、审计信息、哈希校验。

3. 数据分析模块继续 SaaS 化：
   - 把大量旧财务核算面板逐步收敛为统一工作台密度。
   - 优先处理会撑宽页面的宽表和旧 `voucher-table-wrap` 区域。

4. 桌面安装包线：
   - 工作树里已有 Windows 打包相关改动。
   - 下次如果切回安装包目标，需要单独验证 exe、安装脚本、桌面快捷方式和图标，不要与前端 UI 改造混在一个验收结论里。

## 下次启动建议

继续开发前先运行：

```powershell
git status --short
npm --prefix frontend test
```

如果需要视觉验收，再启动：

```powershell
npm --prefix frontend run dev -- --port 5173
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

注意：如果看到 `output` 下旧的 `*-dev-pids.json`，先确认 5173/8000 是否真的仍在监听，不要只相信旧 PID 文件。
