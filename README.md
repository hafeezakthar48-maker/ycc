# China Finance AI Assistant

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
- 工资管理 MVP：支持工资计算、社保、公积金、个税、实发工资、企业成本和部门工资分析
- 财务报表自动生成 MVP：支持资产负债表、利润表、现金流量表、所有者权益变动表、管理报表摘要、快照归档和 Excel/PDF 导出
- AI 凭证草稿：支持费用采购、库存采购、销售收入三类场景，自动生成借贷分录草稿、借贷平衡检查、风险提示和法规引用
- AI 自动审核：审核凭证分录、发票号码、摘要、交易对方、价税勾稽、借贷平衡和增值税科目方向，输出评分、评级、错误清单和整改建议

第一版支持先下载标准模板，再上传 `.xlsx` / `.xlsm` 分析；WPS 表格请先另存为 `.xlsx`。发票图片 / PDF 上传入口已预留，但当前本地环境未内置真实 OCR 引擎，系统会明确提示需接入 OCR 服务，不会伪造图片或 PDF 识别结果。凭证中心当前使用 SQLite 持久化工作流库保存演示凭证、审核状态、过账状态、账套标识、附件元数据和月度编号序列；正式核算一期已新增独立 SQLite 正式分录库，已审核凭证过账会生成 `journal_entry` / `journal_line`，账簿和财务报表优先读取正式分录来源，无正式分录时再回退 MVP 凭证工作流或样例经营数据。固定资产当前为内存台账 MVP，用于验证资产生命周期、折旧和盘点流程。工资管理当前为简化计算 MVP，用于验证工资、社保、公积金、个税和人工成本分析流程。财务报表当前为单账套、单期间生成 MVP，用于验证报表取数和管理摘要，不替代正式财务报表编制与披露。自动审核只做规则提示和风险定位，不构成最终审计意见。暂不支持 WPS 原生 `.et`、旧版 `.xls`、自动申报税务、每日实时政策同步或自动失效判断。

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

当前实现保留凭证中心工作流库，同时接入正式核算一期和多币种核算二期。已审核凭证过账会生成正式不可变分录；反过账不删除原分录，而是生成冲销分录并保留原分录审计轨迹。期末外币重估、辅助核算维度、期末损益结转、电子会计档案和永久附件存储放入后续阶段。

## 账簿读模型 MVP

当前账簿视图支持：
- 总账：优先按正式分录汇总科目借方、贷方、余额方向和分录数；无正式分录时回退已审核凭证。
- 明细账：优先按期间与科目编码列出正式分录行；无正式分录时回退已审核凭证分录。
- 科目余额表：优先按正式分录展示科目余额、借贷合计和平衡状态；无正式分录时回退已审核凭证。
- 账套与期间：查看默认账套和跨境电商账套，按账套读取会计期间状态、凭证数量和过账数量，支持关闭与重开期间。

该能力已接入正式分录读取来源，但仍不覆盖完整期末结账、反结账、辅助核算、多币种重估或完整多账套核算；期间关闭仍是一期控制边界，用于阻止关闭期间继续正式过账。
账簿读取接口受 `ledger.read` 权限控制，期间关闭/重开受 `ledger.period.manage` 权限控制；前端默认以 `X-Actor-Id: u-finance-manager` 读取和操作，后端会记录 `ledger.general.read`、`ledger.detail.read`、`ledger.account_balances.read`、`ledger.period.close` 和 `ledger.period.reopen` 审计日志。

## 固定资产台账 MVP

当前固定资产模块支持：

- 新增固定资产，记录账套、资产名称、类别、购置日期、原值、残值、折旧月数、位置和保管人。
- 按直线法自动计算月折旧额，并按会计期间幂等计提本月折旧。
- 报废和出售固定资产，出售时计算处置损益。
- 盘点固定资产，记录位置、保管人、资产状态、盘点人和备注。
- 按账套读取资产台账和摘要，统计原值、累计折旧、账面净值和月折旧额。

当前实现是内存台账 MVP，服务重启后固定资产演示数据会重置；折旧状态只用于产品流程验证，不自动生成正式凭证、固定资产卡片附件、总账分录或纳税调整。接口受 `fixed_asset.read`、`fixed_asset.write`、`fixed_asset.depreciate`、`fixed_asset.dispose` 和 `fixed_asset.inventory` 权限控制，并记录 `fixed_asset.*` 审计日志。

## 工资管理 MVP

当前工资管理模块支持：

- 录入员工、部门、基本工资、奖金、津贴、社保基数、公积金基数和专项附加扣除。
- 按 MVP 简化口径计算员工社保、公积金、应纳税所得额、个税、实发工资和企业用工成本。
- 汇总应发工资、个税、实发工资、企业成本和平均实发工资。
- 按部门生成工资分析，展示人数、应发、实发和企业成本。

当前个税计算采用月度综合所得简化税率表，默认员工社保 10.5%、企业社保 26.3%、个人/企业公积金各 7%、基本扣除 5000 元；不处理累计预扣预缴、城市差异、封顶基数、补充公积金、年终奖单独计税、专项附加明细校验、银行代发或正式申报。接口受 `payroll.calculate` 权限控制，并记录 `payroll.calculate` 审计日志。

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
- 自动期末分录：固定资产折旧、工资计提、税费计提、外币期末重估、损益结转、年终利润分配。
- 外币重估：按期末汇率计算 `原币余额 × 期末汇率 - 账面本位币余额`，只生成 CNY 调整分录，保持原币余额不变。
- 损益结转：月结将收入、成本、费用类科目结转至 `4103 本年利润`；年结将 `4103 本年利润` 转入 `4104 利润分配-未分配利润`。
- 幂等控制：同一账套、期间、动作和来源键重复执行时返回已有分录，不重复过账。
- 期间控制：关闭期间后拒绝新增正式分录、凭证过账和重生成期末动作；重开期间只记录状态和审计事件，不删除已生成分录。

权限与审计：
- 权限点：`period_close.view`、`period_close.check`、`period_close.generate`、`period_close.close`、`period_close.reopen`。
- 审计事件：`period_close.run_started`、`period_close.runs_viewed`、`period_close.checks_completed`、`period_close.actions_previewed`、`period_close.actions_generated`、`period_close.period_closed`、`period_close.period_reopened`。

回归命令：

```powershell
python -m pytest backend/tests/test_period_close_service.py backend/tests/test_period_close_api.py backend/tests/test_accounting_period_service.py backend/tests/test_accounting_service.py backend/tests/test_fixed_asset_service.py backend/tests/test_payroll_service.py
npm --prefix frontend test
npm --prefix frontend run build
```
