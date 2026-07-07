# China Finance AI Assistant

## Phase 16 正式核算上线治理

本阶段新增正式核算上线治理层，覆盖完整性校验、MVP 凭证迁移 dry-run、受控迁移 apply、备份清单、恢复演练、权限矩阵和上线门禁。后端入口为 `/api/v1/accounting-governance`，前端 AI 财务中心新增“正式核算上线治理”面板，详细操作见 [正式核算上线治理清单](docs/formal-accounting-go-live-checklist.md)。

面向中国企业财务经理的经营分析与风险预警驾驶舱 MVP。

产品长期形态为 China Finance AI OS，完整 FRD V1.0 见 [docs/03-frd-v1.0.md](docs/03-frd-v1.0.md)。当前代码库先实现其中的 MVP 闭环能力。

第一版使用内置示例财务数据，支持：

- AI 首页 V1.0：经营概况、利润、现金流、库存、税务和 AI 今日提示
- 经营总览
- 利润、收入、成本趋势分析
- 费用结构分析
- 现金流分析
- 风险预警
- AI 经营分析报告草稿
- Excel / WPS 表格导入
- 标准财务 Excel 模板下载
- 手动填写多期报表数据并一键分析
- AI 报告导出 Word / PDF
- 电商利润分析：GMV、退款、成本、投放、平台费、物流和净利润测算
- AI 财务问答：基于本地法规卡片返回答案、引用依据、检查清单和人工复核提示
- 财税法规库 RAG 底座：结构化政策文档、关键词检索、片段命中、来源链接和状态标记
- OCR 发票识别 MVP：支持粘贴 OCR 文本或上传 `.txt` 文本文件，提取发票号码、购销方税号、金额、税额和价税合计，并给出基础合规风险提示
- 凭证中心 MVP：支持新增、修改、审核、反审核、过账、反过账、自动编号、JSON 批量导入、CSV 导出、附件上传记录、AI 凭证错误检查、轻量多账套隔离、账套期间状态和账簿只读视图
- 正式会计核算引擎一期：已审核凭证可正式过账为不可变会计分录，账簿和财务报表优先读取正式分录来源，反过账通过冲销分录保留审计轨迹
- 多币种核算二期：支持币种清单、手工维护汇率、外币正式分录、本位币折算、原币明细账展示和本位币财务报表摘要
- 辅助核算维度三期：正式分录行支持客户、供应商、员工、部门、项目、资产、平台和 SKU 维度，明细账可展示并按维度过滤
- 固定资产台账 MVP：支持新增资产、直线法自动折旧、报废、出售、盘点、账套隔离和审计日志
- 固定资产正式核算 Phase 10：基于固定资产台账生成资本化、逐资产折旧、减值准备和清理处置正式分录，支持正式卡片追溯和处置损益
- 工资管理 MVP：支持工资计算、社保、公积金、个税、实发工资、企业成本和部门工资分析
- 薪酬正式核算 Phase 11：基于工资计算批次生成工资计提、工资发放、个税与社保公积金缴纳正式分录，并展示批次入账状态
- 存货与成本核算 Phase 12：支持 SKU/仓库库存余额、采购入库、移动加权平均成本、销售出库成本结转、存货跌价准备和盘点差异正式分录
- 税务核算与申报底稿 Phase 13：从正式分录生成增值税台账和申报底稿，支持未交增值税结转、附加税计提、企业所得税计提和纳税支付正式分录
- 预提摊销与融资利息 Phase 14：支持预付摊销、预提费用、递延收入和借款利息计划，按期间生成幂等正式分录并接入期间结账
- 合并报表与内部抵销 Phase 15：支持合并集团范围、单体报表包、内部往来/交易/未实现利润/投资权益抵销和少数股东权益展示
- 财务报表自动生成 MVP：支持资产负债表、利润表、现金流量表、所有者权益变动表、管理报表摘要、快照归档和 Excel/PDF 导出
- 电子会计档案 Phase 7：凭证附件生成档案文档索引，记录 SHA-256、OCR 状态、验真状态、保管期限，并支持创建案卷和下载归档 ZIP
- 往来核算 Phase 8：基于正式分录和客户/供应商辅助维度生成应收应付未清项、余额、账龄分析、部分核销和坏账准备期末动作
- 银行对账 Phase 9：支持银行流水导入去重、资金分录匹配候选、人工确认对账、银行余额调节表和收付款往来核销联动
- AI 凭证草稿：支持费用采购、库存采购、销售收入三类场景，自动生成借贷分录草稿、借贷平衡检查、风险提示和法规引用
- AI 自动审核：审核凭证分录、发票号码、摘要、交易对方、价税勾稽、借贷平衡和增值税科目方向，输出评分、评级、错误清单和整改建议

第一版支持先下载标准模板，再上传 `.xlsx` / `.xlsm` 分析；WPS 表格请先另存为 `.xlsx`。发票图片 / PDF 上传入口已预留，但当前本地环境未内置真实 OCR 引擎，系统会明确提示需接入 OCR 服务，不会伪造图片或 PDF 识别结果。凭证中心当前使用 SQLite 持久化工作流库保存演示凭证、审核状态、过账状态、账套标识、附件元数据和月度编号序列；正式核算一期已新增独立 SQLite 正式分录库，已审核凭证过账会生成 `journal_entry` / `journal_line`，账簿和财务报表优先读取正式分录来源，无正式分录时再回退 MVP 凭证工作流或样例经营数据。电子会计档案当前只保存文档索引、哈希、可选文本摘录和案卷清单，不把原始二进制永久写入数据库，不提供 CA 签章、官方验真或长期冷备。往来核算当前只以正式分录和客户/供应商辅助维度为来源，不从摘要或报表缓存反推；核销只记录未清项匹配关系，不改写历史正式分录。银行对账当前以导入银行流水和正式资金分录为来源，确认记录只追加，不修改银行流水或正式分录。固定资产台账仍为内存 MVP，用于验证资产生命周期、折旧和盘点流程；Phase 10 已将资本化、折旧、减值和处置接入正式分录与 `asset` 辅助维度，正式卡片可追溯来源分录，但仍不提供固定资产卡片附件、复杂融资租赁、资产评估接口、税会差异自动申报或集团跨法人调拨。工资管理当前为简化计算 MVP，用于验证工资、社保、公积金、个税和人工成本分析流程；Phase 11 已将工资批次计提、发放和薪酬相关款项缴纳接入正式分录，但仍不接真实银行代发、工资条发送或个税正式申报。存货核算当前以内存库存台账和正式分录配合验证 SKU/仓库余额、移动加权成本、销售成本结转、跌价准备和盘点差异，不接 WMS 实时库存、批次保质期、生产 BOM 或跨境平台真实订单。税务核算当前以正式分录为来源生成增值税台账和申报底稿，并生成税费结转、计提和缴款正式分录；不接税局直连申报，不自动做抵扣认证，不做真实发票验真，不处理复杂税收优惠备案，也不替代税务师判断。财务报表当前为单账套、单期间生成 MVP，用于验证报表取数和管理摘要，不替代正式财务报表编制与披露。自动审核只做规则提示和风险定位，不构成最终审计意见。暂不支持 WPS 原生 `.et`、旧版 `.xls`、真实网银直连、自动付款、自动申报税务、每日实时政策同步或自动失效判断。

预提摊销与融资利息当前以内存计划表驱动正式分录生成，用于验证月度摊销、预提、递延收入和借款利息计提流程；不做复杂金融工具公允价值、实际利率摊余成本完整模型、租赁准则全流程或合同收入五步法自动判断。

合并报表当前以内存合并范围和抵销工作底稿验证多账套合并流程，抵销分录只存在于合并层，不回写单体账套正式分录；暂不做复杂股权购买法追溯、商誉减值完整评估、境外准则转换或审计定稿替代。

## OCR 发票识别

当前 OCR 模块支持：

- 粘贴 OCR 文本或手动录入发票文本。
- 上传 `.txt` 发票文本文件并解析。
- 提取发票类型、发票代码、发票号码、开票日期、购买方、销售方、金额、税额、价税合计。
- 检查发票号码缺失、销售方纳税人识别号缺失、价税合计勾稽异常。
- 引用本地法规库中的《中华人民共和国发票管理办法》来源信息。

图片和 PDF 发票需要接入本地 OCR 引擎或第三方 OCR 服务后才能真实识别。

## AI 凭证草稿

当前凭证模块支持：

- 费用采购：借记管理费用、进项税额，贷记应付账款或银行存款。
- 库存采购：借记库存商品、进项税额，贷记应付账款或银行存款。
- 销售收入：借记应收账款或银行存款，贷记主营业务收入、销项税额。
- 自动计算借方合计、贷方合计和平衡状态。
- 检查价税合计与金额税额不一致、借贷不平衡等风险。
- 输出复核建议和法规/准则引用。

本模块是自动记账的前置能力，只能作为财务人员制单参考，不能直接作为正式入账结果。

## 凭证中心 MVP

当前凭证中心支持：

- 新增、修改、审核和反审核凭证。
- 按凭证月份自动生成 `记-YYYYMM-0001` 格式编号。
- 录入摘要、交易对方、发票号码、金额、税额、价税合计和分录行。
- 自动调用 AI 自动审核规则，检查借贷平衡、价税勾稽、基础字段和税额科目方向。
- JSON 批量导入凭证、CSV 导出凭证列表。
- 上传凭证附件并记录附件名称、类型、大小和 OCR 接入状态。
- 按账套保存凭证，当前内置 `default` 和 `cross_border` 两个账套。
- 将已审核凭证标记为过账或反过账；会计期间关闭前必须没有未过账凭证，关闭后禁止继续过账。

当前实现保留凭证中心工作流库，同时接入正式核算一期、多币种核算二期、电子会计档案 Phase 7、往来核算 Phase 8、银行对账 Phase 9、固定资产正式核算 Phase 10、薪酬正式核算 Phase 11、存货与成本核算 Phase 12、税务核算 Phase 13、预提摊销与融资利息 Phase 14 和合并报表 Phase 15。已审核凭证过账会生成正式不可变分录；反过账不删除原分录，而是生成冲销分录并保留原分录审计轨迹。凭证附件上传后会生成会计档案文档索引和哈希，往来核算从正式分录行生成未清项和账龄，银行对账从导入流水和 `1001/1002/1012` 资金分录生成调节表，固定资产资本化、折旧、减值和处置会生成带 `asset` 辅助维度的正式分录，税务核算从正式税费分录生成增值税台账和申报底稿，预提摊销按计划生成本期正式分录，合并报表读取单体报表包并在合并层维护抵销工作底稿，永久原件存储、CA 签章、官方发票验真、税局直连申报和完整档案移交流程仍放入后续阶段。

## 账簿读模型 MVP

当前账簿视图支持：
- 总账：优先按正式分录汇总科目借方、贷方、余额方向和分录数；无正式分录时回退已审核凭证。
- 明细账：优先按期间与科目编码列出正式分录行；无正式分录时回退已审核凭证分录。
- 科目余额表：优先按正式分录展示科目余额、借贷合计和平衡状态；无正式分录时回退已审核凭证。
- 账套与期间：查看默认账套和跨境电商账套，按账套读取会计期间状态、凭证数量和过账数量，支持关闭与重开期间。

该能力已接入正式分录读取来源，但仍不覆盖完整期末结账、反结账、辅助核算、多币种重估或完整多账套核算；期间关闭仍是一期控制边界，用于阻止关闭期间继续正式过账。
账簿读取接口受 `ledger.read` 权限控制，期间关闭/重开受 `ledger.period.manage` 权限控制；前端默认以 `X-Actor-Id: u-finance-manager` 读取和操作，后端会记录 `ledger.general.read`、`ledger.detail.read`、`ledger.account_balances.read`、`ledger.period.close` 和 `ledger.period.reopen` 审计日志。

## 固定资产台账与正式核算 Phase 10

当前固定资产模块支持：

- 新增固定资产，记录账套、资产名称、类别、购置日期、原值、残值、折旧月数、位置和保管人。
- 按直线法自动计算月折旧额，并按会计期间幂等计提本月折旧。
- 报废和出售固定资产，出售时计算处置损益。
- 盘点固定资产，记录位置、保管人、资产状态、盘点人和备注。
- 按账套读取资产台账和摘要，统计原值、累计折旧、账面净值和月折旧额。
- 将资产资本化入账，借记 `1601 固定资产`，贷记应付、银行或指定过渡科目。
- 按资产逐笔生成正式折旧分录，借记 `6602 管理费用`，贷记 `1602 累计折旧`。
- 记录固定资产减值，借记 `6701 资产减值损失`，贷记 `1603 固定资产减值准备`。
- 通过 `1606 固定资产清理` 完成正式处置，结转原值、累计折旧、减值准备、处置收入和处置损益。
- 读取正式资产卡片，追溯资本化、最近折旧、减值准备、处置分录和正式净值。

固定资产台账仍是内存 MVP，服务重启后固定资产演示数据会重置；正式核算 Phase 10 使用正式分录库保存资本化、折旧、减值和处置结果，并用 `asset` 辅助核算维度追溯资产。台账接口受 `fixed_asset.read`、`fixed_asset.write`、`fixed_asset.depreciate`、`fixed_asset.dispose` 和 `fixed_asset.inventory` 权限控制，并记录 `fixed_asset.*` 审计日志；正式核算接口受 `fixed_asset_accounting.read`、`fixed_asset_accounting.post`、`fixed_asset_accounting.impair` 和 `fixed_asset_accounting.dispose` 权限控制，并记录 `fixed_asset_accounting.*` 审计事件。

正式核算接口：

```text
GET /api/v1/fixed-asset-accounting/cards?account_set_id=default
POST /api/v1/fixed-asset-accounting/capitalize
POST /api/v1/fixed-asset-accounting/depreciation
POST /api/v1/fixed-asset-accounting/impairment
POST /api/v1/fixed-asset-accounting/disposal
```

正式分录来源键：

```text
fixed_asset_capitalization:{account_set_id}:{asset_id}
fixed_asset_depreciation:{account_set_id}:{period}:{asset_id}
fixed_asset_impairment:{account_set_id}:{period}:{asset_id}
fixed_asset_disposal:{account_set_id}:{period}:{asset_id}
```

当前不提供固定资产卡片附件、复杂融资租赁、资产评估接口、税会差异自动申报、集团跨法人调拨或完整资产清查审批流程。

## 工资管理 MVP

当前工资管理模块支持：

- 录入员工、部门、基本工资、奖金、津贴、社保基数、公积金基数和专项附加扣除。
- 按 MVP 简化口径计算员工社保、公积金、应纳税所得额、个税、实发工资和企业用工成本。
- 汇总应发工资、个税、实发工资、企业成本和平均实发工资。
- 按部门生成工资分析，展示人数、应发、实发和企业成本。

当前个税计算采用月度综合所得简化税率表，默认员工社保 10.5%、企业社保 26.3%、个人/企业公积金各 7%、基本扣除 5000 元；不处理累计预扣预缴、城市差异、封顶基数、补充公积金、年终奖单独计税、专项附加明细校验、银行代发或正式申报。接口受 `payroll.calculate` 权限控制，并记录 `payroll.calculate` 审计日志。

## 薪酬正式核算 Phase 11

当前薪酬正式核算模块支持：

- 基于工资计算结果生成默认工资批次 `PAY-YYYY-MM`。
- 生成工资和企业社保公积金计提正式分录，借记费用科目，贷记 `2211 应付职工薪酬`。
- 生成工资发放正式分录，借记 `2211`，贷记个人社保公积金、个税和 `1002 银行存款`。
- 生成个税、个人社保公积金和企业社保公积金缴纳分录，支持次月缴纳。
- 前端工资管理面板展示批次状态、计提分录、发放分录、缴纳状态和期间关闭错误提示。

薪酬正式核算接口：

```text
GET /api/v1/payroll-accounting/batches?account_set_id=default&period=2026-06
POST /api/v1/payroll-accounting/accruals
POST /api/v1/payroll-accounting/payments
POST /api/v1/payroll-accounting/liability-payments
```

正式分录来源键：

```text
payroll_accrual:{account_set_id}:{period}:{payroll_batch_id}
payroll_payment:{account_set_id}:{period}:{payroll_batch_id}
payroll_liability_payment:{account_set_id}:{payment_period}:{payroll_batch_id}
```

接口受 `payroll_accounting.read`、`payroll_accounting.accrue`、`payroll_accounting.pay` 和 `payroll_accounting.remit` 权限控制，并记录 `payroll_accounting.*` 审计事件。当前不保存身份证号、银行卡号或手机号明文，不接真实银行代发，不发送工资条，不做累计预扣预缴完整申报。

## 存货与成本核算 Phase 12

当前存货正式核算模块支持：

- 按账套、SKU 和仓库维护库存余额，展示数量、金额和移动加权平均成本。
- 采购入库生成借记 `1405 库存商品`、贷记 `2202 应付账款` 的正式分录，并更新移动平均成本。
- 销售出库按当前移动平均成本生成借记 `6401 主营业务成本`、贷记 `1405 库存商品` 的正式分录。
- 库存不足时拒绝销售出库成本结转，避免数量或金额出现负数。
- 存货跌价准备生成借记 `6701 资产减值损失`、贷记 `1471 存货跌价准备` 的正式分录。
- 盘点盘盈盘亏先进入 `1901 待处理财产损溢`，并保留审批人和审批时间。
- 期间结账新增 `inventory_cost_rollforward` 动作，用于汇总校验当期销售出库成本分录。

存货核算接口：

```text
GET /api/v1/inventory-accounting/balances?account_set_id=default
POST /api/v1/inventory-accounting/purchase-receipts
POST /api/v1/inventory-accounting/sales-issues
POST /api/v1/inventory-accounting/impairments
POST /api/v1/inventory-accounting/count-variances
```

正式分录来源键：

```text
inventory_receipt:{account_set_id}:{period}:{sku_id}:{supplier_id}
inventory_sales_issue:{account_set_id}:{period}:{sku_id}:{warehouse_id}:{sequence}
inventory_impairment:{account_set_id}:{period}:{sku_id}
inventory_count_variance:{account_set_id}:{period}:{sku_id}:{warehouse_id}
```

接口受 `inventory_accounting.read`、`inventory_accounting.receipt`、`inventory_accounting.issue`、`inventory_accounting.impair` 和 `inventory_accounting.count` 权限控制，并记录 `inventory_accounting.*` 审计事件。当前库存台账为内存 MVP，用于验证正式分录、移动加权成本和前端流程；暂不接 WMS 实时库存、批次保质期、生产制造 BOM、工序成本或跨境电商平台真实订单。

## 税务核算与申报底稿 Phase 13

当前税务核算模块支持：

- 从正式分录提取 `22210101` 进项税额、`22210102` 销项税额和 `22210104` 进项税额转出，生成增值税台账。
- 生成申报底稿，展示销项税额、进项税额、进项转出、应交增值税、附加税和企业所得税。
- 结转未交增值税，借记 `22210103 应交税费-应交增值税（转出未交增值税）`，贷记 `222102 应交税费-未交增值税`。
- 计提城建税及教育费附加，借记 `6403 税金及附加`，贷记 `222103 应交税费-城建税及教育费附加`。
- 计提企业所得税，借记 `6801 所得税费用`，贷记 `222104 应交税费-企业所得税`。
- 记录纳税支付，借记对应税费明细科目，贷记 `1002 银行存款`。
- 期间结账新增 `tax_surtax_accrual` 动作，用当期未交增值税结转金额自动生成附加税计提。

税务核算接口：

```text
GET /api/v1/tax-accounting/vat-ledger?account_set_id=default&period=2026-06
GET /api/v1/tax-accounting/filing-worksheet?account_set_id=default&period=2026-06
POST /api/v1/tax-accounting/unpaid-vat-transfer
POST /api/v1/tax-accounting/surtax-accrual
POST /api/v1/tax-accounting/income-tax-accrual
POST /api/v1/tax-accounting/tax-payments
```

正式分录来源键：

```text
tax_unpaid_vat_transfer:{account_set_id}:{period}
tax_surtax_accrual:{account_set_id}:{period}
tax_income_tax_accrual:{account_set_id}:{period}
tax_payment:{account_set_id}:{period}:{tax_account_code}
```

接口受 `tax_accounting.read`、`tax_accounting.accrue` 和 `tax_accounting.pay` 权限控制，并记录 `tax_accounting.*` 审计事件。当前申报底稿只作为计算和复核依据，不做税局直连申报、不自动抵扣认证、不做真实发票验真、不处理复杂税收优惠备案，也不替代税务师判断。

## 预提摊销与融资利息 Phase 14

当前预提摊销与融资利息模块支持：

- 创建预付摊销、预提费用、递延收入和借款利息计划，记录账套、起止期间、总金额、本期入账科目和已生成期间。
- 月度金额按计划期间平均分摊，尾差由最后一期吸收，避免累计金额偏离总额。
- `post_schedule_for_period` 按 `schedule_posting:{account_set_id}:{period}:{schedule_code}` 来源键生成本期正式分录，重复调用返回既有分录。
- 借款利息按本金和年利率计算月息，来源键为 `loan_interest_accrual:{account_set_id}:{period}:{loan_code}`。
- 期间结账新增 `accrual_amortization_posting` 动作，按活跃核算计划生成本期幂等分录。

预提摊销与融资利息接口：

```text
GET /api/v1/accrual-amortization/schedules?account_set_id=default
POST /api/v1/accrual-amortization/schedules
POST /api/v1/accrual-amortization/schedules/{schedule_code}/post
POST /api/v1/accrual-amortization/loan-interest
```

正式分录来源键：

```text
schedule_posting:{account_set_id}:{period}:{schedule_code}
loan_interest_accrual:{account_set_id}:{period}:{loan_code}
```

接口受 `accrual_amortization.read`、`accrual_amortization.write` 和 `accrual_amortization.post` 权限控制，并记录 `accrual_amortization.*` 审计事件。当前计划表为内存 MVP，用于验证正式分录、期间结账和前端流程；暂不做复杂金融工具公允价值、实际利率摊余成本完整模型、租赁准则全流程、合同收入五步法自动判断或长期计划持久化治理。

## 合并报表与内部抵销 Phase 15

当前合并报表模块支持：

- 维护合并集团、纳入账套、主体名称、持股比例和合并方法。
- 读取单体账套资产负债表、利润表和现金流量表报表包。
- 重建内部应收应付、内部销售成本、期末存货未实现利润和投资权益抵销工作底稿。
- 计算少数股东权益和少数股东损益，展示合并资产负债表、合并利润表和合并现金流量表摘要。
- 抵销分录只存在于合并层，不回写单体账套正式分录。

合并报表接口：

```text
GET /api/v1/consolidation/groups
POST /api/v1/consolidation/groups
GET /api/v1/consolidation/reporting-package?account_set_id=default&period=2026-06
GET /api/v1/consolidation/eliminations?group_id=group-001&period=2026-06
POST /api/v1/consolidation/eliminations/rebuild
GET /api/v1/consolidation/statements?group_id=group-001&period=2026-06
```

接口受 `consolidation.read`、`consolidation.write` 和 `consolidation.rebuild` 权限控制，并记录 `consolidation.*` 审计事件。当前合并范围和抵销底稿为内存 MVP，用于验证多账套合并流程；暂不做复杂股权购买法追溯、商誉减值完整评估模型、境外准则转换或审计合并底稿替代。

## 财务报表自动生成 MVP

当前财务报表模块支持：

- 基于正式分录优先生成资产负债表、利润表、现金流量表、所有者权益变动表和管理报表摘要；无正式分录时回退已审核凭证，再无数据时回退内置样例经营数据。
- 使用默认“中国企业会计准则通用报表映射”计算报表项目：资产负债表取期末余额，利润表取期间发生额，现金流量表取现金流项目金额，所有者权益变动表取期初权益、净利润、利润分配和期末权益。
- 现金流量表优先读取分录行 `cash_flow_item_code`；缺失时按现金科目与对方科目规则推断，并在校验结果中标记 warning。
- 生成结果返回 `mapping_set_id`、`trace_items` 和 `validation_items`，可追溯项目编码、映射规则、来源科目、现金流项目、公式、金额和公式校验状态。
- 支持将当前期间报表生成 `StatementSnapshot` 快照，记录版本号、内容哈希、校验状态和归档状态；锁定后保留 `locked_by` / `locked_at` 审计信息。
- 支持从快照导出 Excel 和 PDF；Excel 包含四张标准报表、校验结果和追溯明细，PDF 当前为轻量版归档摘要。
- 接口受 `statement.generate`、`statement.validate`、`statement.mapping.view`、`statement.mapping.manage`、`statement.snapshot.create`、`statement.snapshot.lock`、`statement.archive.view`、`statement.export` 权限控制，并记录 `statement.generate`、`statement.mapping.view`、`statement.mapping.update`、`statement.snapshot.create`、`statement.snapshot.lock`、`statement.archive.view`、`statement.export` 审计事件。

当前实现不覆盖合并报表、复杂金融工具、长期股权投资、递延所得税、现金流量表补充资料、附注披露、正式申报报表或审计定稿流程。

## 报表映射引擎 Phase 5

后端新增 `GET /api/v1/financial-statements/mapping-sets/default?account_set_id=default`，前端 AI 财务中心新增“报表映射”面板，展示四张标准报表的映射规则和取数公式。

回归命令：

```powershell
python -m pytest backend/tests/test_statement_mapping_service.py backend/tests/test_financial_statement_service.py backend/tests/test_financial_statement_api.py backend/tests/test_accounting_service.py backend/tests/test_system_admin_api.py
npm --prefix frontend test
npm --prefix frontend run build
```

## 报表归档导出 Phase 6

后端新增快照归档和导出接口：

```text
POST /api/v1/financial-statements/snapshots
GET /api/v1/financial-statements/snapshots?account_set_id=default&period=2026-06
POST /api/v1/financial-statements/snapshots/{snapshot_id}/lock
GET /api/v1/financial-statements/snapshots/{snapshot_id}/export/xlsx
GET /api/v1/financial-statements/snapshots/{snapshot_id}/export/pdf
```

前端 AI 财务中心新增“报表归档”面板，支持按期间创建快照、查看归档版本、锁定快照，并从已保存快照导出 Excel 或 PDF。样例数据来源生成的快照会标记为 `demo_only`，用于演示流程；正式分录来源的快照可进入 `draft`、`archived` 状态。关闭期间后可以继续生成新的快照版本，但不会覆盖已锁定快照。

回归命令：

```powershell
python -m pytest backend/tests/test_statement_archive_service.py backend/tests/test_statement_export_service.py backend/tests/test_financial_statement_api.py backend/tests/test_financial_statement_service.py backend/tests/test_system_admin_api.py
npm --prefix frontend test
npm --prefix frontend run build
```

## 电子会计档案 Phase 7

后端新增会计档案文档、案卷和归档包接口：

```text
GET /api/v1/accounting-archive/documents?account_set_id=default&period=2026-06
GET /api/v1/accounting-archive/documents/{archive_document_id}
POST /api/v1/accounting-archive/cases
GET /api/v1/accounting-archive/cases/{archive_case_id}/download
```

凭证附件上传后会创建 `ArchiveDocument`，记录 `source_type/source_id`、账套、期间、文档类型、文件名、content type、大小、`sha256_hash`、`storage_status`、`ocr_status`、`verification_status` 和 `retention_years`。文本附件可保存文本摘录；图片或 PDF 在未接入真实 OCR 引擎时标记为 `ocr_status="engine_required"`；发票和银行回单在未接入外部验真服务时标记为 `verification_status="pending_external"`，不会伪造成 `verified`。

前端 AI 财务中心新增“会计档案”面板，支持查看当前期间档案文档、勾选文档创建案卷，并下载包含 `manifest.json`、文档元数据 JSON 和可用文本摘录的 ZIP 归档包。当前 MVP 不永久保存原始二进制文件，不提供 CA 签章、对象存储 WORM、官方电子发票验真、跨系统档案移交或档案销毁审批。

权限点：`archive.read`、`archive.document.create`、`archive.case.create`、`archive.package.download`、`archive.verification.update`。审计事件：`archive.document.list`、`archive.document.get`、`archive.document.create`、`archive.case.create`、`archive.package.download`、`archive.verification.update`。

回归命令：
```powershell
python -m pytest backend/tests/test_accounting_archive_service.py backend/tests/test_accounting_archive_api.py backend/tests/test_voucher_center_service.py backend/tests/test_voucher_center_api.py backend/tests/test_system_admin_api.py backend/tests/test_module_registry_api.py
npm --prefix frontend test
npm --prefix frontend run build
```

## 往来核算 Phase 8

后端新增应收应付余额、账龄和核销接口：

```text
GET /api/v1/receivable-payable/balances?account_set_id=default&period=2026-06&open_item_type=receivable
GET /api/v1/receivable-payable/aging?account_set_id=default&period=2026-06&open_item_type=receivable&as_of_date=2026-06-30
POST /api/v1/receivable-payable/settlements
```

应收未清项来自 `1122/1221` 且必须挂载客户维度；应付未清项来自 `2202/2241` 且必须挂载供应商维度。系统按正式已过账分录行生成未清项和往来余额，不从凭证摘要、报表快照或演示数据反推。账龄桶固定为 `0-30`、`31-60`、`61-90`、`91-180`、`181-365` 和 `365+`，截止日默认取期间月末。

核销支持同一往来对象下的部分核销，只追加 `CounterpartySettlement` 记录并扣减未清余额展示，不改写历史正式分录；已关闭期间拒绝新增核销。坏账准备接入期间结账动作 `bad_debt_provision`，当前默认规则为 `91-180` 计提 5%、`181-365` 计提 10%、`365+` 计提 50%，生成借记 `6701`、贷记 `1231` 的正式分录。

前端 AI 财务中心新增“应收应付余额与账龄”面板，支持应收/应付切换、余额摘要、往来对象余额表和账龄分布表。接口受 `receivable_payable.read`、`receivable_payable.settle`、`receivable_payable.bad_debt` 权限控制，并记录 `receivable_payable.balance.read`、`receivable_payable.aging.read`、`receivable_payable.settle`、`receivable_payable.bad_debt.provision` 审计事件。

当前不覆盖销售订单、采购订单、合同台账、银行流水自动抓取、自动付款、信用额度审批、完整催收流程、预收预付重分类报表或复杂坏账组合模型。

回归命令：
```powershell
python -m pytest backend/tests/test_receivable_payable_service.py backend/tests/test_receivable_payable_api.py backend/tests/test_period_close_service.py backend/tests/test_accounting_service.py backend/tests/test_system_admin_api.py backend/tests/test_module_registry_api.py
npm --prefix frontend test
npm --prefix frontend run build
```

## 银行对账 Phase 9

后端新增银行流水、匹配候选、确认对账和银行余额调节表接口：

```text
POST /api/v1/bank-reconciliation/statements/import
GET /api/v1/bank-reconciliation/matches?account_set_id=default&bank_account_id=bank-001&period=2026-06&minimum_score=80
POST /api/v1/bank-reconciliation/confirm
GET /api/v1/bank-reconciliation/statements?account_set_id=default&bank_account_id=bank-001&period=2026-06
```

银行流水按 `account_set_id + bank_account_id + bank_reference` 去重。匹配候选基于银行流水与正式资金分录生成，正式资金分录只读取 `1001 库存现金`、`1002 银行存款`、`1012 其他货币资金`；评分规则当前为金额一致 60 分、日期一致 25 分、摘要匹配 15 分。确认对账只追加 `BankReconciliationMatch`，不修改正式分录或银行流水金额；已关闭期间拒绝新增确认。

银行余额调节表展示银行账面余额、企业账面余额、银行已收企业未收、银行已付企业未付、企业已收银行未收、企业已付银行未付和调节后余额。确认接口可透传八期 `CounterpartySettlementCreate`，用于收付款确认后联动应收应付核销。

前端 AI 财务中心新增“银行余额调节表”面板，展示银行账户、调节前后余额、银行未达账项、企业未达账项和匹配候选。接口受 `bank_reconciliation.read`、`bank_reconciliation.import`、`bank_reconciliation.match`、`bank_reconciliation.confirm` 权限控制，并记录 `bank_reconciliation.statement.import`、`bank_reconciliation.match.suggest`、`bank_reconciliation.match.confirm`、`bank_reconciliation.statement.read` 审计事件。

当前不接真实网银，不保存网银登录凭据，不做银企直连签名、自动付款、银行回单官方验真、多币种换汇拆分对账或完整出纳复核流程。

回归命令：
```powershell
python -m pytest backend/tests/test_bank_reconciliation_service.py backend/tests/test_bank_reconciliation_api.py backend/tests/test_receivable_payable_service.py backend/tests/test_accounting_service.py backend/tests/test_system_admin_api.py backend/tests/test_module_registry_api.py
npm --prefix frontend test
npm --prefix frontend run build
```

## AI 自动审核

当前审核模块支持：

- 借贷平衡检查。
- 金额、税额和价税合计勾稽检查。
- 发票号码、摘要、交易对方完整性检查。
- 分录行金额有效性检查。
- 进项税额借方、销项税额贷方的方向检查。
- 输出审核评分、通过/需复核/高风险评级、错误证据、整改建议和法规/准则引用。

本模块用于自动找错和辅助复核，不替代财务审核、税务复核或正式审计结论。

## AI 首页 V1.0

当前 AI 首页按 FRD V1.0 的首页结构展示：

- 经营概况：今日销售额、本月销售额、本年销售额。
- 利润：毛利润、净利润、利润率。
- 现金流：经营现金流流入、流出、货币资金余额。
- 库存：库存金额、库存周转率、滞销库存估算。
- 税务：本月应纳税额估算、税负率、风险数量。
- AI 今日提示：风险提示、异常分析、今日经营建议。

首页数据支持默认示例数据，也支持用户导入/手动填写数据后重新生成。

## Excel / WPS 表格字段

建议表头包含：

```text
期间、营业收入、营业成本、销售费用、管理费用、研发费用、财务费用、净利润、
货币资金、应收账款、存货、固定资产、资产总额、短期借款、应付账款、
负债总额、所有者权益、经营现金流净额、投资现金流净额、筹资现金流净额、
库存周转天数、税负率
```

`税负率` 可以填写 `0.038` 或 `3.8`，系统会按 `3.8%` 处理。

## 本地启动

```powershell
.\start-local.ps1
```

启动后访问：

```text
前端：http://127.0.0.1:5173
后端：http://127.0.0.1:8000/health
```

## 期间结账引擎 Phase 4

当前版本已接入正式核算期间结账流程，入口位于前端 AI 财务中心的“期间结账”面板，后端 API 前缀为 `/api/v1/period-close`。

支持能力：
- 结账检查清单：期间存在、期间未关闭、正式分录借贷平衡、凭证已过账、科目有效、期末汇率准备、折旧/工资/税费准备状态。
- 自动期末分录：固定资产折旧、工资计提、税费计提、外币期末重估、坏账准备、损益结转、年终利润分配。
- 外币重估：按期末汇率计算 `原币余额 × 期末汇率 - 账面本位币余额`，只生成 CNY 调整分录，保持原币余额不变。
- 损益结转：月结将收入、成本、费用类科目结转至 `4103 本年利润`；年结将 `4103 本年利润` 转入 `4104 利润分配-未分配利润`。
- 幂等控制：同一账套、期间、动作和来源键重复执行时返回已有分录，不重复过账。
- 期间控制：关闭期间后拒绝新增正式分录、凭证过账和重生成期末动作；重开期间只记录状态和审计事件，不删除已生成分录。

权限与审计：
- 权限点：`period_close.view`、`period_close.check`、`period_close.generate`、`period_close.close`、`period_close.reopen`。
- 审计事件：`period_close.run_started`、`period_close.runs_viewed`、`period_close.checks_completed`、`period_close.actions_previewed`、`period_close.actions_generated`、`period_close.period_closed`、`period_close.period_reopened`。

回归命令：

```powershell
python -m pytest backend/tests/test_period_close_service.py backend/tests/test_period_close_api.py backend/tests/test_accounting_period_service.py backend/tests/test_accounting_service.py backend/tests/test_fixed_asset_service.py backend/tests/test_payroll_service.py backend/tests/test_payroll_accounting_service.py backend/tests/test_payroll_accounting_api.py
npm --prefix frontend test
npm --prefix frontend run build
```
