import {
  AppstoreOutlined,
  BarChartOutlined,
  BellOutlined,
  FileDoneOutlined,
  FileSearchOutlined,
  HomeOutlined,
  RobotOutlined,
  SearchOutlined,
  SettingOutlined,
  SafetyCertificateOutlined,
  UserOutlined
} from "@ant-design/icons";
import { Avatar, Badge, Button, Card, Drawer, Input, Layout, Menu, Space, Tag, Typography } from "antd";
import type { MenuProps } from "antd";
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
import AIFinanceAdvisor from "./AIFinanceAdvisor";
import BankReconciliationPanel from "./BankReconciliationPanel";
import ConsolidationPanel from "./ConsolidationPanel";
import FinancialStatementPanel from "./FinancialStatementPanel";
import FixedAssetPanel from "./FixedAssetPanel";
import HomeDashboardPanel from "./HomeDashboardPanel";
import InvoiceOcrPanel from "./InvoiceOcrPanel";
import InventoryAccountingPanel from "./InventoryAccountingPanel";
import LedgerPanel from "./LedgerPanel";
import PayrollPanel from "./PayrollPanel";
import PeriodClosePanel from "./PeriodClosePanel";
import ReceivablePayablePanel from "./ReceivablePayablePanel";
import ReportPanel from "./ReportPanel";
import RiskPanel from "./RiskPanel";
import SaasModuleWorkspace from "./SaasModuleWorkspace";
import StatementArchivePanel from "./StatementArchivePanel";
import StatementMappingPanel from "./StatementMappingPanel";
import SystemAdminPanel from "./SystemAdminPanel";
import TaxAccountingPanel from "./TaxAccountingPanel";
import UpdateCenterPanel from "./UpdateCenterPanel";
import VoucherCenterPanel from "./VoucherCenterPanel";
import { useState } from "react";

const { Header, Sider, Content } = Layout;
const { Text, Title } = Typography;

interface DashboardLayoutProps {
  modules: NavigationOsModule[];
  homeDashboard: HomeDashboard;
  overview: DashboardOverview;
  report: ManagementReport;
  onOpenDataEntry: () => void;
}

const navigationItems: MenuProps["items"] = [
  { key: "ai-home", icon: <HomeOutlined />, label: <a href="#ai-home">首页 Dashboard</a> },
  { key: "analysis-center", icon: <BarChartOutlined />, label: <a href="#analysis-center">智能财务分析</a> },
  { key: "invoice-center", icon: <FileSearchOutlined />, label: <a href="#invoice-center">发票管理</a> },
  { key: "tax-risk-center", icon: <SafetyCertificateOutlined />, label: <a href="#tax-risk-center">税务风险检测</a> },
  { key: "statement-center", icon: <FileDoneOutlined />, label: <a href="#statement-center">财务报表</a> },
  { key: "data-center", icon: <AppstoreOutlined />, label: <a href="#data-center">数据分析</a> },
  { key: "ai-advisor", icon: <RobotOutlined />, label: <a href="#ai-advisor">AI 财务顾问</a> },
  { key: "company-settings", icon: <SettingOutlined />, label: <a href="#company-settings">企业设置</a> }
];

export default function DashboardLayout({ homeDashboard, overview, report, onOpenDataEntry }: DashboardLayoutProps) {
  const [isAiDrawerOpen, setIsAiDrawerOpen] = useState(false);

  return (
    <Layout className="saas-shell">
      <Sider width={240} className="saas-sider">
        <div className="saas-brand">
          <span className="brand-mark" aria-hidden="true">
            <span className="brand-mark__sheet" />
            <span className="brand-mark__node" />
          </span>
          <div>
            <strong>中国财务 AI 助手</strong>
            <Text type="secondary">Enterprise Finance Copilot</Text>
          </div>
        </div>
        <Menu mode="inline" defaultSelectedKeys={["ai-home"]} items={navigationItems} className="saas-menu" />
      </Sider>

      <Layout>
        <Header className="saas-header">
          <Input
            className="global-search"
            prefix={<SearchOutlined />}
            placeholder="搜索发票、凭证、报表、风险"
            allowClear
          />
          <Space size={12} className="header-actions">
            <Button type="text" icon={<Badge dot><BellOutlined /></Badge>}>消息提醒</Button>
            <Button type="primary" icon={<RobotOutlined />} onClick={() => setIsAiDrawerOpen(true)}>AI助手</Button>
            <Space className="user-chip">
              <Avatar size={32} icon={<UserOutlined />} />
              <span>财务经理</span>
            </Space>
          </Space>
        </Header>

        <Content className="saas-content">
          <section className="page-hero">
            <div>
              <Text className="eyebrow">企业经营驾驶舱</Text>
              <Title level={2}>{overview.company_name} 智能财务工作台</Title>
              <Text type="secondary">以风险、现金流和利润质量为核心，减少财务人员查找路径。</Text>
            </div>
            <Space wrap>
              <Tag color="blue">{overview.period}</Tag>
              <Button onClick={onOpenDataEntry}>导入/填写数据</Button>
              <Button type="primary">生成报告</Button>
            </Space>
          </section>

          <HomeDashboardPanel
            dashboard={homeDashboard}
            overview={overview}
            report={report}
            onOpenDataEntry={onOpenDataEntry}
            onOpenAiAdvisor={() => setIsAiDrawerOpen(true)}
          />

          <section id="analysis-center" className="saas-section">
            <SectionHeading eyebrow="智能财务分析" title="收入、成本、利润与现金流趋势" />
            <div className="saas-grid saas-grid--two">
              <Card title="经营趋势">
                <TrendChart series={overview.trend_series} />
              </Card>
              <Card title="成本结构">
                <ExpensePieChart data={overview.expense_structure} />
              </Card>
              <Card title="现金流趋势">
                <CashFlowChart series={overview.cash_flow_series} />
              </Card>
              <Card title="利润形成">
                <ProfitWaterfallChart data={overview.profit_waterfall} />
              </Card>
            </div>
          </section>

          <SaasModuleWorkspace
            id="invoice-center"
            eyebrow="发票管理"
            title="发票处理中心"
            description="把票据导入、OCR 识别、异常复核和凭证入口放在同一个工作台，减少财务人员在菜单间来回跳转。"
            summaryItems={[
              { label: "待识别票据", value: "18", helper: "今日新增 6 张", status: "warning" },
              { label: "识别准确率", value: "96.8%", helper: "供应商与税额字段优先校验" },
              { label: "异常发票", value: "4", helper: "抬头、税率、重复票据待复核", status: "danger" },
              { label: "凭证转化", value: "12", helper: "可直接生成凭证草稿" }
            ]}
            statusItems={[
              { label: "OCR 队列", value: "自动识别中", tone: "processing" },
              { label: "风险校验", value: "4 条预警", tone: "warning" },
              { label: "凭证入口", value: "可生成", tone: "normal" }
            ]}
            primaryActions={[
              { label: "导入发票", type: "primary", onClick: onOpenDataEntry },
              { label: "查看异常", href: "#tax-risk-center" },
              { label: "AI 解释", onClick: () => setIsAiDrawerOpen(true) }
            ]}
          >
            <InvoiceOcrPanel />
          </SaasModuleWorkspace>

          <SaasModuleWorkspace
            id="tax-risk-center"
            eyebrow="税务风险检测"
            title="税务风险驾驶舱"
            description="把税负波动、票据异常、凭证口径和闭环处理放到同一视图，打开模块即可看到最该处理的事项。"
            summaryItems={[
              { label: "风险闭环", value: `${overview.risks.length}`, helper: "按风险等级自动排序", status: overview.risks.length ? "warning" : "normal" },
              { label: "高风险事项", value: `${overview.risks.filter((risk) => risk.level >= 3).length}`, helper: "需复核政策依据", status: "danger" },
              { label: "税负口径", value: "已校验", helper: "销项、进项、所得税联动" },
              { label: "处理时效", value: "2 天", helper: "建议本周内完成复核", status: "warning" }
            ]}
            statusItems={[
              { label: "热力图", value: "已生成", tone: "normal" },
              { label: "政策依据", value: "待复核", tone: "warning" },
              { label: "闭环任务", value: "处理中", tone: "processing" }
            ]}
            primaryActions={[
              { label: "AI 分析风险", type: "primary", onClick: () => setIsAiDrawerOpen(true) },
              { label: "查看发票", href: "#invoice-center" },
              { label: "生成处理清单", href: "#data-center" }
            ]}
          >
            <div className="saas-grid saas-grid--two">
              <Card title="风险热力图">
                <RiskHeatmap data={overview.risk_heatmap} />
              </Card>
              <Card title="风险提醒">
                <RiskPanel risks={overview.risks} period={overview.period} />
              </Card>
            </div>
            <TaxAccountingPanel period={overview.period} />
          </SaasModuleWorkspace>

          <SaasModuleWorkspace
            id="statement-center"
            eyebrow="财务报表"
            title="报表交付中心"
            description="围绕报表口径、映射规则、合并抵销、归档锁定和经营分析报告组织交付流程，适合月结和管理层汇报。"
            summaryItems={[
              { label: "报表口径", value: "4 套", helper: "资产负债表、利润表、现金流等" },
              { label: "映射规则", value: "已追溯", helper: "科目到报表项目可校验" },
              { label: "归档快照", value: "待锁定", helper: "月结后生成不可改快照", status: "warning" },
              { label: "报告章节", value: `${report.sections.length}`, helper: "经营分析报告已生成" }
            ]}
            statusItems={[
              { label: "报表生成", value: "可刷新", tone: "normal" },
              { label: "合并抵销", value: "待重建", tone: "warning" },
              { label: "归档锁定", value: "月结后执行", tone: "processing" }
            ]}
            primaryActions={[
              { label: "生成报表", type: "primary", href: "#statement-center" },
              { label: "导出报告", href: "#statement-center" },
              { label: "AI 审阅", onClick: () => setIsAiDrawerOpen(true) }
            ]}
          >
            <StatementMappingPanel />
            <FinancialStatementPanel period={overview.period} />
            <ConsolidationPanel period={overview.period} />
            <StatementArchivePanel period={overview.period} />
            <ReportPanel report={report} />
          </SaasModuleWorkspace>

          <SaasModuleWorkspace
            id="data-center"
            eyebrow="数据分析"
            title="数据运营中心"
            description="把凭证、账簿、往来、银行、存货、资产、薪酬、月结和会计档案集中到一个运营视图，方便长期高频使用。"
            summaryItems={[
              { label: "数据质量", value: "92%", helper: "凭证、账簿、银行流水综合评分" },
              { label: "待处理任务", value: "11", helper: "对账、月结、归档事项", status: "warning" },
              { label: "自动化覆盖", value: "8 类", helper: "存货、资产、薪酬、税务等" },
              { label: "审计追踪", value: "开启", helper: "关键动作保留留痕" }
            ]}
            statusItems={[
              { label: "凭证中心", value: "可过账", tone: "processing" },
              { label: "银行对账", value: "待匹配", tone: "warning" },
              { label: "会计档案", value: "可归档", tone: "normal" }
            ]}
            primaryActions={[
              { label: "导入数据", type: "primary", onClick: onOpenDataEntry },
              { label: "执行月结", href: "#data-center" },
              { label: "AI 生成清单", onClick: () => setIsAiDrawerOpen(true) }
            ]}
          >
            <VoucherCenterPanel />
            <LedgerPanel period={overview.period} />
            <ReceivablePayablePanel period={overview.period} />
            <BankReconciliationPanel period={overview.period} />
            <InventoryAccountingPanel period={overview.period} />
            <AccrualAmortizationPanel period={overview.period} />
            <FixedAssetPanel period={overview.period} />
            <PayrollPanel period={overview.period} />
            <PeriodClosePanel period={overview.period} />
            <AccountingArchivePanel period={overview.period} />
            <AccountingGovernancePanel period={overview.period} />
          </SaasModuleWorkspace>

          <section id="ai-advisor" className="saas-section">
            <SectionHeading eyebrow="AI 财务顾问" title="带政策依据和执行方案的财务问答" />
            <AIFinanceAdvisor />
          </section>

          <section id="company-settings" className="saas-section">
            <SectionHeading eyebrow="企业设置" title="权限、角色、审计与系统治理" />
            <UpdateCenterPanel />
            <SystemAdminPanel />
          </section>
        </Content>
      </Layout>

      <Drawer
        title="AI 财务助手"
        size={520}
        open={isAiDrawerOpen}
        onClose={() => setIsAiDrawerOpen(false)}
        destroyOnClose
      >
        <AIFinanceAdvisor compact />
      </Drawer>
    </Layout>
  );
}

function SectionHeading({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div className="saas-section-heading">
      <div>
        <Text className="eyebrow">{eyebrow}</Text>
        <Title level={3}>{title}</Title>
      </div>
    </div>
  );
}
