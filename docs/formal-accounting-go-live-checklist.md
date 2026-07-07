# 正式核算上线治理清单

## 上线前数据冻结

- 冻结目标账套和期间的新增凭证、正式分录、期间结账、报表快照和归档操作。
- 记录冻结时间、冻结人、账套、期间和待迁移 MVP 凭证范围。
- 冻结后只执行完整性校验、迁移 dry-run、备份、恢复演练和门禁读取。

## 备份和恢复演练

- 执行 `POST /api/v1/accounting-governance/backups` 生成备份清单。
- 核对清单覆盖 `journal_entries`、`journal_lines`、`accounting_periods`、`statement_mappings`、`archive_documents` 和 `audit_logs` 等核心数据集。
- 执行 `POST /api/v1/accounting-governance/restore-rehearsals`，记录临时恢复库路径、行数、完整性状态、开始时间、完成时间和操作者。
- 恢复演练未通过时不得执行迁移 apply 或上线审批。

## MVP 与正式核算并行核对

- 执行迁移 dry-run，确认 `blocked_count` 为 0。
- 对比 MVP 凭证状态、正式分录来源键、借贷金额、已迁移数量和阻塞原因。
- 历史 MVP 数据迁移为可选动作；执行 apply 前必须已经生成备份清单，并且完整性校验无失败项。

## 关键报表核对

- 资产负债表：确认资产合计等于负债和所有者权益合计。
- 利润表：确认收入、成本、费用、所得税和净利润来源于正式分录。
- 现金流量表：确认现金流项目来源或推断 warning 已复核。
- 报表映射：确认默认映射集启用且规则数不为 0。

## 权限职责分离

- 必备权限：`voucher.review`、`voucher.post`、`ledger.read`、`period_close.close`、`statement.generate`、`bank_reconciliation.confirm`、`receivable_payable.settle`、`tax_accounting.accrue`。
- 上线治理权限：`accounting_governance.read`、`accounting_migration.preview`、`accounting_migration.apply`、`accounting_backup.create`、`accounting_governance.approve_go_live`。
- 同一用户不能同时完成制单、审核和正式过账。
- 迁移执行人不能审批上线。

## 上线当天切换

- 读取 `GET /api/v1/accounting-governance/go-live-gate`，确认状态为 `pass`。
- 核对完整性校验、迁移 dry-run、备份恢复、权限矩阵和回归命令全部通过。
- 记录审批人、切换时间、门禁结果和审计日志。

## 上线后首月观察

- 每日检查正式分录借贷平衡、重复来源键、期间锁定、报表映射和归档链接。
- 每周复核迁移差异、关键报表、往来余额、银行调节表和税务底稿。
- 观察异常包括：门禁 warning、迁移阻塞、缺失归档、报表不平、回归命令失败。

## 回滚条件和步骤

- 回滚条件：完整性校验失败、恢复演练失败、关键报表不一致、权限矩阵缺失关键权限、审计日志缺失关键操作。
- 回滚步骤：停止新迁移批次，保留原始 MVP 数据和正式分录，恢复备份清单对应的数据快照，在审计日志中记录回滚原因和责任人。
- 回滚后重新执行备份、恢复演练、迁移 dry-run 和上线门禁。

## 自动化验证命令

```powershell
python -m pytest backend/tests -q
npm --prefix frontend test
npm --prefix frontend run build
git diff --check
```

## 手工验收场景

- 已审核凭证生成不可变正式分录。
- 总账、明细账和科目余额表优先读取正式分录。
- 期间结账生成期末动作并阻止关账后新增正式分录。
- 固定资产、薪酬、存货、税务、预提摊销和合并模块生成正式分录或工作底稿。
- 电子凭证归档包可导出。
- 上线门禁全部通过。
