import CashFlowChart from "../charts/CashFlowChart";
import ExpensePieChart from "../charts/ExpensePieChart";
import ProfitWaterfallChart from "../charts/ProfitWaterfallChart";
import RiskHeatmap from "../charts/RiskHeatmap";
import TrendChart from "../charts/TrendChart";
import type { DashboardOverview, ManagementReport } from "../types/dashboard";
import type { HomeDashboard } from "../types/homeDashboard";
import type { NavigationOsModule } from "../types/moduleRegistry";
import AccountingArchivePanel from "./AccountingArchivePanel";
import AccountingGovernancePanel from "./AccountingGovernancePanel";
import AccrualAmortizationPanel from "./AccrualAmortizationPanel";
import AuditReviewPanel from "./AuditReviewPanel";
import BankReconciliationPanel from "./BankReconciliationPanel";
import ConsolidationPanel from "./ConsolidationPanel";
import ECommerceProfitPanel from "./ECommerceProfitPanel";
import FinanceQaPanel from "./FinanceQaPanel";
import FinancialStatementPanel from "./FinancialStatementPanel";
import FixedAssetPanel from "./FixedAssetPanel";
import HomeDashboardPanel from "./HomeDashboardPanel";
import InvoiceOcrPanel from "./InvoiceOcrPanel";
import InventoryAccountingPanel from "./InventoryAccountingPanel";
import LedgerPanel from "./LedgerPanel";
import MetricCard from "./MetricCard";
import PayrollPanel from "./PayrollPanel";
import PeriodClosePanel from "./PeriodClosePanel";
import PolicyLibraryPanel from "./PolicyLibraryPanel";
import ReceivablePayablePanel from "./ReceivablePayablePanel";
import ReportPanel from "./ReportPanel";
import RiskPanel from "./RiskPanel";
import StatementArchivePanel from "./StatementArchivePanel";
import StatementMappingPanel from "./StatementMappingPanel";
import SystemAdminPanel from "./SystemAdminPanel";
import TaxAccountingPanel from "./TaxAccountingPanel";
import VoucherCenterPanel from "./VoucherCenterPanel";
import VoucherDraftPanel from "./VoucherDraftPanel";

interface DashboardLayoutProps {
  modules: NavigationOsModule[];
  homeDashboard: HomeDashboard;
  overview: DashboardOverview;
  report: ManagementReport;
  onOpenDataEntry: () => void;
}

type ModuleById = Record<string, NavigationOsModule>;

export default function DashboardLayout({ modules, homeDashboard, overview, report, onOpenDataEntry }: DashboardLayoutProps) {
  const moduleById = Object.fromEntries(modules.map((module) => [module.id, module])) as ModuleById;

  return (
    <div className="shell">
      <aside className="sidebar os-sidebar">
        <div className="brand">
          <span>CF</span>
          <strong>Finance AI OS</strong>
        </div>
        <nav className="module-nav" aria-label="China Finance AI OS 一级模块">
          {modules.map((module, index) => (
            <div className="module-nav-group" key={module.id}>
              <a className={index === 0 ? "active" : ""} href={`#${module.id}`}>
                <span>{module.label}</span>
                <small className={module.status === "MVP" ? "status-pill" : "status-pill status-pill--planned"}>
                  {module.status}
                </small>
              </a>
              <div className="module-nav-links">
                {module.items.slice(0, 3).map((item) => (
                  <a href={`#${item.anchor}`} key={`${module.id}-${item.anchor}`}>
                    {item.label}
                  </a>
                ))}
              </div>
            </div>
          ))}
        </nav>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">China Finance AI OS</p>
            <h1>{overview.company_name}智能财务操作系统</h1>
          </div>
          <div className="topbar-actions">
            <span>{overview.period}</span>
            <button type="button" className="button-secondary" onClick={onOpenDataEntry}>导入/填写数据</button>
            <button type="button">生成报告</button>
          </div>
        </header>

        <ModuleMap modules={modules} />

        <ModuleRoadmap module={moduleById["ai-home"]} />
        <HomeDashboardPanel dashboard={homeDashboard} />

        <section id="bi-center" className="module-band">
          <ModuleSectionHeader
            eyebrow="BI数据中心"
            title="经营驾驶舱"
            status="MVP"
          />
          <ModuleRoadmap module={moduleById["bi-center"]} />
          <section id="overview" className="metric-grid">
            {overview.metrics.map((metric) => (
              <MetricCard key={metric.key} metric={metric} />
            ))}
          </section>
          <section id="risk-heatmap" className="panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">风险分布</span>
                <h2>风险热力图</h2>
              </div>
            </div>
            <RiskHeatmap data={overview.risk_heatmap} />
          </section>
        </section>

        <section id="finance-center" className="module-band">
          <ModuleSectionHeader
            eyebrow="AI财务中心"
            title="凭证、审核与报表"
            status="MVP"
          />
          <ModuleRoadmap module={moduleById["finance-center"]} />
          <VoucherCenterPanel />
          <AccountingArchivePanel period={overview.period} />
          <AccountingGovernancePanel period={overview.period} />
          <LedgerPanel period={overview.period} />
          <ReceivablePayablePanel period={overview.period} />
          <BankReconciliationPanel period={overview.period} />
          <InventoryAccountingPanel period={overview.period} />
          <TaxAccountingPanel period={overview.period} />
          <AccrualAmortizationPanel period={overview.period} />
          <ConsolidationPanel period={overview.period} />
          <FixedAssetPanel period={overview.period} />
          <PayrollPanel period={overview.period} />
          <PeriodClosePanel period={overview.period} />
          <StatementMappingPanel />
          <FinancialStatementPanel period={overview.period} />
          <StatementArchivePanel period={overview.period} />
          <VoucherDraftPanel />
          <AuditReviewPanel />
          <div id="report">
            <ReportPanel report={report} />
          </div>
        </section>

        <section id="analysis-center" className="module-band">
          <ModuleSectionHeader
            eyebrow="AI经营分析中心"
            title="趋势、结构与经营判断"
            status="MVP"
          />
          <ModuleRoadmap module={moduleById["analysis-center"]} />
          <section className="content-grid">
            <section id="profit" className="panel panel--wide">
              <div className="panel-header">
                <div>
                  <span className="eyebrow">趋势分析</span>
                  <h2>收入、成本、净利润趋势</h2>
                </div>
              </div>
              <TrendChart series={overview.trend_series} />
            </section>

            <section className="panel">
              <div className="panel-header">
                <div>
                  <span className="eyebrow">费用分析</span>
                  <h2>费用结构</h2>
                </div>
              </div>
              <ExpensePieChart data={overview.expense_structure} />
            </section>

            <section id="cashflow" className="panel panel--wide">
              <div className="panel-header">
                <div>
                  <span className="eyebrow">资金分析</span>
                  <h2>现金流趋势</h2>
                </div>
              </div>
              <CashFlowChart series={overview.cash_flow_series} />
            </section>

            <section className="panel">
              <div className="panel-header">
                <div>
                  <span className="eyebrow">利润形成</span>
                  <h2>利润瀑布</h2>
                </div>
              </div>
              <ProfitWaterfallChart data={overview.profit_waterfall} />
            </section>

            <section id="ai-summary" className="panel ai-summary">
              <div className="panel-header">
                <div>
                  <span className="eyebrow">AI摘要</span>
                  <h2>经营判断</h2>
                </div>
              </div>
              <p>{overview.ai_summary}</p>
            </section>
          </section>
        </section>

        <section id="ecommerce-center" className="module-band">
          <ModuleSectionHeader
            eyebrow="电商分析中心"
            title="平台利润与成本拆解"
            status="MVP"
          />
          <ModuleRoadmap module={moduleById["ecommerce-center"]} />
          <ECommerceProfitPanel />
        </section>

        <section id="ocr-center" className="module-band">
          <ModuleSectionHeader
            eyebrow="OCR识别中心"
            title="票据识别与凭证入口"
            status="MVP"
          />
          <ModuleRoadmap module={moduleById["ocr-center"]} />
          <InvoiceOcrPanel />
        </section>

        <section id="knowledge-base" className="module-band">
          <ModuleSectionHeader
            eyebrow="企业知识库"
            title="政策、制度与来源追踪"
            status="MVP"
          />
          <ModuleRoadmap module={moduleById["knowledge-base"]} />
          <PolicyLibraryPanel />
        </section>

        <section id="tax-center" className="module-band">
          <ModuleSectionHeader
            eyebrow="AI税务中心"
            title="政策依据与税务风险"
            status="MVP"
          />
          <ModuleRoadmap module={moduleById["tax-center"]} />
          <div className="module-two-column">
            <ModuleInfoPanel
              title="政策依据"
              body="税率、优惠、减免和风险提示统一引用企业知识库中的政策来源。"
              actionHref="#policy-library"
              actionLabel="查看法规库"
            />
            <ModuleInfoPanel
              title="税务风险"
              body="税负率、发票异常和凭证税额方向进入风险预警中心闭环跟踪。"
              actionHref="#risk"
              actionLabel="查看风险"
            />
          </div>
        </section>

        <section id="ai-assistant" className="module-band">
          <ModuleSectionHeader
            eyebrow="AI智能助手"
            title="财务问答与工具调用"
            status="MVP"
          />
          <ModuleRoadmap module={moduleById["ai-assistant"]} />
          <FinanceQaPanel />
        </section>

        <section id="risk-center" className="module-band">
          <ModuleSectionHeader
            eyebrow="风险预警中心"
            title="风险发现与闭环跟踪"
            status="MVP"
          />
          <ModuleRoadmap module={moduleById["risk-center"]} />
          <div id="risk">
            <RiskPanel risks={overview.risks} period={overview.period} />
          </div>
        </section>

        <section id="system-admin" className="module-band">
          <ModuleSectionHeader
            eyebrow="系统管理"
            title="权限、账套与审计"
            status="规划"
          />
          <ModuleRoadmap module={moduleById["system-admin"]} />
          <SystemAdminPanel />
        </section>

        <section id="open-platform" className="module-band">
          <ModuleSectionHeader
            eyebrow="开放平台"
            title="API、Webhook 与集成"
            status="规划"
          />
          <ModuleRoadmap module={moduleById["open-platform"]} />
          <ModuleInfoPanel
            title="开放接口"
            body="后续承载 REST API、Webhook、OAuth2、OpenAPI、SDK、限流和版本管理。"
          />
        </section>
      </main>
    </div>
  );
}

function ModuleMap({ modules }: { modules: NavigationOsModule[] }) {
  return (
    <section className="module-map" aria-label="China Finance AI OS 十二个一级模块">
      {modules.map((module) => (
        <a className="module-card" href={`#${module.id}`} key={module.id}>
          <div>
            <span className="eyebrow">{module.status}</span>
            <strong>{module.label}</strong>
          </div>
          <small>{module.apiPrefixes?.[0] ?? `${module.items.length} 个入口`}</small>
        </a>
      ))}
    </section>
  );
}

function ModuleSectionHeader({
  eyebrow,
  title,
  status
}: {
  eyebrow: string;
  title: string;
  status: NavigationOsModule["status"];
}) {
  return (
    <div className="module-section-header">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
      </div>
      <span className={status === "MVP" ? "status-pill" : "status-pill status-pill--planned"}>{status}</span>
    </div>
  );
}

function ModuleRoadmap({ module }: { module: NavigationOsModule }) {
  return (
    <section className="module-roadmap" aria-label={`${module.label} FRD 规划接入点`}>
      <div>
        <span className="eyebrow">下一步接入点</span>
        <p>{module.nextIntegration}</p>
      </div>
      <div className="roadmap-tags">
        {module.roadmap.slice(0, 9).map((item) => (
          <span key={`${module.id}-${item}`}>{item}</span>
        ))}
      </div>
      {module.apiPrefixes ? (
        <div className="module-governance" aria-label={`${module.label} API 治理信息`}>
          <span>API {module.apiPrefixes.join(" / ")}</span>
          <span>{module.requiresPermission ? "权限控制" : "开放访问"}</span>
          <span>限流 {module.rateLimitPolicy}</span>
        </div>
      ) : null}
    </section>
  );
}

function ModuleInfoPanel({
  title,
  body,
  actionHref,
  actionLabel
}: {
  title: string;
  body: string;
  actionHref?: string;
  actionLabel?: string;
}) {
  return (
    <section className="module-info-panel">
      <h3>{title}</h3>
      <p>{body}</p>
      {actionHref && actionLabel ? <a href={actionHref}>{actionLabel}</a> : null}
    </section>
  );
}
