import { useEffect, useMemo, useState } from "react";
import {
  fetchAuditLogs,
  fetchPermissions,
  fetchRoles,
  fetchUsers
} from "../services/systemAdminApi";
import type {
  AuditLogEntry,
  PermissionItem,
  RoleItem,
  UserItem
} from "../types/systemAdmin";

function riskLabel(level: PermissionItem["risk_level"]) {
  if (level === "high") {
    return "高风险";
  }
  if (level === "medium") {
    return "中风险";
  }
  return "低风险";
}

export default function SystemAdminPanel() {
  const [permissions, setPermissions] = useState<PermissionItem[]>([]);
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [users, setUsers] = useState<UserItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadSystemAdmin() {
      try {
        const [permissionPayload, rolePayload, userPayload, logPayload] = await Promise.all([
          fetchPermissions(),
          fetchRoles(),
          fetchUsers(),
          fetchAuditLogs(null, 8)
        ]);

        if (!cancelled) {
          setPermissions(permissionPayload);
          setRoles(rolePayload);
          setUsers(userPayload);
          setAuditLogs(logPayload);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "系统管理数据加载失败");
        }
      }
    }

    loadSystemAdmin();

    return () => {
      cancelled = true;
    };
  }, []);

  const highRiskPermissions = useMemo(
    () => permissions.filter((permission) => permission.risk_level === "high"),
    [permissions]
  );
  const activeUsers = users.filter((user) => user.active);

  return (
    <section className="system-admin-section">
      <div className="section-heading">
        <div>
          <span className="eyebrow">系统管理底座</span>
          <h2>角色、权限点与审计日志</h2>
        </div>
        <div className="qa-status-strip">
          <span>权限控制</span>
          <span>审计日志</span>
          <span>角色模型</span>
        </div>
      </div>

      {error ? <p className="inline-error">{error}</p> : null}

      <div className="system-admin-summary">
        <article>
          <span>权限点</span>
          <strong>{permissions.length}</strong>
        </article>
        <article>
          <span>高风险权限</span>
          <strong>{highRiskPermissions.length}</strong>
        </article>
        <article>
          <span>角色</span>
          <strong>{roles.length}</strong>
        </article>
        <article>
          <span>启用用户</span>
          <strong>{activeUsers.length}</strong>
        </article>
      </div>

      <div className="system-admin-grid">
        <section className="panel system-admin-card">
          <div className="panel-header">
            <div>
              <span className="eyebrow">权限点</span>
              <h3>按模块登记</h3>
            </div>
          </div>
          <div className="system-list">
            {permissions.slice(0, 8).map((permission) => (
              <article key={permission.code}>
                <div>
                  <strong>{permission.name}</strong>
                  <small>{permission.code} · {permission.module_id}</small>
                </div>
                <span className={`risk-badge risk-badge--${permission.risk_level}`}>
                  {riskLabel(permission.risk_level)}
                </span>
              </article>
            ))}
          </div>
        </section>

        <section className="panel system-admin-card">
          <div className="panel-header">
            <div>
              <span className="eyebrow">角色</span>
              <h3>权限组合</h3>
            </div>
          </div>
          <div className="system-list">
            {roles.map((role) => (
              <article key={role.id}>
                <div>
                  <strong>{role.name}</strong>
                  <small>{role.description}</small>
                </div>
                <span>{role.permission_codes.length}项</span>
              </article>
            ))}
          </div>
        </section>

        <section className="panel system-admin-card">
          <div className="panel-header">
            <div>
              <span className="eyebrow">用户</span>
              <h3>演示账号</h3>
            </div>
          </div>
          <div className="system-list">
            {users.map((user) => (
              <article key={user.id}>
                <div>
                  <strong>{user.name}</strong>
                  <small>{user.department} · {user.role_ids.join(" / ")}</small>
                </div>
                <span>{user.active ? "启用" : "停用"}</span>
              </article>
            ))}
          </div>
        </section>

        <section className="panel system-admin-card">
          <div className="panel-header">
            <div>
              <span className="eyebrow">审计日志</span>
              <h3>最近操作</h3>
            </div>
          </div>
          <div className="system-list">
            {auditLogs.length > 0 ? auditLogs.map((log) => (
              <article key={log.id}>
                <div>
                  <strong>{log.event}</strong>
                  <small>{log.actor_id} · {log.module_id} · {log.target_id}</small>
                </div>
                <span>{log.result}</span>
              </article>
            )) : <p className="muted">暂无审计日志，后续业务接口接入后会自动沉淀操作记录。</p>}
          </div>
        </section>
      </div>
    </section>
  );
}
