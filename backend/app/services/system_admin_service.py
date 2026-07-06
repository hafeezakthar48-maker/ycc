from datetime import UTC, datetime

from app.models.system_admin import (
    AuditLogCreateRequest,
    AuditLogEntry,
    AuthorizationDecision,
    PermissionItem,
    RoleItem,
    UserItem,
)


PERMISSIONS: tuple[PermissionItem, ...] = (
    PermissionItem(
        code="home.dashboard.read",
        name="查看AI首页",
        module_id="ai-home",
        action="read",
        description="查看经营概况、利润、现金流、库存、税务和AI提示。",
        risk_level="low",
    ),
    PermissionItem(
        code="voucher.create",
        name="新增凭证",
        module_id="finance-center",
        action="write",
        description="新增或导入会计凭证草稿。",
        risk_level="medium",
    ),
    PermissionItem(
        code="voucher.update",
        name="修改凭证",
        module_id="finance-center",
        action="write",
        description="修改未审核的会计凭证。",
        risk_level="medium",
    ),
    PermissionItem(
        code="voucher.review",
        name="审核凭证",
        module_id="finance-center",
        action="approve",
        description="审核或反审核会计凭证。",
        risk_level="high",
    ),
    PermissionItem(
        code="voucher.unreview",
        name="反审核凭证",
        module_id="finance-center",
        action="approve",
        description="将已审核凭证退回草稿状态。",
        risk_level="high",
    ),
    PermissionItem(
        code="voucher.import",
        name="导入凭证",
        module_id="finance-center",
        action="import",
        description="批量导入会计凭证。",
        risk_level="medium",
    ),
    PermissionItem(
        code="voucher.export",
        name="导出凭证",
        module_id="finance-center",
        action="export",
        description="导出凭证中心列表数据。",
        risk_level="medium",
    ),
    PermissionItem(
        code="voucher.attachment.upload",
        name="上传凭证附件",
        module_id="finance-center",
        action="upload",
        description="上传发票、回单、合同等凭证附件。",
        risk_level="medium",
    ),
    PermissionItem(
        code="voucher.post",
        name="过账凭证",
        module_id="finance-center",
        action="post",
        description="将已审核凭证标记为已过账。",
        risk_level="high",
    ),
    PermissionItem(
        code="voucher.unpost",
        name="反过账凭证",
        module_id="finance-center",
        action="unpost",
        description="将已过账凭证退回未过账状态。",
        risk_level="high",
    ),
    PermissionItem(
        code="ledger.read",
        name="查看账簿",
        module_id="finance-center",
        action="read",
        description="查看总账、明细账和科目余额表只读视图。",
        risk_level="medium",
    ),
    PermissionItem(
        code="ledger.period.manage",
        name="管理会计期间",
        module_id="finance-center",
        action="close",
        description="关闭或重开账套会计期间，控制期间内凭证过账。",
        risk_level="high",
    ),
    PermissionItem(
        code="accounting.account.read",
        name="查看正式科目",
        module_id="finance-center",
        action="read",
        description="查看正式会计核算科目表。",
        risk_level="medium",
    ),
    PermissionItem(
        code="accounting.currency.read",
        name="查看币种",
        module_id="finance-center",
        action="read",
        description="查看正式核算支持的币种清单。",
        risk_level="medium",
    ),
    PermissionItem(
        code="accounting.exchange_rate.read",
        name="查看汇率",
        module_id="finance-center",
        action="read",
        description="查看正式核算汇率表。",
        risk_level="medium",
    ),
    PermissionItem(
        code="accounting.exchange_rate.write",
        name="维护汇率",
        module_id="finance-center",
        action="write",
        description="维护正式核算外币兑本位币汇率。",
        risk_level="high",
    ),
    PermissionItem(
        code="accounting.dimension.read",
        name="查看辅助核算",
        module_id="finance-center",
        action="read",
        description="查看客户、供应商、部门、项目等辅助核算维度。",
        risk_level="medium",
    ),
    PermissionItem(
        code="accounting.dimension.write",
        name="维护辅助核算",
        module_id="finance-center",
        action="write",
        description="维护客户、供应商、部门、项目等辅助核算维度主数据。",
        risk_level="high",
    ),
    PermissionItem(
        code="accounting.entry.read",
        name="查看正式分录",
        module_id="finance-center",
        action="read",
        description="查看正式会计分录和分录行。",
        risk_level="high",
    ),
    PermissionItem(
        code="accounting.entry.post",
        name="正式过账",
        module_id="finance-center",
        action="post",
        description="生成不可变正式会计分录。",
        risk_level="high",
    ),
    PermissionItem(
        code="accounting.entry.reverse",
        name="正式冲销",
        module_id="finance-center",
        action="reverse",
        description="通过冲销分录撤销正式分录影响。",
        risk_level="high",
    ),
    PermissionItem(
        code="period_close.view",
        name="查看期间结账",
        module_id="finance-center",
        action="read",
        description="查看期间结账运行记录、检查清单和期末处理结果。",
        risk_level="high",
    ),
    PermissionItem(
        code="period_close.check",
        name="执行结账检查",
        module_id="finance-center",
        action="check",
        description="执行期间结账前置检查清单。",
        risk_level="high",
    ),
    PermissionItem(
        code="period_close.generate",
        name="生成期末分录",
        module_id="finance-center",
        action="generate",
        description="生成折旧、工资、税费、外币重估和损益结转等期末正式分录。",
        risk_level="high",
    ),
    PermissionItem(
        code="period_close.close",
        name="关闭会计期间",
        module_id="finance-center",
        action="close",
        description="在结账检查通过后关闭会计期间。",
        risk_level="high",
    ),
    PermissionItem(
        code="period_close.reopen",
        name="重开会计期间",
        module_id="finance-center",
        action="reopen",
        description="按审计规则重开已关闭的会计期间。",
        risk_level="high",
    ),
    PermissionItem(
        code="fixed_asset.read",
        name="查看固定资产",
        module_id="finance-center",
        action="read",
        description="查看固定资产台账、折旧状态和盘点结果。",
        risk_level="medium",
    ),
    PermissionItem(
        code="fixed_asset.write",
        name="维护固定资产",
        module_id="finance-center",
        action="write",
        description="新增和维护固定资产基础信息。",
        risk_level="medium",
    ),
    PermissionItem(
        code="fixed_asset.depreciate",
        name="计提固定资产折旧",
        module_id="finance-center",
        action="depreciate",
        description="按会计期间自动计算并写入固定资产折旧状态。",
        risk_level="high",
    ),
    PermissionItem(
        code="fixed_asset.dispose",
        name="处置固定资产",
        module_id="finance-center",
        action="dispose",
        description="执行固定资产报废或出售生命周期操作。",
        risk_level="high",
    ),
    PermissionItem(
        code="fixed_asset.inventory",
        name="盘点固定资产",
        module_id="finance-center",
        action="inventory",
        description="记录固定资产盘点位置、保管人和资产状态。",
        risk_level="medium",
    ),
    PermissionItem(
        code="payroll.calculate",
        name="计算工资",
        module_id="finance-center",
        action="calculate",
        description="计算工资、社保、公积金、个税和部门工资分析。",
        risk_level="high",
    ),
    PermissionItem(
        code="statement.generate",
        name="生成财务报表",
        module_id="finance-center",
        action="generate",
        description="生成资产负债表、利润表、现金流量表、所有者权益变动表和管理报表摘要。",
        risk_level="high",
    ),
    PermissionItem(
        code="statement.validate",
        name="校验财务报表",
        module_id="finance-center",
        action="validate",
        description="运行资产负债表平衡、报表公式和现金流项目等结构化校验。",
        risk_level="medium",
    ),
    PermissionItem(
        code="statement.mapping.view",
        name="查看报表映射",
        module_id="finance-center",
        action="read",
        description="查看账套默认报表映射集、映射规则和现金流项目规则。",
        risk_level="medium",
    ),
    PermissionItem(
        code="statement.mapping.manage",
        name="维护报表映射",
        module_id="finance-center",
        action="manage",
        description="维护账套报表映射规则、公式和现金流项目映射。",
        risk_level="high",
    ),
    PermissionItem(
        code="report.export",
        name="导出报表",
        module_id="finance-center",
        action="export",
        description="导出管理报表、Word或PDF文件。",
        risk_level="medium",
    ),
    PermissionItem(
        code="risk.read",
        name="查看风险",
        module_id="risk-center",
        action="read",
        description="查看税务、库存、利润、现金流等风险预警。",
        risk_level="medium",
    ),
    PermissionItem(
        code="knowledge.search",
        name="检索知识库",
        module_id="knowledge-base",
        action="read",
        description="检索政策、制度、流程和案例依据。",
        risk_level="low",
    ),
    PermissionItem(
        code="assistant.ask",
        name="使用AI助手",
        module_id="ai-assistant",
        action="invoke",
        description="向AI助手提问并调用已授权工具。",
        risk_level="medium",
    ),
    PermissionItem(
        code="system.audit.read",
        name="查看审计日志",
        module_id="system-admin",
        action="read",
        description="查看系统操作审计日志。",
        risk_level="high",
    ),
    PermissionItem(
        code="system.role.manage",
        name="管理角色权限",
        module_id="system-admin",
        action="admin",
        description="管理用户角色、权限点和系统策略。",
        risk_level="high",
    ),
    PermissionItem(
        code="platform.client.manage",
        name="管理开放平台客户端",
        module_id="open-platform",
        action="admin",
        description="管理API客户端、Webhook、OAuth2和SDK接入。",
        risk_level="high",
    ),
)

PERMISSION_CODES = [permission.code for permission in PERMISSIONS]

ROLES: tuple[RoleItem, ...] = (
    RoleItem(
        id="super_admin",
        name="系统管理员",
        description="拥有系统管理、审计、财务和开放平台配置权限。",
        permission_codes=PERMISSION_CODES,
    ),
    RoleItem(
        id="finance_manager",
        name="财务主管",
        description="负责凭证、报表、风险查看和AI财务分析。",
        permission_codes=[
            "home.dashboard.read",
            "voucher.create",
            "voucher.update",
            "voucher.review",
            "voucher.unreview",
            "voucher.import",
            "voucher.export",
            "voucher.attachment.upload",
            "voucher.post",
            "voucher.unpost",
            "ledger.read",
            "ledger.period.manage",
            "accounting.account.read",
            "accounting.currency.read",
            "accounting.exchange_rate.read",
            "accounting.exchange_rate.write",
            "accounting.dimension.read",
            "accounting.dimension.write",
            "accounting.entry.read",
            "accounting.entry.post",
            "accounting.entry.reverse",
            "period_close.view",
            "period_close.check",
            "period_close.generate",
            "period_close.close",
            "period_close.reopen",
            "fixed_asset.read",
            "fixed_asset.write",
            "fixed_asset.depreciate",
            "fixed_asset.dispose",
            "fixed_asset.inventory",
            "payroll.calculate",
            "statement.generate",
            "statement.validate",
            "statement.mapping.view",
            "statement.mapping.manage",
            "report.export",
            "risk.read",
            "knowledge.search",
            "assistant.ask",
        ],
    ),
    RoleItem(
        id="auditor",
        name="审计复核员",
        description="负责风险查看、凭证复核和系统审计日志查看。",
        permission_codes=["home.dashboard.read", "ledger.read", "risk.read", "system.audit.read"],
    ),
    RoleItem(
        id="api_integrator",
        name="开放平台集成员",
        description="负责开放平台客户端、Webhook和接口接入配置。",
        permission_codes=["platform.client.manage", "system.audit.read"],
    ),
)

USERS: tuple[UserItem, ...] = (
    UserItem(
        id="u-super-admin",
        name="系统管理员",
        department="信息化",
        role_ids=["super_admin"],
        active=True,
    ),
    UserItem(
        id="u-finance-manager",
        name="财务主管",
        department="财务部",
        role_ids=["finance_manager"],
        active=True,
    ),
    UserItem(
        id="u-auditor",
        name="审计复核员",
        department="内控部",
        role_ids=["auditor"],
        active=True,
    ),
    UserItem(
        id="u-api-integrator",
        name="接口集成员",
        department="信息化",
        role_ids=["api_integrator"],
        active=True,
    ),
)

_audit_logs: list[AuditLogEntry] = []
_audit_sequence = 0


def reset_system_admin_store() -> None:
    global _audit_logs, _audit_sequence
    _audit_logs = []
    _audit_sequence = 0


def list_permissions() -> list[PermissionItem]:
    return list(PERMISSIONS)


def list_roles() -> list[RoleItem]:
    return list(ROLES)


def list_users() -> list[UserItem]:
    return list(USERS)


def authorize(request_user_id: str, permission_code: str) -> AuthorizationDecision:
    user = next((item for item in USERS if item.id == request_user_id and item.active), None)
    if user is None:
        return AuthorizationDecision(
            allowed=False,
            user_id=request_user_id,
            permission_code=permission_code,
            matched_role_ids=[],
            reason="用户不存在或已停用",
        )

    if permission_code not in PERMISSION_CODES:
        return AuthorizationDecision(
            allowed=False,
            user_id=request_user_id,
            permission_code=permission_code,
            matched_role_ids=[],
            reason="权限不存在",
        )

    matched_role_ids = [
        role.id
        for role in ROLES
        if role.id in user.role_ids and permission_code in role.permission_codes
    ]
    if matched_role_ids:
        return AuthorizationDecision(
            allowed=True,
            user_id=request_user_id,
            permission_code=permission_code,
            matched_role_ids=matched_role_ids,
            reason="已授权",
        )

    return AuthorizationDecision(
        allowed=False,
        user_id=request_user_id,
        permission_code=permission_code,
        matched_role_ids=[],
        reason="权限不足",
    )


def record_audit_log(request: AuditLogCreateRequest) -> AuditLogEntry:
    global _audit_sequence
    _audit_sequence += 1
    entry = AuditLogEntry(
        id=f"audit-{_audit_sequence:06d}",
        actor_id=request.actor_id,
        module_id=request.module_id,
        event=request.event,
        target_id=request.target_id,
        result=request.result,
        metadata=request.metadata,
        created_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )
    _audit_logs.insert(0, entry)
    return entry


def list_audit_logs(
    module_id: str | None = None,
    actor_id: str | None = None,
    event: str | None = None,
    limit: int = 50,
) -> list[AuditLogEntry]:
    logs = _audit_logs
    if module_id is not None:
        logs = [log for log in logs if log.module_id == module_id]
    if actor_id is not None:
        logs = [log for log in logs if log.actor_id == actor_id]
    if event is not None:
        logs = [log for log in logs if log.event == event]
    return logs[:limit]
