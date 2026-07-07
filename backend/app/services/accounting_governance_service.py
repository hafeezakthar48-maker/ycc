from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException

from app.models.accounting_governance import (
    FormalAccountingGoLiveGate,
    FormalAccountingPermissionMatrix,
    GoLiveGateCheck,
    GoLiveGateStatus,
)
from app.services.backup_service import get_latest_backup_manifest, get_latest_restore_rehearsal
from app.services.integrity_check_service import run_accounting_integrity_checks
from app.services.migration_service import preview_mvp_voucher_migration
from app.services.system_admin_service import list_permissions, list_roles


REQUIRED_PERMISSIONS = [
    "voucher.review",
    "voucher.post",
    "ledger.read",
    "period_close.close",
    "statement.generate",
    "bank_reconciliation.confirm",
    "receivable_payable.settle",
    "tax_accounting.accrue",
    "accounting_governance.read",
    "accounting_migration.preview",
    "accounting_migration.apply",
    "accounting_backup.create",
    "accounting_governance.approve_go_live",
]

SEGREGATION_RULES = [
    "同一用户不能同时完成制单、审核和正式过账。",
    "迁移执行人不能审批上线。",
    "备份恢复演练通过前不能切换正式核算来源。",
]


def build_formal_accounting_permission_matrix() -> FormalAccountingPermissionMatrix:
    available_permissions = sorted(permission.code for permission in list_permissions())
    available_set = set(available_permissions)
    missing_permissions = [permission for permission in REQUIRED_PERMISSIONS if permission not in available_set]
    role_coverage = {
        permission: [
            role.id
            for role in list_roles()
            if permission in role.permission_codes
        ]
        for permission in REQUIRED_PERMISSIONS
    }
    return FormalAccountingPermissionMatrix(
        required_permissions=list(REQUIRED_PERMISSIONS),
        available_permissions=available_permissions,
        missing_permissions=missing_permissions,
        critical_missing_permissions=missing_permissions,
        role_coverage=role_coverage,
        segregation_rules=list(SEGREGATION_RULES),
    )


def evaluate_formal_accounting_go_live_gate(
    account_set_id: str = "default",
    period: str = "2026-06",
    regression_results: dict[str, str] | None = None,
) -> FormalAccountingGoLiveGate:
    checks = [
        _integrity_gate(account_set_id, period),
        _migration_gate(account_set_id, period),
        _backup_restore_gate(account_set_id, period),
        _permission_matrix_gate(),
        _regression_gate(regression_results or {}),
    ]
    return FormalAccountingGoLiveGate(
        account_set_id=account_set_id,
        period=period,
        status=_overall_gate_status(checks),
        generated_at=_now_iso(),
        checks=checks,
        blockers=[check.gate_code for check in checks if check.status == "blocked"],
        warnings=[check.gate_code for check in checks if check.status == "warning"],
        regression_results=regression_results or {},
    )


def _integrity_gate(account_set_id: str, period: str) -> GoLiveGateCheck:
    report = run_accounting_integrity_checks(account_set_id, period)
    if report.overall_status == "fail":
        return GoLiveGateCheck(
            gate_code="integrity_checks",
            gate_name="完整性校验",
            status="blocked",
            message="完整性校验存在失败项，不能上线。",
        )
    if report.overall_status == "warning":
        return GoLiveGateCheck(
            gate_code="integrity_checks",
            gate_name="完整性校验",
            status="warning",
            message="完整性校验存在警告项，上线前需要确认豁免或补齐材料。",
        )
    return GoLiveGateCheck(
        gate_code="integrity_checks",
        gate_name="完整性校验",
        status="pass",
        message="完整性校验通过。",
    )


def _migration_gate(account_set_id: str, period: str) -> GoLiveGateCheck:
    preview = preview_mvp_voucher_migration(account_set_id=account_set_id, period=period, actor_id="go-live-gate")
    if preview.blocked_count:
        return GoLiveGateCheck(
            gate_code="migration_dry_run",
            gate_name="迁移 dry-run",
            status="blocked",
            message="迁移预览存在阻塞凭证，不能上线。",
        )
    return GoLiveGateCheck(
        gate_code="migration_dry_run",
        gate_name="迁移 dry-run",
        status="pass",
        message="迁移预览无阻塞项。",
    )


def _backup_restore_gate(account_set_id: str, period: str) -> GoLiveGateCheck:
    try:
        manifest = get_latest_backup_manifest(account_set_id, period)
        rehearsal = get_latest_restore_rehearsal(account_set_id, period)
    except HTTPException:
        return GoLiveGateCheck(
            gate_code="backup_restore_rehearsal",
            gate_name="备份恢复演练",
            status="blocked",
            message="缺少备份清单或恢复演练结果。",
        )
    if rehearsal.backup_manifest_id != manifest.backup_manifest_id:
        return GoLiveGateCheck(
            gate_code="backup_restore_rehearsal",
            gate_name="备份恢复演练",
            status="blocked",
            message="最新恢复演练未基于最新备份清单。",
        )
    if rehearsal.status != "passed":
        return GoLiveGateCheck(
            gate_code="backup_restore_rehearsal",
            gate_name="备份恢复演练",
            status="blocked",
            message="恢复演练未通过。",
        )
    return GoLiveGateCheck(
        gate_code="backup_restore_rehearsal",
        gate_name="备份恢复演练",
        status="pass",
        message="备份清单和恢复演练通过。",
    )


def _permission_matrix_gate() -> GoLiveGateCheck:
    matrix = build_formal_accounting_permission_matrix()
    if matrix.critical_missing_permissions:
        return GoLiveGateCheck(
            gate_code="permission_matrix",
            gate_name="权限矩阵",
            status="blocked",
            message="权限矩阵缺少关键权限点。",
        )
    return GoLiveGateCheck(
        gate_code="permission_matrix",
        gate_name="权限矩阵",
        status="pass",
        message="权限矩阵覆盖上线关键权限和职责分离规则。",
    )


def _regression_gate(regression_results: dict[str, str]) -> GoLiveGateCheck:
    required_commands = ["backend_tests", "frontend_tests", "frontend_build"]
    missing = [command for command in required_commands if command not in regression_results]
    failed = [command for command in required_commands if regression_results.get(command) not in {"pass", "passed"}]
    if missing or failed:
        return GoLiveGateCheck(
            gate_code="regression_commands",
            gate_name="回归验证命令",
            status="blocked",
            message="后端测试、前端测试或生产构建尚未全部通过。",
        )
    return GoLiveGateCheck(
        gate_code="regression_commands",
        gate_name="回归验证命令",
        status="pass",
        message="后端测试、前端测试和生产构建均已通过。",
    )


def _overall_gate_status(checks: list[GoLiveGateCheck]) -> GoLiveGateStatus:
    if any(check.status == "blocked" for check in checks):
        return "blocked"
    if any(check.status == "warning" for check in checks):
        return "warning"
    return "pass"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
