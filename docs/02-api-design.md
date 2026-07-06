# API 设计

## 健康检查

```text
GET /health
```

返回：

```json
{ "status": "ok" }
```

## AI 首页

```text
GET /api/v1/home/dashboard?period=2026-06
```

返回经营概况、利润、现金流、库存、税务五组首页指标，以及 AI 今日提示。

```text
POST /api/v1/home/analyze
```

请求结构与驾驶舱手动分析一致：

```json
{
  "period": "2026-06",
  "records": []
}
```

返回基于用户导入或手动填写数据重新计算的 AI 首页。

## 经营驾驶舱总览

```text
GET /api/v1/dashboard/overview?period=2026-06
```

返回核心指标、趋势图数据、费用结构、现金流、利润瀑布、风险热力图、风险摘要和 AI 摘要。

## 风险清单

```text
GET /api/v1/dashboard/risks?period=2026-06
```

返回风险标题、等级、触发原因、建议检查资料和谨慎合规提示。

## 报告草稿

```text
GET /api/v1/dashboard/report?period=2026-06
```

返回利润分析、资金分析、风险提示和管理建议。

## 示例数据

```text
GET /api/v1/dashboard/sample-data
```

返回内置 12 个月示例财务数据。

## OCR 发票识别

```text
POST /api/v1/invoice-ocr/recognize-text
```

请求：

```json
{ "text": "增值税电子普通发票\n发票号码：12345678\n金额：1000.00\n税额：60.00\n价税合计（小写）¥1060.00" }
```

返回发票类型、结构化字段、风险提示、告警和法规引用。

```text
POST /api/v1/invoice-ocr/upload
```

支持上传 `.txt` 文本文件并复用文本识别逻辑。图片 / PDF 在未配置 OCR 引擎时返回 `engine_status=missing` 和明确告警，不伪造识别结果。

## AI 凭证草稿

```text
POST /api/v1/vouchers/draft
```

请求：

```json
{
  "business_type": "expense_purchase",
  "voucher_date": "2026-06-30",
  "counterparty": "上海云智科技有限公司",
  "amount": "1000.00",
  "tax_amount": "60.00",
  "total_amount_with_tax": "1060.00",
  "payment_status": "unpaid",
  "memo": "办公服务费"
}
```

返回凭证场景、摘要、借贷分录、借方合计、贷方合计、平衡状态、风险提示、审核建议和法规/准则引用。当前接口只生成草稿，不写入正式账簿。

## 凭证中心 MVP

```text
GET /api/v1/vouchers/center
GET /api/v1/vouchers/center?account_set_id=cross_border
```

返回当前 SQLite 凭证中心的凭证总数和凭证列表；传入 `account_set_id` 时只返回指定账套凭证。

```text
POST /api/v1/vouchers/center
```

请求：

```json
{
  "account_set_id": "default",
  "voucher_date": "2026-06-30",
  "summary": "办公服务费",
  "counterparty": "上海云智科技有限公司",
  "invoice_number": "12345678",
  "amount": "1000.00",
  "tax_amount": "60.00",
  "total_amount_with_tax": "1060.00",
  "lines": [
    {
      "account_code": "6602",
      "account_name": "管理费用",
      "direction": "借",
      "amount": "1000.00",
      "explanation": "办公服务费"
    },
    {
      "account_code": "22210101",
      "account_name": "应交税费-应交增值税（进项税额）",
      "direction": "借",
      "amount": "60.00",
      "explanation": "进项税额"
    },
    {
      "account_code": "2202",
      "account_name": "应付账款",
      "direction": "贷",
      "amount": "1060.00",
      "explanation": "应付未付款"
    }
  ]
}
```

返回自动编号后的凭证记录、账套标识、审核状态、AI 自动审核结果和附件列表。`account_set_id` 不传时默认为 `default`；当前内置 `default` 和 `cross_border` 两个账套。编号规则为 `记-YYYYMM-0001`。

```text
PUT /api/v1/vouchers/center/{voucher_id}
POST /api/v1/vouchers/center/{voucher_id}/review
POST /api/v1/vouchers/center/{voucher_id}/unreview
POST /api/v1/vouchers/center/{voucher_id}/post
POST /api/v1/vouchers/center/{voucher_id}/unpost
```

分别用于修改草稿凭证、审核凭证、反审核凭证、过账凭证和反过账凭证。已审核凭证不允许直接修改，需要先反审核；已过账凭证不允许直接反审核，需要先反过账。过账请求体为：

```json
{ "operator": "财务主管" }
```

过账/反过账接口受 `voucher.post` 和 `voucher.unpost` 权限控制，并记录 `voucher.post` / `voucher.unpost` 审计日志。已关闭会计期间内的凭证不允许继续过账；关闭期间前如果同账套同期间仍有未过账凭证，会返回 `409`。当前过账只是凭证工作流状态，不生成正式不可变总账分录。

```text
POST /api/v1/vouchers/center/import
GET /api/v1/vouchers/center/export/csv
POST /api/v1/vouchers/center/{voucher_id}/attachments
```

分别用于 JSON 批量导入、CSV 导出和附件上传记录。当前附件接口只记录文件元数据与 OCR 接入状态，未做永久文件存储。

当前凭证中心是工作流 MVP，使用本地 SQLite 保存演示凭证、账套标识、审核状态、过账状态、附件元数据和月度编号序列；服务重启后凭证仍保留。账簿读模型可基于已审核凭证生成只读总账、明细账和科目余额表；默认账套、跨境电商账套与会计期间状态用于演示关账控制，该库仍不执行正式结账、反结账或完整多账套核算。

## 账簿读模型 MVP

```text
GET /api/v1/ledger/general?period=2026-06
GET /api/v1/ledger/general?period=2026-06&account_set_id=cross_border
```

返回指定期间、指定账套已审核凭证汇总后的总账视图，包括凭证数、分录数、借方合计、贷方合计、平衡状态和科目汇总列表。`account_set_id` 不传时默认为 `default`。

```text
GET /api/v1/ledger/detail?period=2026-06&account_code=6602
GET /api/v1/ledger/detail?period=2026-06&account_code=6602&account_set_id=cross_border
```

返回指定期间、指定科目的明细账分录，包括凭证号、凭证日期、摘要、交易对方、借方金额、贷方金额和科目余额方向。

```text
GET /api/v1/ledger/account-balances?period=2026-06
GET /api/v1/ledger/account-balances?period=2026-06&account_set_id=cross_border
```

返回指定期间的科目余额表，包括科目数、借贷合计、平衡状态、各科目的借方发生额、贷方发生额、余额方向和余额金额。

```text
GET /api/v1/ledger/account-sets
GET /api/v1/ledger/periods?account_set_id=default
POST /api/v1/ledger/periods/{period}/close?account_set_id=default
POST /api/v1/ledger/periods/{period}/reopen?account_set_id=default
```

账套接口返回默认账套和跨境电商账套；期间接口返回指定账套下的会计期间、状态、关闭人、关闭时间、凭证数量和已过账凭证数量。关闭/重开期间请求体为：

```json
{ "operator": "财务主管" }
```

当前账簿接口只读取指定账套内 `reviewed` 状态的凭证中心记录，不读取草稿凭证，不替代正式财务系统中的记账、结账、反结账、完整账套隔离和账簿锁定流程。期间关闭是工作流状态控制，只用于阻止继续过账。
账簿读取接口支持 `X-Actor-Id` 请求头，非 `system` 调用方必须具备 `ledger.read` 权限；期间关闭/重开必须具备 `ledger.period.manage` 权限。成功读取或操作会记录 `ledger.general.read`、`ledger.detail.read`、`ledger.account_balances.read`、`ledger.account_sets.read`、`ledger.periods.read`、`ledger.period.close`、`ledger.period.reopen` 审计日志；权限不足会返回 `403` 并记录 `denied` 审计日志。

## 固定资产台账 MVP

```text
GET /api/v1/fixed-assets?account_set_id=default
POST /api/v1/fixed-assets
POST /api/v1/fixed-assets/depreciation/run
POST /api/v1/fixed-assets/{asset_id}/inventory
POST /api/v1/fixed-assets/{asset_id}/dispose
POST /api/v1/fixed-assets/{asset_id}/sell
```

新增固定资产请求：

```json
{
  "account_set_id": "default",
  "name": "自动贴标机",
  "category": "生产设备",
  "acquisition_date": "2026-01-15",
  "original_cost": "120000.00",
  "salvage_value": "12000.00",
  "useful_life_months": 60,
  "location": "一号仓",
  "custodian": "设备管理员"
}
```

折旧计提请求：

```json
{
  "account_set_id": "default",
  "period": "2026-06",
  "operator": "财务主管"
}
```

系统按直线法计算月折旧额：`(original_cost - salvage_value) / useful_life_months`，并按账套和期间幂等计提折旧；同一资产同一期间重复计提时不会重复增加累计折旧。

盘点请求：

```json
{
  "inventory_date": "2026-06-30",
  "location": "二号仓",
  "custodian": "资产专员",
  "condition": "正常",
  "operator": "盘点员",
  "note": "已贴标签"
}
```

报废请求：

```json
{
  "disposal_date": "2026-06-30",
  "reason": "损坏报废",
  "operator": "财务主管"
}
```

出售请求：

```json
{
  "sale_date": "2026-06-30",
  "sale_amount": "118000.00",
  "reason": "更新换代",
  "operator": "财务主管"
}
```

当前固定资产台账是内存 MVP，服务重启后演示资产会重置；折旧、报废、出售和盘点只维护资产生命周期状态，不生成正式固定资产卡片附件、折旧凭证、总账分录或税会差异调整。接口支持 `X-Actor-Id` 请求头，读取、新增、折旧、处置和盘点分别受 `fixed_asset.read`、`fixed_asset.write`、`fixed_asset.depreciate`、`fixed_asset.dispose`、`fixed_asset.inventory` 权限控制，并记录 `fixed_asset.list`、`fixed_asset.create`、`fixed_asset.depreciation.run`、`fixed_asset.inventory`、`fixed_asset.dispose` 和 `fixed_asset.sell` 审计日志。

## 工资管理 MVP

```text
POST /api/v1/payroll/calculate
```

请求：

```json
{
  "account_set_id": "default",
  "period": "2026-06",
  "operator": "财务主管",
  "employees": [
    {
      "employee_id": "E001",
      "employee_name": "张会计",
      "department": "财务部",
      "base_salary": "20000.00",
      "bonus": "0.00",
      "allowance": "0.00",
      "social_security_base": "20000.00",
      "housing_fund_base": "20000.00",
      "special_additional_deduction": "1000.00",
      "other_deduction": "0.00"
    }
  ]
}
```

返回工资计算结果、员工明细和部门分析，包括：

- 应发工资、个人社保、企业社保、个人公积金、企业公积金。
- 应纳税所得额、税率、速算扣除数、个人所得税。
- 实发工资、企业用工成本。
- 部门人数、部门应发工资、部门实发工资和部门企业成本。

当前工资接口采用 MVP 简化口径：员工社保 10.5%、企业社保 26.3%、个人/企业公积金各 7%、基本扣除 5000 元和月度综合所得税率表；不处理累计预扣预缴、城市差异、封顶基数、年终奖单独计税、银行代发、工资条发送、个税正式申报或工资凭证自动生成。接口支持 `X-Actor-Id` 请求头，非 `system` 调用方必须具备 `payroll.calculate` 权限；成功或权限不足都会记录 `payroll.calculate` 审计日志。

## 财务报表自动生成 MVP

```text
POST /api/v1/financial-statements/generate
```

请求：

```json
{
  "period": "2026-06",
  "account_set_id": "default",
  "operator": "财务主管"
}
```

返回：

- `balance_sheet`：资产负债表，包含货币资金、应收账款、存货、固定资产、短期借款、应付账款、应交税费、所有者权益、资产合计、负债合计和负债权益平衡状态。
- `income_statement`：利润表，包含营业收入、营业成本、期间费用、利润总额和净利润。
- `cash_flow_statement`：现金流量表，包含经营、投资、筹资活动现金流量净额和现金净增加额。
- `equity_statement`：所有者权益变动表，包含期初权益、本期净利润、权益调整和期末权益。
- `management_summary`：管理报表摘要，包含净利率、资产负债率、现金流利润比、管理亮点和风险提示。

接口优先基于指定账套、指定期间的已审核凭证生成报表；当前账套无已审核凭证时，回退使用内置样例经营数据生成演示报表。当前 MVP 不覆盖合并报表、复杂金融工具、长期股权投资、递延所得税、现金流量表补充资料、附注披露或正式申报报表。
接口支持 `X-Actor-Id` 请求头，非 `system` 调用方必须具备 `statement.generate` 权限；成功或权限不足都会记录 `statement.generate` 审计日志。

## AI 自动审核

```text
POST /api/v1/audit/review
```

请求：

```json
{
  "audit_subject": "voucher",
  "voucher_date": "2026-06-30",
  "summary": "办公服务费",
  "counterparty": "上海云智科技有限公司",
  "invoice_number": "12345678",
  "amount": "1000.00",
  "tax_amount": "60.00",
  "total_amount_with_tax": "1060.00",
  "lines": [
    {
      "account_code": "6602",
      "account_name": "管理费用",
      "direction": "借",
      "amount": "1000.00",
      "explanation": "办公服务费"
    }
  ]
}
```

返回审核评分、评级、检查项状态、错误清单、审核建议和法规/准则引用。当前接口只做规则审核与错误定位，不输出最终审计意见。
