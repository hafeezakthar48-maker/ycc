import type { HomeDashboard, HomeMetric } from "../types/homeDashboard";

interface HomeDashboardPanelProps {
  dashboard: HomeDashboard;
}

function metricClass(metric: HomeMetric) {
  return `home-metric home-metric--${metric.status}`;
}

function tipClass(level: string) {
  if (level === "high") {
    return "home-tip home-tip--high";
  }
  if (level === "medium") {
    return "home-tip home-tip--medium";
  }
  return "home-tip";
}

export default function HomeDashboardPanel({ dashboard }: HomeDashboardPanelProps) {
  return (
    <section id="ai-home" className="home-dashboard">
      <div className="section-heading">
        <div>
          <span className="eyebrow">AI 首页</span>
          <h2>企业经营一屏总览</h2>
        </div>
        <div className="qa-status-strip">
          <span>{dashboard.period}</span>
          <span>经营概况</span>
          <span>AI 今日提示</span>
        </div>
      </div>

      <div className="home-section-grid">
        {dashboard.sections.map((section) => (
          <article className="home-section-card" key={section.key}>
            <div className="home-section-title">
              <span className="eyebrow">{section.title}</span>
            </div>
            <div className="home-metric-grid">
              {section.metrics.map((metric) => (
                <div className={metricClass(metric)} key={metric.key}>
                  <span>{metric.title}</span>
                  <strong>{metric.value}</strong>
                  <small>{metric.note}</small>
                </div>
              ))}
            </div>
          </article>
        ))}
      </div>

      <section className="panel home-ai-tips">
        <div className="panel-header">
          <div>
            <span className="eyebrow">AI 提示</span>
            <h3>今日自动生成</h3>
          </div>
        </div>
        <div className="home-tip-grid">
          {dashboard.ai_tips.map((tip) => (
            <article className={tipClass(tip.level)} key={tip.category}>
              <span>{tip.category}</span>
              <strong>{tip.title}</strong>
              <p>{tip.content}</p>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}
