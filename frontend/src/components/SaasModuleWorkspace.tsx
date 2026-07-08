import type { ReactNode } from "react";
import { Button, Tag, Typography } from "antd";
import type { ButtonProps } from "antd";

const { Text, Title, Paragraph } = Typography;

export interface ModuleSummaryItem {
  label: string;
  value: string;
  helper: string;
  status?: "normal" | "warning" | "danger";
}

export interface ModuleStatusItem {
  label: string;
  value: string;
  tone?: "normal" | "processing" | "warning" | "danger";
}

export interface ModuleActionItem {
  label: string;
  href?: string;
  onClick?: () => void;
  type?: ButtonProps["type"];
}

interface SaasModuleWorkspaceProps {
  id: string;
  eyebrow: string;
  title: string;
  description: string;
  summaryItems: ModuleSummaryItem[];
  statusItems: ModuleStatusItem[];
  primaryActions: ModuleActionItem[];
  children: ReactNode;
}

export default function SaasModuleWorkspace({
  id,
  eyebrow,
  title,
  description,
  summaryItems,
  statusItems,
  primaryActions,
  children
}: SaasModuleWorkspaceProps) {
  return (
    <section id={id} className="saas-section module-workspace">
      <div className="module-workspace__header">
        <div>
          <Text className="eyebrow">{eyebrow}</Text>
          <Title level={3}>{title}</Title>
          <Paragraph>{description}</Paragraph>
        </div>
        <div className="module-action-bar">
          {primaryActions.map((action) => (
            <Button key={action.label} type={action.type ?? "default"} href={action.href} onClick={action.onClick}>
              {action.label}
            </Button>
          ))}
        </div>
      </div>

      <div className="module-summary-grid">
        {summaryItems.map((item) => (
          <article className={`module-summary-card module-summary-card--${item.status ?? "normal"}`} key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            <small>{item.helper}</small>
          </article>
        ))}
      </div>

      <div className="module-workspace__body">
        <aside className="module-status-list" aria-label={`${title}状态队列`}>
          <Text className="eyebrow">状态队列</Text>
          {statusItems.map((item) => (
            <div className="module-status-list__item" key={item.label}>
              <span>{item.label}</span>
              <Tag className={`module-status-tag module-status-tag--${item.tone ?? "normal"}`}>{item.value}</Tag>
            </div>
          ))}
        </aside>
        <div className="module-workspace__content">{children}</div>
      </div>
    </section>
  );
}
