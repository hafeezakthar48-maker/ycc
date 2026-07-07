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

过账/反过账接口受 `voucher.post` 和 `voucher.unpost` 权限控制，并记录 `voucher.post` / `voucher.unpost` 审计日志。已关闭会计期间内的凭证不允许继续过账；关闭期间前如果同账套同期间仍有未过账凭证，会返回 `409`。当前 `post` 会生成正式分录并在凭证记录中返回 `journal_entry_id`，`unpost` 会生成冲销分录并返回 `journal_reversal_entry_id`。

```text
POST /api/v1/vouchers/center/import
GET /api/v1/vouchers/center/export/csv
POST /api/v1/vouchers/center/{voucher_id}/attachments
```

分别用于 JSON 批量导入、CSV 导出和附件上传记录。当前附件上传会生成电子会计档案文档索引，返回 `archive_document_id`、`sha256_hash`、`storage_status` 和 `ocr_status`；系统计算上传字节的 SHA-256 并保存元数据与可选文本摘录，不把原始二进制永久写入 SQLite，也不伪造 OCR 或官方验真结果。

当前凭证中心是工作流 MVP，使用本地 SQLite 保存演示凭证、账套标识、审核状态、过账状态、附件元数据和月度编号序列；服务重启后凭证仍保留。正式核算一期使用独立 SQLite 正式分录库保存 `journal_entry` / `journal_line`，账簿读模型优先基于正式分录生成总账、明细账和科目余额表；默认账套、跨境电商账套与会计期间状态用于一期关账控制，该库仍不执行完整期末结账、完整反结账或完整多账套核算。

## 电子会计档案 Phase 7

```text
GET /api/v1/accounting-archive/documents?account_set_id=default&period=2026-06
GET /api/v1/accounting-archive/documents/{archive_document_id}
POST /api/v1/accounting-archive/cases
GET /api/v1/accounting-archive/cases/{archive_case_id}/download
```

文档列表响应：

```json
{
  "total": 1,
  "documents": [
    {
      "archive_document_id": "arch_doc_...",
      "account_set_id": "default",
      "period": "2026-06",
      "source_type": "voucher",
      "source_id": "voucher-001",
      "document_type": "invoice",
      "filename": "invoice.txt",
      "content_type": "text/plain",
      "size": 12,
      "sha256_hash": "9adcc70a5f32964ef54c16a3f3e2138f3bfe85e88b12402b248e8f28a1b2a884",
      "storage_status": "metadata_only",
      "archive_status": "indexed",
      "ocr_status": "text_parsed",
      "verification_status": "pending_external",
      "retention_years": 30,
      "uploaded_by": "finance-user",
      "created_at": "2026-07-06T00:00:00+00:00"
    }
  ]
}
```

创建案卷请求：

```json
{
  "account_set_id": "default",
  "period": "2026-06",
  "case_type": "voucher",
  "title": "2026-06 凭证档案",
  "document_ids": ["arch_doc_..."],
  "created_by": "finance-manager"
}
```

归档包下载返回 ZIP，文件名形如 `accounting-archive-default-2026-06-voucher.zip`，内容包含 `manifest.json`、每个档案文档的元数据 JSON，以及可用的文本摘录文件。图片和 PDF 在未接入真实 OCR 引擎时返回 `ocr_status="engine_required"`；发票和银行回单在未接入外部验真服务前返回 `verification_status="pending_external"`；默认保管期限按档案类型设置，凭证、发票、回单、合同和报表当前按 30 年处理。

权限点：

- `archive.read`
- `archive.document.create`
- `archive.case.create`
- `archive.package.download`
- `archive.verification.update`

审计事件：

- `archive.document.list`
- `archive.document.get`
- `archive.document.create`
- `archive.case.create`
- `archive.package.download`
- `archive.verification.update`

当前归档 API 只提供档案索引、哈希校验、案卷清单和 ZIP 交换包，不覆盖 CA 签章、官方电子发票实时验真、对象存储 WORM、长期冷备、跨系统档案移交或档案销毁审批。

## 往来核算 Phase 8

```text
GET /api/v1/receivable-payable/balances?account_set_id=default&period=2026-06&open_item_type=receivable
GET /api/v1/receivable-payable/aging?account_set_id=default&period=2026-06&open_item_type=receivable&as_of_date=2026-06-30
POST /api/v1/receivable-payable/settlements
```

余额响应：

```json
{
  "account_set_id": "default",
  "period": "2026-06",
  "open_item_type": "receivable",
  "total_base_balance": 1000,
  "item_count": 1,
  "items": [
    {
      "counterparty_type": "customer",
      "counterparty_code": "CUST-SH-001",
      "counterparty_name": "上海客户",
      "open_item_type": "receivable",
      "currency": "CNY",
      "original_balance": 1000,
      "base_balance": 1000,
      "open_item_count": 1
    }
  ]
}
```

账龄响应：

```json
{
  "account_set_id": "default",
  "period": "2026-06",
  "open_item_type": "receivable",
  "as_of_date": "2026-06-30",
  "buckets": [
    { "bucket_code": "0-30", "day_from": 0, "day_to": 30, "amount": 1000, "open_item_count": 1 },
    { "bucket_code": "31-60", "day_from": 31, "day_to": 60, "amount": 0, "open_item_count": 0 },
    { "bucket_code": "61-90", "day_from": 61, "day_to": 90, "amount": 0, "open_item_count": 0 },
    { "bucket_code": "91-180", "day_from": 91, "day_to": 180, "amount": 0, "open_item_count": 0 },
    { "bucket_code": "181-365", "day_from": 181, "day_to": 365, "amount": 0, "open_item_count": 0 },
    { "bucket_code": "365+", "day_from": 366, "day_to": null, "amount": 0, "open_item_count": 0 }
  ],
  "items": [
    {
      "counterparty_type": "customer",
      "counterparty_code": "CUST-SH-001",
      "counterparty_name": "上海客户",
      "buckets": [
        { "bucket_code": "0-30", "day_from": 0, "day_to": 30, "amount": 1000, "open_item_count": 1 },
        { "bucket_code": "31-60", "day_from": 31, "day_to": 60, "amount": 0, "open_item_count": 0 },
        { "bucket_code": "61-90", "day_from": 61, "day_to": 90, "amount": 0, "open_item_count": 0 },
        { "bucket_code": "91-180", "day_from": 91, "day_to": 180, "amount": 0, "open_item_count": 0 },
        { "bucket_code": "181-365", "day_from": 181, "day_to": 365, "amount": 0, "open_item_count": 0 },
        { "bucket_code": "365+", "day_from": 366, "day_to": null, "amount": 0, "open_item_count": 0 }
      ],
      "total_base_balance": 1000
    }
  ],
  "total_base_balance": 1000
}
```

核销请求：

```json
{
  "account_set_id": "default",
  "period": "2026-06",
  "open_item_type": "receivable",
  "settlement_date": "2026-06-30",
  "counterparty_type": "customer",
  "counterparty_code": "CUST-SH-001",
  "payment_entry_id": "entry_payment_001",
  "settled_by": "finance-manager",
  "items": [
    {
      "open_item_id": "open_item_...",
      "source_line_id": "line_...",
      "settled_base_amount": 500
    }
  ]
}
```

应收未清项来自 `1122/1221` 且必须挂载客户维度；应付未清项来自 `2202/2241` 且必须挂载供应商维度。未清项和余额只基于正式已过账分录行、期间参数和核销记录生成，不从凭证摘要、报表快照或样例数据反推。账龄桶固定为 `0-30`、`31-60`、`61-90`、`91-180`、`181-365` 和 `365+`。

核销只追加 `CounterpartySettlement` 记录，支持部分核销和同一往来对象内多未清项核销，不改写历史正式分录；已关闭期间新增核销返回 `409`。坏账准备通过期间结账动作 `bad_debt_provision` 生成，当前默认规则为 `91-180` 计提 5%、`181-365` 计提 10%、`365+` 计提 50%，分录方向为借 `6701`、贷 `1231`。

权限点：

- `receivable_payable.read`
- `receivable_payable.settle`
- `receivable_payable.bad_debt`

审计事件：

- `receivable_payable.balance.read`
- `receivable_payable.aging.read`
- `receivable_payable.settle`
- `receivable_payable.bad_debt.provision`

当前往来 API 不覆盖销售订单、采购订单、合同台账、银行流水自动抓取、自动付款、信用额度审批、完整催收流程、预收预付复杂重分类或复杂坏账组合模型。

## 银行对账 Phase 9

```text
POST /api/v1/bank-reconciliation/statements/import
GET /api/v1/bank-reconciliation/matches?account_set_id=default&bank_account_id=bank-001&period=2026-06&minimum_score=80
POST /api/v1/bank-reconciliation/confirm
GET /api/v1/bank-reconciliation/statements?account_set_id=default&bank_account_id=bank-001&period=2026-06
```

导入银行流水请求：

```json
{
  "account_set_id": "default",
  "lines": [
    {
      "account_set_id": "default",
      "bank_account_id": "bank-001",
      "transaction_date": "2026-06-30",
      "direction": "inflow",
      "amount": "1200.00",
      "currency": "CNY",
      "counterparty_name": "上海客户A",
      "summary": "销售回款",
      "bank_reference": "B20260630001"
    }
  ]
}
```

导入响应返回 `imported_count`、`duplicate_count` 和已导入 `lines`。去重键为 `account_set_id + bank_account_id + bank_reference`。

匹配候选响应：

```json
{
  "account_set_id": "default",
  "bank_account_id": "bank-001",
  "period": "2026-06",
  "minimum_score": 80,
  "candidates": [
    {
      "statement_line_id": "bankline-...",
      "journal_entry_id": "je-...",
      "journal_line_id": "jl-...",
      "direction": "inflow",
      "score": 100,
      "reasons": ["金额一致", "日期一致", "摘要匹配"],
      "statement_date": "2026-06-30",
      "journal_date": "2026-06-30",
      "statement_amount": "1200.00",
      "journal_amount": "1200.00",
      "currency": "CNY",
      "counterparty_name": "上海客户A",
      "summary": "销售回款"
    }
  ]
}
```

匹配候选只读取正式已过账资金分录，科目范围为 `1001/1002/1012`。银行流入匹配资金借方，银行流出匹配资金贷方；当前评分规则为金额一致 60 分、日期一致 25 分、摘要匹配 15 分。

确认对账请求：

```json
{
  "account_set_id": "default",
  "bank_account_id": "bank-001",
  "period": "2026-06",
  "statement_line_ids": ["bankline-..."],
  "journal_line_ids": ["jl-..."],
  "confirmed_by": "treasury-user",
  "note": "月末回款对账"
}
```

确认记录返回 `reconciliation_id`、来源流水行、来源分录行、确认人、确认时间和可选 `settlement_ids`。确认只追加 `BankReconciliationMatch`；已关闭期间新增确认返回 `409`。如果请求体包含 `receivable_payable_settlement`，后端会透传给八期 `CounterpartySettlementCreate` 并创建应收应付核销记录。

银行余额调节表响应：

```json
{
  "account_set_id": "default",
  "bank_account_id": "bank-001",
  "period": "2026-06",
  "bank_balance": "1200.00",
  "book_balance": "1200.00",
  "bank_received_not_booked": "0.00",
  "bank_paid_not_booked": "0.00",
  "book_received_not_bank": "0.00",
  "book_paid_not_bank": "0.00",
  "adjusted_bank_balance": "1200.00",
  "adjusted_book_balance": "1200.00",
  "unmatched_statement_count": 0,
  "unmatched_journal_count": 0,
  "unmatched_statement_lines": [],
  "unmatched_journal_lines": []
}
```

权限点：

- `bank_reconciliation.read`
- `bank_reconciliation.import`
- `bank_reconciliation.match`
- `bank_reconciliation.confirm`

审计事件：

- `bank_reconciliation.statement.import`
- `bank_reconciliation.match.suggest`
- `bank_reconciliation.match.confirm`
- `bank_reconciliation.statement.read`

当前银行对账 API 不接真实网银，不保存网银登录凭据，不做银企直连签名、自动付款、银行回单官方验真、多币种换汇拆分对账或完整出纳复核流程。

## 正式会计核算引擎一期

```text
GET /api/v1/accounting/accounts?account_set_id=default
GET /api/v1/accounting/journal-entries?account_set_id=default&period=2026-06
GET /api/v1/accounting/journal-entries/{entry_id}
```

正式过账继续使用：

```text
POST /api/v1/vouchers/center/{voucher_id}/post
POST /api/v1/vouchers/center/{voucher_id}/unpost
```

`post` 会生成正式分录，`unpost` 会生成冲销分录。已关闭期间拒绝正式过账和反过账。正式核算读取接口支持 `X-Actor-Id` 请求头，非 `system` 调用方必须具备 `accounting.account.read` 或 `accounting.entry.read` 权限；成功或拒绝都会记录 `accounting.*` 审计日志。

## 多币种核算二期

```text
GET /api/v1/accounting/currencies
GET /api/v1/accounting/exchange-rates?account_set_id=default
POST /api/v1/accounting/exchange-rates
POST /api/v1/accounting/journal-entries
```

外币分录行必须同时提交 `currency`、`original_amount`、`exchange_rate` 和 `base_amount`，后端会校验 `original_amount * exchange_rate == base_amount`。当分录行币种不是账套本位币时，后端还会校验该日期、该账套下的汇率表记录。汇率维护接口受 `accounting.exchange_rate.read` / `accounting.exchange_rate.write` 权限控制；正式分录创建接口受 `accounting.entry.post` 权限控制。

## 辅助核算维度三期

```text
GET /api/v1/accounting/dimensions?account_set_id=default
GET /api/v1/accounting/dimensions?account_set_id=default&dimension_type=customer
POST /api/v1/accounting/dimensions
GET /api/v1/ledger/detail?period=2026-06&account_code=1122&dimension_type=customer&dimension_code=CUST-SH-001
```

正式分录行支持：

```json
{
  "dimensions": [
    { "dimension_type": "customer", "dimension_code": "CUST-SH-001" }
  ]
}
```

后端会校验维度主数据存在且启用，并在正式分录行中保存维度名称快照。

## 期间结账引擎四期

```text
POST /api/v1/period-close/runs
GET /api/v1/period-close/runs?account_set_id=default&period=2026-06
POST /api/v1/period-close/checks
POST /api/v1/period-close/actions/preview
POST /api/v1/period-close/actions/generate
POST /api/v1/period-close/close
POST /api/v1/period-close/reopen
```

发起或查询结账运行：

```json
{
  "account_set_id": "default",
  "period": "2026-06",
  "close_type": "monthly",
  "started_by": "u-finance-manager"
}
```

运行结账检查：

```json
{
  "account_set_id": "default",
  "period": "2026-06",
  "close_type": "monthly"
}
```

生成或预览期末动作：

```json
{
  "account_set_id": "default",
  "period": "2026-06",
  "close_type": "monthly",
  "actions": [
    "fixed_asset_depreciation",
    "payroll_accrual",
    "tax_accrual",
    "tax_surtax_accrual",
    "accrual_amortization_posting",
    "fx_revaluation",
    "bad_debt_provision",
    "inventory_cost_rollforward",
    "profit_loss_carryforward"
  ],
  "tax_accrual_rules": [
    {
      "tax_name": "增值税",
      "expense_account_code": "6403",
      "liability_account_code": "2221",
      "amount": 3600
    }
  ]
}
```

关闭或重开期间：

```json
{
  "account_set_id": "default",
  "period": "2026-06"
}
```

生成接口会先运行检查清单，存在阻断项时返回 `409`；`preview=true` 时只返回将要生成的动作结果，不写入正式分录。实际生成时会按来源键幂等处理，同一账套、期间、动作和来源重复执行不会重复过账。
外币期末重估只生成本位币 CNY 调整分录，原币金额保持不变；坏账准备按往来账龄规则生成借 `6701`、贷 `1231` 的正式分录；存货成本结转动作汇总当期已生成的销售出库成本分录；附加税计提动作按当期未交增值税结转金额生成借 `6403`、贷 `222103` 的正式分录；预提摊销动作按活跃核算计划生成本期幂等分录；损益结转按月结转至 `4103 本年利润`，年结再转入 `4104 利润分配-未分配利润`。
期间结账接口支持 `X-Actor-Id` 请求头，分别受 `period_close.view`、`period_close.check`、`period_close.generate`、`period_close.close` 和 `period_close.reopen` 权限控制，并记录 `period_close.run_started`、`period_close.runs_viewed`、`period_close.checks_completed`、`period_close.actions_previewed`、`period_close.actions_generated`、`period_close.period_closed` 和 `period_close.period_reopened` 审计日志；坏账准备动作还会记录 `receivable_payable.bad_debt.provision`。

## 账簿读模型 MVP

```text
GET /api/v1/ledger/general?period=2026-06
GET /api/v1/ledger/general?period=2026-06&account_set_id=cross_border
```

返回指定期间、指定账套的总账视图，包括来源、凭证数、分录数、借方合计、贷方合计、平衡状态和科目汇总列表。存在正式分录时 `source=formal_journal_entries`；无正式分录时回退已审核凭证，`source=mvp_voucher_workflow`。`account_set_id` 不传时默认为 `default`。

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

当前账簿接口优先读取正式分录；无正式分录时读取指定账套内 `reviewed` 状态的凭证中心记录，不读取草稿凭证。该能力仍不替代完整财务系统中的期末结账、完整反结账、完整账套隔离和账簿锁定流程。期间关闭是一控制边界，用于阻止关闭期间继续正式过账。
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

当前固定资产台账是内存 MVP，服务重启后演示资产会重置；台账接口只维护资产生命周期状态，正式资本化、正式折旧、减值和处置分录由固定资产正式核算 Phase 10 接口生成。台账接口支持 `X-Actor-Id` 请求头，读取、新增、折旧、处置和盘点分别受 `fixed_asset.read`、`fixed_asset.write`、`fixed_asset.depreciate`、`fixed_asset.dispose`、`fixed_asset.inventory` 权限控制，并记录 `fixed_asset.list`、`fixed_asset.create`、`fixed_asset.depreciation.run`、`fixed_asset.inventory`、`fixed_asset.dispose` 和 `fixed_asset.sell` 审计日志。

### 固定资产正式核算 Phase 10

```text
GET /api/v1/fixed-asset-accounting/cards?account_set_id=default
POST /api/v1/fixed-asset-accounting/capitalize
POST /api/v1/fixed-asset-accounting/depreciation
POST /api/v1/fixed-asset-accounting/impairment
POST /api/v1/fixed-asset-accounting/disposal
```

资本化请求：

```json
{
  "account_set_id": "default",
  "asset_id": "asset-001",
  "period": "2026-06",
  "credit_account_code": "2202"
}
```

折旧正式过账请求：

```json
{
  "account_set_id": "default",
  "period": "2026-06"
}
```

减值请求：

```json
{
  "account_set_id": "default",
  "asset_id": "asset-001",
  "period": "2026-06",
  "amount": "5000.00"
}
```

正式处置请求：

```json
{
  "account_set_id": "default",
  "asset_id": "asset-001",
  "period": "2026-06",
  "disposal_date": "2026-06-30",
  "proceeds_amount": "118000.00",
  "proceeds_account_code": "1002",
  "reason": "更新换代"
}
```

正式卡片接口返回资产台账字段、正式核算状态、资本化分录 ID、最近折旧分录 ID、减值准备金额、处置分录 ID 和正式净值。正式核算分录使用 `asset` 辅助核算维度追溯资产，核心科目包括 `1601 固定资产`、`1602 累计折旧`、`1603 固定资产减值准备`、`1606 固定资产清理`、`6602 管理费用`、`6701 资产减值损失`、`6301 营业外收入`、`6711 营业外支出` 以及处置或资本化对方科目。

正式分录来源键：

```text
fixed_asset_capitalization:{account_set_id}:{asset_id}
fixed_asset_depreciation:{account_set_id}:{period}:{asset_id}
fixed_asset_impairment:{account_set_id}:{period}:{asset_id}
fixed_asset_disposal:{account_set_id}:{period}:{asset_id}
```

接口支持 `X-Actor-Id` 请求头。读取卡片受 `fixed_asset_accounting.read` 控制，资本化和折旧受 `fixed_asset_accounting.post` 控制，减值受 `fixed_asset_accounting.impair` 控制，处置受 `fixed_asset_accounting.dispose` 控制；成功或拒绝都会记录 `fixed_asset_accounting.card.read`、`fixed_asset_accounting.capitalize`、`fixed_asset_accounting.depreciation.post`、`fixed_asset_accounting.impairment.post`、`fixed_asset_accounting.disposal.post` 审计事件。已关闭期间拒绝新增正式资本化、折旧、减值和处置分录；同一来源键重复调用返回既有正式分录，避免重复入账。当前不提供固定资产卡片附件、复杂融资租赁、资产评估接口、税会差异自动申报、集团跨法人调拨或完整资产清查审批流程。

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

## 薪酬正式核算 Phase 11

```text
GET /api/v1/payroll-accounting/batches?account_set_id=default&period=2026-06
POST /api/v1/payroll-accounting/accruals
POST /api/v1/payroll-accounting/payments
POST /api/v1/payroll-accounting/liability-payments
```

批次查询返回指定账套和期间的工资批次正式核算状态：

```json
{
  "account_set_id": "default",
  "period": "2026-06",
  "total": 1,
  "batches": [
    {
      "payroll_batch_id": "PAY-2026-06",
      "status": "paid",
      "accrual_journal_entry_id": "je-xxx",
      "payment_journal_entry_id": "je-yyy",
      "liability_payment_status": "remitted",
      "liability_payment_journal_entry_id": "je-zzz"
    }
  ]
}
```

计提请求：

```json
{
  "account_set_id": "default",
  "period": "2026-06",
  "payroll_batch_id": "PAY-2026-06"
}
```

发放请求：

```json
{
  "account_set_id": "default",
  "period": "2026-06",
  "payroll_batch_id": "PAY-2026-06",
  "bank_account_code": "1002"
}
```

缴纳请求：

```json
{
  "account_set_id": "default",
  "period": "2026-07",
  "payroll_batch_id": "PAY-2026-06",
  "bank_account_code": "1002"
}
```

来源键分别为 `payroll_accrual:{account_set_id}:{period}:{payroll_batch_id}`、`payroll_payment:{account_set_id}:{period}:{payroll_batch_id}` 和 `payroll_liability_payment:{account_set_id}:{payment_period}:{payroll_batch_id}`。同一来源键重复调用返回既有正式分录；已关闭期间拒绝新增计提、发放或缴纳分录。接口支持 `X-Actor-Id` 请求头，分别受 `payroll_accounting.read`、`payroll_accounting.accrue`、`payroll_accounting.pay`、`payroll_accounting.remit` 权限控制，并记录 `payroll_accounting.batch.read`、`payroll_accounting.accrual.post`、`payroll_accounting.payment.post`、`payroll_accounting.liability_payment.post` 审计事件。

当前不接真实银行代发，不保存身份证号、银行卡号或手机号明文，不发送工资条，不做累计预扣预缴完整申报。

## 存货与成本核算 Phase 12

```text
GET /api/v1/inventory-accounting/balances?account_set_id=default
POST /api/v1/inventory-accounting/purchase-receipts
POST /api/v1/inventory-accounting/sales-issues
POST /api/v1/inventory-accounting/impairments
POST /api/v1/inventory-accounting/count-variances
```

余额查询返回账套下 SKU/仓库余额和存货移动流水：

```json
{
  "account_set_id": "default",
  "total_balances": 1,
  "total_movements": 2,
  "balances": [
    {
      "sku_id": "SKU-001",
      "warehouse_id": "WH-SH",
      "quantity": "7.0000",
      "amount": "700.00",
      "moving_average_cost": "100.00"
    }
  ],
  "movements": [
    {
      "movement_type": "purchase_receipt",
      "quantity": "10.0000",
      "amount": "1000.00",
      "journal_entry_id": "je-xxx"
    }
  ]
}
```

采购入库请求：

```json
{
  "account_set_id": "default",
  "sku_id": "SKU-001",
  "warehouse_id": "WH-SH",
  "period": "2026-06",
  "quantity": "10",
  "amount": "1000.00",
  "supplier_id": "SUP-001"
}
```

销售出库请求：

```json
{
  "account_set_id": "default",
  "sku_id": "SKU-001",
  "warehouse_id": "WH-SH",
  "period": "2026-06",
  "quantity": "3"
}
```

跌价准备请求：

```json
{
  "account_set_id": "default",
  "sku_id": "SKU-001",
  "period": "2026-06",
  "amount": "500.00"
}
```

盘点差异请求：

```json
{
  "account_set_id": "default",
  "sku_id": "SKU-001",
  "warehouse_id": "WH-SH",
  "period": "2026-06",
  "actual_quantity": "6",
  "approved_by": "controller",
  "approved_at": "2026-06-30T10:00:00Z"
}
```

采购入库借 `1405` 贷 `2202`；销售出库借 `6401` 贷 `1405`；跌价准备借 `6701` 贷 `1471`；盘盈盘亏先进入 `1901 待处理财产损溢`。来源键分别为 `inventory_receipt:{account_set_id}:{period}:{sku_id}:{supplier_id}`、`inventory_sales_issue:{account_set_id}:{period}:{sku_id}:{warehouse_id}:{sequence}`、`inventory_impairment:{account_set_id}:{period}:{sku_id}` 和 `inventory_count_variance:{account_set_id}:{period}:{sku_id}:{warehouse_id}`。接口支持 `X-Actor-Id` 请求头，分别受 `inventory_accounting.read`、`inventory_accounting.receipt`、`inventory_accounting.issue`、`inventory_accounting.impair` 和 `inventory_accounting.count` 权限控制，并记录 `inventory_accounting.*` 审计事件。

当前库存台账为内存 MVP，用于验证正式分录和移动加权成本；已关闭期间拒绝新增存货正式分录，不接 WMS 实时库存、批次保质期、生产 BOM 或跨境电商平台真实订单。

## 税务核算与申报底稿 Phase 13

```text
GET /api/v1/tax-accounting/vat-ledger?account_set_id=default&period=2026-06
GET /api/v1/tax-accounting/filing-worksheet?account_set_id=default&period=2026-06
POST /api/v1/tax-accounting/unpaid-vat-transfer
POST /api/v1/tax-accounting/surtax-accrual
POST /api/v1/tax-accounting/income-tax-accrual
POST /api/v1/tax-accounting/tax-payments
```

增值税台账返回正式分录来源、发票号、税基、税额和方向：

```json
{
  "account_set_id": "default",
  "period": "2026-06",
  "total": 2,
  "lines": [
    {
      "tax_direction": "output",
      "invoice_no": "INV-001",
      "tax_base": "1000.00",
      "tax_amount": "130.00",
      "counterparty_id": "CUST-001",
      "source_journal_entry_id": "je-001"
    }
  ]
}
```

申报底稿返回销项、进项、进项转出、应交增值税、附加税和企业所得税：

```json
{
  "account_set_id": "default",
  "period": "2026-06",
  "output_vat": "130.00",
  "input_vat": "104.00",
  "input_transfer_out": "0.00",
  "vat_payable": "26.00",
  "surtax_payable": "3.12",
  "income_tax_payable": "5000.00"
}
```

未交增值税结转和企业所得税计提请求：

```json
{
  "account_set_id": "default",
  "period": "2026-06",
  "amount": "26.00"
}
```

附加税计提请求：

```json
{
  "account_set_id": "default",
  "period": "2026-06",
  "vat_payable": "26.00",
  "urban_maintenance_rate": "0.07",
  "education_rate": "0.03",
  "local_education_rate": "0.02"
}
```

纳税支付请求：

```json
{
  "account_set_id": "default",
  "period": "2026-07",
  "tax_account_code": "222102",
  "amount": "26.00",
  "bank_account_code": "1002"
}
```

未交增值税结转借 `22210103` 贷 `222102`；附加税计提借 `6403` 贷 `222103`；所得税计提借 `6801` 贷 `222104`；纳税支付借税费明细科目、贷银行存款。来源键分别为 `tax_unpaid_vat_transfer:{account_set_id}:{period}`、`tax_surtax_accrual:{account_set_id}:{period}`、`tax_income_tax_accrual:{account_set_id}:{period}` 和 `tax_payment:{account_set_id}:{period}:{tax_account_code}`。接口支持 `X-Actor-Id` 请求头，分别受 `tax_accounting.read`、`tax_accounting.accrue`、`tax_accounting.pay` 权限控制，并记录 `tax_accounting.vat_ledger.read`、`tax_accounting.worksheet.read`、`tax_accounting.vat.transfer`、`tax_accounting.surtax.accrue`、`tax_accounting.income_tax.accrue` 和 `tax_accounting.payment.post` 审计事件。

当前申报底稿只用于计算和复核，不接税局真实申报接口，不自动做抵扣认证，不做真实发票验真，不处理复杂税收优惠备案，不替代税务师判断；已关闭期间拒绝新增税费计提、结转和缴款正式分录。

## 预提摊销与融资利息 Phase 14

```text
GET /api/v1/accrual-amortization/schedules?account_set_id=default
POST /api/v1/accrual-amortization/schedules
POST /api/v1/accrual-amortization/schedules/{schedule_code}/post
POST /api/v1/accrual-amortization/loan-interest
```

计划列表返回核算计划和借款计划：

```json
{
  "account_set_id": "default",
  "total_schedules": 1,
  "total_loans": 1,
  "schedules": [
    {
      "account_set_id": "default",
      "schedule_code": "AMORT-2026-001",
      "schedule_type": "prepaid_amortization",
      "start_period": "2026-06",
      "end_period": "2026-08",
      "total_amount": "12000.00",
      "debit_account_code": "6602",
      "credit_account_code": "1801",
      "department_id": null,
      "project_id": null,
      "status": "active",
      "posted_periods": ["2026-06"]
    }
  ],
  "loan_schedules": [
    {
      "account_set_id": "default",
      "loan_code": "LOAN-2026-001",
      "principal": "1000000.00",
      "annual_rate": "0.036000",
      "start_period": "2026-06",
      "end_period": "2026-12",
      "loan_account_code": "2001",
      "interest_expense_account_code": "6603",
      "interest_payable_account_code": "2231",
      "status": "active",
      "interest_posted_periods": ["2026-06"]
    }
  ]
}
```

创建预付摊销、预提费用或递延收入计划：

```json
{
  "account_set_id": "default",
  "schedule_code": "AMORT-2026-001",
  "schedule_type": "prepaid_amortization",
  "start_period": "2026-06",
  "end_period": "2026-08",
  "total_amount": "12000.00",
  "debit_account_code": "6602",
  "credit_account_code": "1801",
  "department_id": "D-FIN",
  "project_id": null
}
```

生成指定期间计划分录：

```json
{
  "account_set_id": "default",
  "period": "2026-06"
}
```

借款利息计提请求会在借款计划不存在时先创建计划，再按期间生成利息计提：

```json
{
  "account_set_id": "default",
  "loan_code": "LOAN-2026-001",
  "period": "2026-06",
  "principal": "1000000.00",
  "annual_rate": "0.036000",
  "start_period": "2026-06",
  "end_period": "2026-12",
  "loan_account_code": "2001",
  "interest_expense_account_code": "6603",
  "interest_payable_account_code": "2231"
}
```

月度摊销金额按计划总金额和起止期间平均分摊，尾差由最后一期吸收。计划过账来源键为 `schedule_posting:{account_set_id}:{period}:{schedule_code}`；借款利息计提来源键为 `loan_interest_accrual:{account_set_id}:{period}:{loan_code}`，重复调用返回既有正式分录，已关闭期间拒绝新增分录。期间结账动作 `accrual_amortization_posting` 会按活跃计划批量生成本期分录。

接口支持 `X-Actor-Id` 请求头，分别受 `accrual_amortization.read`、`accrual_amortization.write` 和 `accrual_amortization.post` 权限控制，并记录 `accrual_amortization.schedule.read`、`accrual_amortization.schedule.create`、`accrual_amortization.schedule.post` 和 `accrual_amortization.loan_interest.post` 审计事件。当前计划表为内存 MVP，不做复杂金融工具公允价值、实际利率摊余成本完整模型、租赁准则全流程或合同收入五步法自动判断。

## 合并报表与内部抵销 Phase 15

```text
GET /api/v1/consolidation/groups
POST /api/v1/consolidation/groups
GET /api/v1/consolidation/reporting-package?account_set_id=default&period=2026-06
GET /api/v1/consolidation/eliminations?group_id=group-001&period=2026-06
POST /api/v1/consolidation/eliminations/rebuild
GET /api/v1/consolidation/statements?group_id=group-001&period=2026-06
```

创建合并集团：

```json
{
  "group_id": "group-001",
  "group_name": "中国财务AI集团",
  "entities": [
    {
      "consolidation_group_id": "group-001",
      "account_set_id": "default",
      "entity_name": "母公司",
      "ownership_percentage": "1.000000",
      "consolidation_method": "full"
    },
    {
      "consolidation_group_id": "group-001",
      "account_set_id": "cross_border",
      "entity_name": "子公司A",
      "ownership_percentage": "0.800000",
      "consolidation_method": "proportionate"
    }
  ]
}
```

单体报表包返回指定账套的资产负债表、利润表和现金流量表；合并层保留原始报表来源，不修改单体正式分录。

重建抵销请求：

```json
{
  "group_id": "group-001",
  "period": "2026-06",
  "intercompany_balance_amount": "50000.00",
  "intercompany_revenue_amount": "80000.00",
  "intercompany_cost_amount": "60000.00",
  "ending_internal_inventory_amount": "100000.00",
  "internal_gross_margin_rate": "0.200000",
  "investment_amount": "800000.00",
  "subsidiary_equity_amount": "1000000.00",
  "ownership_percentage": "0.800000"
}
```

抵销列表返回：

```json
{
  "group_id": "group-001",
  "period": "2026-06",
  "total_eliminations": 4,
  "eliminations": [
    {
      "elimination_type": "intercompany_balance",
      "debit_account_code": "2202",
      "credit_account_code": "1122",
      "amount": "50000.00",
      "explanation": "抵销内部应收应付"
    }
  ]
}
```

合并报表返回合并资产负债表、合并利润表、合并现金流量表、少数股东权益、少数股东损益和抵销分录数量。抵销类型包括 `intercompany_balance`、`intercompany_revenue_cost`、`unrealized_profit` 和 `investment_equity`。

接口支持 `X-Actor-Id` 请求头，分别受 `consolidation.read`、`consolidation.write` 和 `consolidation.rebuild` 权限控制，并记录 `consolidation.group.read`、`consolidation.group.write`、`consolidation.package.read`、`consolidation.elimination.rebuild` 和 `consolidation.statement.read` 审计事件。当前合并范围和抵销底稿为内存 MVP，不做复杂股权购买法追溯、商誉减值完整评估模型、境外准则转换或审计合并底稿替代。

## 财务报表自动生成 MVP

```text
POST /api/v1/financial-statements/generate
GET /api/v1/financial-statements/mapping-sets/default?account_set_id=default
POST /api/v1/financial-statements/snapshots
GET /api/v1/financial-statements/snapshots?account_set_id=default&period=2026-06
POST /api/v1/financial-statements/snapshots/{snapshot_id}/lock
GET /api/v1/financial-statements/snapshots/{snapshot_id}/export/xlsx
GET /api/v1/financial-statements/snapshots/{snapshot_id}/export/pdf
```

请求：

```json
{
  "period": "2026-06",
  "account_set_id": "default",
  "operator": "财务主管",
  "include_trace": true
}
```

返回：

- `balance_sheet`：资产负债表，包含货币资金、应收账款、存货、固定资产、短期借款、应付账款、应交税费、所有者权益、资产合计、负债合计和负债权益平衡状态。
- `income_statement`：利润表，包含营业收入、营业成本、期间费用、利润总额和净利润。
- `cash_flow_statement`：现金流量表，包含经营、投资、筹资活动现金流量净额和现金净增加额。
- `equity_statement`：所有者权益变动表，包含期初权益、本期净利润、权益调整和期末权益。
- `management_summary`：管理报表摘要，包含净利率、资产负债率、现金流利润比、管理亮点和风险提示。
- `mapping_set_id`：本次报表使用的映射集。
- `trace_items`：报表项目追溯，包含项目编码、规则、来源科目、现金流项目、公式和金额。
- `validation_items`：结构化校验结果，包含资产负债表恒等式、样例数据回退和现金流项目推断 warning。

默认映射集接口返回：

```json
{
  "mapping_set": {
    "mapping_set_id": "stmtmap_default_default",
    "mapping_set_name": "中国企业会计准则通用报表映射"
  },
  "rules": [
    {
      "line_code": "BS-CASH",
      "line_name": "货币资金",
      "source_type": "account_balance",
      "account_prefixes": ["1001", "1002"]
    }
  ]
}
```

当前报表映射规则：资产负债表取期末余额；利润表取期间发生额；现金流量表优先读取分录行 `cash_flow_item_code`，缺失时按现金科目和对方科目推断并返回 warning；所有者权益变动表取期初权益、本期净利润、利润分配和期末权益。

创建快照请求：

```json
{
  "period": "2026-06",
  "account_set_id": "default",
  "operator": "财务主管",
  "created_by": "finance-user"
}
```

快照返回 `snapshot_id`、`version`、`content_hash`、`validation_status`、`archive_status`、`locked`、`created_at` 和完整 `bundle`。同一账套同一期间重复创建会生成递增版本，不覆盖既有快照。样例数据来源快照标记为 `demo_only`。

锁定快照请求：

```json
{ "locked_by": "finance-manager" }
```

锁定后返回更新后的快照，记录 `locked_by` 和 `locked_at`。导出接口返回二进制文件响应，`xlsx` 的 `content-type` 为 `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`，文件包含四张标准报表、校验结果和追溯明细；`pdf` 返回轻量归档摘要。

接口支持 `X-Actor-Id` 请求头，分别受 `statement.generate`、`statement.validate`、`statement.mapping.view`、`statement.mapping.manage`、`statement.snapshot.create`、`statement.snapshot.lock`、`statement.archive.view` 和 `statement.export` 权限控制，并记录 `statement.generate`、`statement.mapping.view`、`statement.mapping.update`、`statement.snapshot.create`、`statement.snapshot.lock`、`statement.archive.view` 和 `statement.export` 审计日志。

生成接口优先基于指定账套、指定期间的正式分录生成报表；当前账套无正式分录时回退已审核凭证，无已审核凭证时回退使用内置样例经营数据生成演示报表。当前 MVP 不覆盖合并报表、复杂金融工具、长期股权投资、递延所得税、现金流量表补充资料、附注披露或正式申报报表。
生成接口支持 `X-Actor-Id` 请求头，非 `system` 调用方必须具备 `statement.generate` 权限；快照和导出接口按上文权限点控制，成功或权限不足都会记录对应审计日志。

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
## 正式核算上线治理 Phase 16

```text
GET /api/v1/accounting-governance/integrity-checks?account_set_id=default&period=2026-06
POST /api/v1/accounting-governance/migration-preview
POST /api/v1/accounting-governance/migration-apply
POST /api/v1/accounting-governance/backups
POST /api/v1/accounting-governance/restore-rehearsals
GET /api/v1/accounting-governance/permission-matrix
GET /api/v1/accounting-governance/go-live-gate?account_set_id=default&period=2026-06
```

权限点：

- `accounting_governance.read`
- `accounting_migration.preview`
- `accounting_migration.apply`
- `accounting_backup.create`
- `accounting_governance.approve_go_live`

审计事件：

- `accounting_governance.integrity.read`
- `accounting_governance.migration.preview`
- `accounting_governance.migration.apply`
- `accounting_governance.backup.create`
- `accounting_governance.restore.rehearsal`
- `accounting_governance.permission_matrix.read`
- `accounting_governance.go_live_gate.read`
