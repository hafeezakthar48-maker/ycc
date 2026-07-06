# Finance Data Import And Manual Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 China Finance AI Assistant 增加 Excel/WPS 表格导入和手动填写报表数据能力，让用户不用示例数据也能生成驾驶舱、风险预警和报告草稿。

**Architecture:** 后端新增 `POST /api/v1/dashboard/analyze` 统一分析接口，以及 `POST /api/v1/dashboard/import/excel` 导入预览接口；前端新增“数据录入中心”，支持上传 `.xlsx/.xlsm` 和手动编辑多期报表数据，最终都调用同一套分析接口刷新驾驶舱。

**Tech Stack:** FastAPI、Pydantic、openpyxl、python-multipart、pytest、React、TypeScript、ECharts。

**Execution Constraint:** 跳过 Git，本计划只做本地文件修改、测试、构建和浏览器验证。

---

## Tasks

- [ ] 后端测试先行：新增分析接口测试、Excel 解析测试。
- [ ] 后端实现：新增导入模型、`spreadsheet_import_service.py`、`analyze` 与 `import/excel` API。
- [ ] 前端实现：新增数据录入中心组件、API 客户端、类型定义，支持上传和手动表格。
- [ ] 验证：后端 `pytest`、前端 `npm run build`、`npm audit`、API 手工请求、桌面与移动浏览器截图检查。

## Scope

第一版支持：

- `.xlsx`
- `.xlsm`
- WPS 表格另存为 `.xlsx`
- 手动填写多期核心报表字段
- 一键分析并刷新驾驶舱

第一版不支持：

- WPS 原生 `.et`
- 旧版 `.xls`
- OCR 表格识别
- 复杂合并单元格财务报表自动还原
