# 正式核算引擎十六期 上线治理迁移与验收 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立正式核算版本上线所需的数据迁移、完整性校验、备份恢复、权限矩阵、性能基线和验收清单。  
**Architecture:** 新增 `accounting_governance`、`migration`、`backup` 和 `integrity_check` 服务，作为正式核算引擎的上线控制层。该层不产生新的业务核算口径，只检查和保护已有正式分录、账簿、报表、归档和权限配置，确保实施前后可审计、可回滚、可验收。  
**Tech Stack:** FastAPI、Pydantic、SQLite、Decimal、pytest、React、TypeScript、Vite、Node test runner、PowerShell。

---

## 前置条件

- 一期到十五期大纲已完成评审，并按实施顺序逐期落地。
- 正式分录、账簿、报表、往来、资金、资产、薪酬、存货、税务和合并模块均有测试覆盖。
- 系统管理权限和审计日志可记录关键操作。
- 七期电子凭证归档可导出凭证和附件索引。

本期不改变会计准则和核算口径，不引入新业务模块，不自动清理历史数据，不删除 MVP 数据。

## 上线决策

- 正式核算上线采用“并行校验后切换”方式，先让正式引擎和 MVP 只读结果并行运行。
- 历史 MVP 数据迁移为可选动作，迁移前必须生成快照和差异报告。
- 切换正式核算来源前必须通过完整性校验、权限矩阵校验、关键报表一致性校验和备份恢复演练。
- 任何迁移修复都通过迁移批次记录，不直接覆盖原始记录。
- 上线后仍保留演示数据回退标识，但正式账套默认不再使用样例数据回退。
- 所有上线操作必须有操作者、时间、批次号、检查结果和审计日志。

## 文件结构

- Create: `backend/app/models/accounting_governance.py`
- Create: `backend/app/services/integrity_check_service.py`
- Create: `backend/app/services/migration_service.py`
- Create: `backend/app/services/backup_service.py`
- Create: `backend/app/services/accounting_governance_service.py`
- Create: `backend/app/api/accounting_governance.py`
- Modify: `backend/app/api/router_registry.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Create: `backend/tests/test_integrity_check_service.py`
- Create: `backend/tests/test_migration_service.py`
- Create: `backend/tests/test_backup_service.py`
- Create: `backend/tests/test_accounting_governance_api.py`
- Create: `frontend/src/types/accountingGovernance.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/AccountingGovernancePanel.tsx`
- Modify: `frontend/src/components/SystemAdminPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Create: `frontend/tests/accountingGovernanceApi.test.mjs`
- Create: `frontend/tests/accountingGovernancePanel.test.mjs`
- Create: `docs/formal-accounting-go-live-checklist.md`
- Modify: `README.md`
- Modify: `docs/01-mvp-design.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

## Task 1: 完整性校验模型和规则

**Files:**
- Create: `backend/app/models/accounting_governance.py`
- Create: `backend/app/services/integrity_check_service.py`
- Test: `backend/tests/test_integrity_check_service.py`

- [ ] **Step 1: Write failing integrity test**

```python
from app.services.integrity_check_service import run_accounting_integrity_checks


def test_integrity_checks_report_balanced_journal_entries():
    result = run_accounting_integrity_checks("default", "2026-06")

    assert result.account_set_id == "default"
    assert any(check.check_code == "journal_entries_balanced" for check in result.checks)
```

- [ ] **Step 2: Create governance models**

```python
from typing import Literal

from pydantic import BaseModel


CheckStatus = Literal["pass", "fail", "warning"]


class AccountingIntegrityCheck(BaseModel):
    check_code: str
    status: CheckStatus
    message: str
    affected_count: int = 0


class AccountingIntegrityReport(BaseModel):
    account_set_id: str
    period: str
    overall_status: CheckStatus
    checks: list[AccountingIntegrityCheck]
```

- [ ] **Step 3: Implement base checks**

```python
def run_accounting_integrity_checks(account_set_id: str, period: str):
    checks = [
        check_journal_entries_balanced(account_set_id, period),
        check_no_duplicate_source_keys(account_set_id, period),
        check_closed_period_has_no_new_unapproved_entries(account_set_id, period),
        check_statement_mapping_coverage(account_set_id, period),
        check_attachment_archive_links(account_set_id, period),
    ]
    overall_status = "fail" if any(item.status == "fail" for item in checks) else "warning" if any(item.status == "warning" for item in checks) else "pass"
    return AccountingIntegrityReport(account_set_id=account_set_id, period=period, overall_status=overall_status, checks=checks)
```

- [ ] **Step 4: Run integrity tests**

```powershell
python -m pytest backend/tests/test_integrity_check_service.py -v
```

Expected result: integrity report includes balance, source key, period lock, mapping and archive checks.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/models/accounting_governance.py backend/app/services/integrity_check_service.py backend/tests/test_integrity_check_service.py
git commit -m "feat: add accounting integrity checks"
```

## Task 2: MVP 数据迁移批次和差异报告

**Files:**
- Create: `backend/app/services/migration_service.py`
- Test: `backend/tests/test_migration_service.py`

- [ ] **Step 1: Add failing dry-run migration test**

```python
from app.services.migration_service import preview_mvp_to_formal_migration


def test_preview_migration_returns_batch_without_writing_entries():
    preview = preview_mvp_to_formal_migration("default", "2026-06", "migration-user")

    assert preview.mode == "dry_run"
    assert preview.account_set_id == "default"
    assert preview.proposed_entry_count >= 0
```

- [ ] **Step 2: Implement migration preview**

```python
def preview_mvp_to_formal_migration(account_set_id: str, period: str, actor_id: str):
    reviewed_vouchers = list_reviewed_vouchers(account_set_id, period)
    proposed_entries = [build_formal_entry_from_voucher(voucher) for voucher in reviewed_vouchers if not voucher.formal_journal_entry_id]
    return type(
        "MigrationPreview",
        (),
        {
            "mode": "dry_run",
            "account_set_id": account_set_id,
            "period": period,
            "actor_id": actor_id,
            "proposed_entry_count": len(proposed_entries),
            "warnings": collect_migration_warnings(proposed_entries),
        },
    )()
```

- [ ] **Step 3: Implement migration apply guard**

Required guards:
- The dry-run preview exists for the same batch.
- Integrity checks before migration return no failed checks.
- A backup snapshot exists.
- The actor has `accounting_migration.apply` permission.
- Source vouchers without review status are rejected.

- [ ] **Step 4: Run migration tests**

```powershell
python -m pytest backend/tests/test_migration_service.py -v
```

Expected result: dry run does not write entries and apply requires backup and clean checks.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/migration_service.py backend/tests/test_migration_service.py
git commit -m "feat: add formal accounting migration preview"
```

## Task 3: 备份、恢复演练和导出包

**Files:**
- Create: `backend/app/services/backup_service.py`
- Test: `backend/tests/test_backup_service.py`

- [ ] **Step 1: Add failing backup manifest test**

```python
from app.services.backup_service import create_accounting_backup_manifest


def test_backup_manifest_lists_core_accounting_datasets():
    manifest = create_accounting_backup_manifest("default", "2026-06", "backup-user")

    assert "journal_entries" in manifest.datasets
    assert "journal_lines" in manifest.datasets
    assert "audit_logs" in manifest.datasets
```

- [ ] **Step 2: Implement backup manifest**

```python
def create_accounting_backup_manifest(account_set_id: str, period: str, actor_id: str):
    datasets = [
        "journal_entries",
        "journal_lines",
        "accounting_periods",
        "statement_mappings",
        "counterparty_settlements",
        "bank_reconciliations",
        "fixed_asset_cards",
        "payroll_batches",
        "inventory_movements",
        "tax_worksheets",
        "voucher_archive",
        "audit_logs",
    ]
    return type("BackupManifest", (), {"account_set_id": account_set_id, "period": period, "actor_id": actor_id, "datasets": datasets})()
```

- [ ] **Step 3: Add restore rehearsal result**

Restore rehearsal must record:
- Backup manifest ID.
- Target temporary database path.
- Row counts per dataset.
- Integrity check result after restore.
- Start time, end time and actor ID.

- [ ] **Step 4: Run backup tests**

```powershell
python -m pytest backend/tests/test_backup_service.py -v
```

Expected result: backup manifest and restore rehearsal tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/backup_service.py backend/tests/test_backup_service.py
git commit -m "feat: add accounting backup manifest"
```

## Task 4: 权限矩阵和上线门禁

**Files:**
- Create: `backend/app/services/accounting_governance_service.py`
- Modify: `backend/app/services/system_admin_service.py`
- Test: `backend/tests/test_accounting_governance_api.py`

- [ ] **Step 1: Add failing permission matrix test**

```python
from app.services.accounting_governance_service import build_formal_accounting_permission_matrix


def test_permission_matrix_includes_segregation_of_duties():
    matrix = build_formal_accounting_permission_matrix()

    assert "voucher.post" in matrix.required_permissions
    assert "accounting_migration.apply" in matrix.required_permissions
    assert matrix.segregation_rules
```

- [ ] **Step 2: Implement permission matrix**

```python
def build_formal_accounting_permission_matrix():
    required_permissions = [
        "voucher.review",
        "voucher.post",
        "ledger.read",
        "period.close",
        "statement.generate",
        "bank_reconciliation.confirm",
        "receivable_payable.settle",
        "tax_accounting.accrue",
        "accounting_migration.preview",
        "accounting_migration.apply",
        "accounting_backup.create",
        "accounting_governance.approve_go_live",
    ]
    segregation_rules = [
        "同一用户不能同时完成制单、审核和正式过账",
        "迁移执行人不能审批上线",
        "备份恢复演练通过前不能切换正式核算来源",
    ]
    return type("PermissionMatrix", (), {"required_permissions": required_permissions, "segregation_rules": segregation_rules})()
```

- [ ] **Step 3: Implement go-live gate**

Go-live gate requires:
- Latest integrity report status is `pass`.
- Latest migration dry-run has no blocking warning.
- Backup manifest exists and restore rehearsal passed.
- Permission matrix has no missing critical permission.
- Backend regression, frontend test and production build commands passed.

- [ ] **Step 4: Run governance tests**

```powershell
python -m pytest backend/tests/test_accounting_governance_api.py backend/tests/test_system_admin_api.py -v
```

Expected result: permission matrix and go-live gate tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/accounting_governance_service.py backend/app/services/system_admin_service.py backend/tests/test_accounting_governance_api.py
git commit -m "feat: add formal accounting go live gate"
```

## Task 5: API、前端治理面板和上线清单

**Files:**
- Create: `backend/app/api/accounting_governance.py`
- Modify: `backend/app/api/router_registry.py`
- Modify: `backend/app/services/module_registry_service.py`
- Create: `frontend/src/types/accountingGovernance.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/AccountingGovernancePanel.tsx`
- Modify: `frontend/src/components/SystemAdminPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Create: `frontend/tests/accountingGovernanceApi.test.mjs`
- Create: `frontend/tests/accountingGovernancePanel.test.mjs`
- Create: `docs/formal-accounting-go-live-checklist.md`
- Modify: `README.md`
- Modify: `docs/01-mvp-design.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

- [ ] **Step 1: Implement endpoints**

Endpoints:
- `GET /api/v1/accounting-governance/integrity-checks`
- `POST /api/v1/accounting-governance/migration-preview`
- `POST /api/v1/accounting-governance/migration-apply`
- `POST /api/v1/accounting-governance/backups`
- `POST /api/v1/accounting-governance/restore-rehearsals`
- `GET /api/v1/accounting-governance/permission-matrix`
- `GET /api/v1/accounting-governance/go-live-gate`

Permissions:
- `accounting_governance.read`
- `accounting_migration.preview`
- `accounting_migration.apply`
- `accounting_backup.create`
- `accounting_governance.approve_go_live`

Audit events:
- `accounting_governance.integrity.read`
- `accounting_governance.migration.preview`
- `accounting_governance.migration.apply`
- `accounting_governance.backup.create`
- `accounting_governance.restore.rehearsal`
- `accounting_governance.go_live_gate.read`

- [ ] **Step 2: Build governance panel**

Panel must show:
- 完整性校验结果。
- 迁移预览批次和差异摘要。
- 备份清单和恢复演练状态。
- 权限矩阵缺口。
- 上线门禁状态。
- 回归测试命令和最近执行结果。

- [ ] **Step 3: Write go-live checklist**

`docs/formal-accounting-go-live-checklist.md` must contain:
- 上线前数据冻结流程。
- 备份和恢复演练步骤。
- MVP 与正式核算并行核对方法。
- 关键报表核对表。
- 权限职责分离表。
- 上线当天切换步骤。
- 上线后首月观察指标。
- 回滚条件和回滚步骤。

- [ ] **Step 4: Run full regression**

```powershell
python -m pytest
npm --prefix frontend test
npm --prefix frontend run build
```

Expected result: backend test suite, frontend tests and production build pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/api/accounting_governance.py backend/app/api/router_registry.py backend/app/services/module_registry_service.py frontend/src/types/accountingGovernance.ts frontend/src/services/dashboardApi.ts frontend/src/components/AccountingGovernancePanel.tsx frontend/src/components/SystemAdminPanel.tsx frontend/src/components/DashboardLayout.tsx frontend/tests/accountingGovernanceApi.test.mjs frontend/tests/accountingGovernancePanel.test.mjs docs/formal-accounting-go-live-checklist.md README.md docs/01-mvp-design.md docs/02-api-design.md docs/03-frd-v1.0.md
git commit -m "feat: add formal accounting governance panel"
```

## Task 6: 最终验收包

**Files:**
- Modify: `docs/formal-accounting-go-live-checklist.md`
- Modify: `README.md`

- [ ] **Step 1: Record final verification commands**

```powershell
python -m pytest
npm --prefix frontend test
npm --prefix frontend run build
git status --short
```

Expected result:
- `python -m pytest` exits with code 0.
- `npm --prefix frontend test` exits with code 0.
- `npm --prefix frontend run build` exits with code 0.
- `git status --short` has no unexpected files.

- [ ] **Step 2: Record manual accounting acceptance scenarios**

Manual scenarios:
1. 凭证正式过账并生成不可变分录。
2. 多币种分录折算并生成汇兑损益。
3. 客户应收形成账龄并部分核销。
4. 银行流水匹配收款并形成调节表。
5. 固定资产入账、折旧、减值和处置。
6. 工资计提、发放、个税和社保缴纳。
7. 存货采购入库、销售出库和成本结转。
8. 增值税、附加税和所得税底稿生成。
9. 预提摊销和借款利息月结。
10. 合并范围生成抵销分录和合并报表。
11. 电子凭证归档包可导出。
12. 上线门禁全部通过。

- [ ] **Step 3: Commit final checklist**

```powershell
git add docs/formal-accounting-go-live-checklist.md README.md
git commit -m "docs: finalize formal accounting go live checklist"
```

## 验收标准

- 完整性校验覆盖借贷平衡、source key、期间锁定、报表映射和归档链接。
- 迁移支持 dry-run、差异报告和受控 apply。
- 备份清单覆盖正式核算关键数据集。
- 恢复演练可在临时库运行并复查完整性。
- 权限矩阵覆盖职责分离。
- 上线门禁能明确通过、警告或阻塞。
- 前端治理面板可展示上线状态和阻塞原因。
- 最终清单包含自动化测试和手工验收场景。

## 风险控制

- 不删除 MVP 历史数据。
- 不在没有备份和恢复演练的情况下应用迁移。
- 不允许同一人完成迁移执行和上线审批。
- 所有迁移批次、备份、恢复演练和上线门禁读取都写入审计日志。
- 上线前保留并行核对期，正式切换必须可回滚。
