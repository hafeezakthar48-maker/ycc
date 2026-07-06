import { FormEvent, useEffect, useState } from "react";
import ECommerceCostChart from "../charts/ECommerceCostChart";
import ECommerceProfitBridgeChart from "../charts/ECommerceProfitBridgeChart";
import { analyzeECommerceProfit } from "../services/dashboardApi";
import type { ECommerceProfitRequest, ECommerceProfitResult } from "../types/ecommerce";

const defaultRequest: ECommerceProfitRequest = {
  period: "2026-06",
  platform: "抖音小店",
  gmv: 100000,
  refund_amount: 8000,
  product_cost: 48000,
  platform_commission: 5500,
  payment_fee: 600,
  advertising_spend: 18000,
  logistics_cost: 5200,
  packaging_cost: 1200,
  labor_cost: 4000,
  other_cost: 1800,
  order_count: 2000,
  visitor_count: 50000
};

const fields: Array<{ key: keyof ECommerceProfitRequest; label: string; type: "text" | "number" }> = [
  { key: "period", label: "期间", type: "text" },
  { key: "platform", label: "平台/店铺", type: "text" },
  { key: "gmv", label: "GMV", type: "number" },
  { key: "refund_amount", label: "退款金额", type: "number" },
  { key: "product_cost", label: "商品成本", type: "number" },
  { key: "platform_commission", label: "平台佣金", type: "number" },
  { key: "payment_fee", label: "支付手续费", type: "number" },
  { key: "advertising_spend", label: "广告投放", type: "number" },
  { key: "logistics_cost", label: "物流成本", type: "number" },
  { key: "packaging_cost", label: "包装成本", type: "number" },
  { key: "labor_cost", label: "人工成本", type: "number" },
  { key: "other_cost", label: "其他成本", type: "number" },
  { key: "order_count", label: "订单数", type: "number" },
  { key: "visitor_count", label: "访客数", type: "number" }
];

function percent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export default function ECommerceProfitPanel() {
  const [form, setForm] = useState<ECommerceProfitRequest>(defaultRequest);
  const [result, setResult] = useState<ECommerceProfitResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  async function runAnalysis(nextForm = form) {
    setIsBusy(true);
    setError(null);
    try {
      setResult(await analyzeECommerceProfit(nextForm));
    } catch (analysisError) {
      setError(analysisError instanceof Error ? analysisError.message : "电商利润分析失败");
    } finally {
      setIsBusy(false);
    }
  }

  useEffect(() => {
    runAnalysis(defaultRequest);
  }, []);

  function updateField(key: keyof ECommerceProfitRequest, value: string) {
    setForm((current) => {
      if (key === "period" || key === "platform") {
        return { ...current, [key]: value };
      }
      const numericValue = Number(value);
      return { ...current, [key]: Number.isFinite(numericValue) ? numericValue : 0 };
    });
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    runAnalysis();
  }

  return (
    <section id="ecommerce" className="ecommerce-section">
      <div className="section-heading">
        <div>
          <span className="eyebrow">电商利润分析</span>
          <h2>从 GMV 到净利润的单店测算</h2>
        </div>
        {result ? (
          <div className="ecommerce-ratio-strip">
            <span>毛利率 {percent(result.gross_margin)}</span>
            <span>净利率 {percent(result.net_margin)}</span>
            <span>退款率 {percent(result.refund_rate)}</span>
          </div>
        ) : null}
      </div>

      <form className="ecommerce-form" onSubmit={handleSubmit}>
        {fields.map((field) => (
          <label key={field.key}>
            {field.label}
            <input
              type={field.type}
              min={field.type === "number" ? 0 : undefined}
              step={field.key === "order_count" || field.key === "visitor_count" ? 1 : 100}
              value={String(form[field.key])}
              onChange={(event) => updateField(field.key, event.target.value)}
            />
          </label>
        ))}
        <button type="submit" disabled={isBusy}>{isBusy ? "分析中..." : "重新分析"}</button>
      </form>

      {error ? <p className="inline-error">{error}</p> : null}

      {result ? (
        <>
          <div className="ecommerce-metrics">
            {result.metrics.map((metric) => (
              <article className={`metric-card metric-card--${metric.status}`} key={metric.key}>
                <span>{metric.title}</span>
                <strong>{metric.value}</strong>
                <small>{metric.key === "roi" ? "净销售额 / 广告投放" : result.platform}</small>
              </article>
            ))}
          </div>

          <div className="ecommerce-grid">
            <section className="panel">
              <div className="panel-header">
                <div>
                  <span className="eyebrow">成本结构</span>
                  <h3>费用与成本占比</h3>
                </div>
              </div>
              <ECommerceCostChart data={result.cost_breakdown} />
            </section>

            <section className="panel panel--wide">
              <div className="panel-header">
                <div>
                  <span className="eyebrow">利润桥</span>
                  <h3>净销售额到净利润</h3>
                </div>
              </div>
              <ECommerceProfitBridgeChart data={result.profit_bridge} />
            </section>
          </div>

          <div className="ecommerce-insights">
            <section className="panel">
              <div className="panel-header">
                <div>
                  <span className="eyebrow">风险提示</span>
                  <h3>利润质量复核点</h3>
                </div>
              </div>
              {result.risks.length > 0 ? (
                result.risks.map((risk) => (
                  <article className="ecommerce-risk" key={risk.id}>
                    <strong>{risk.title}</strong>
                    <span>{"★".repeat(risk.level)}{"☆".repeat(5 - risk.level)}</span>
                    <p>{risk.description}</p>
                    <small>{risk.suggestion}</small>
                  </article>
                ))
              ) : (
                <p className="muted">未发现明显利润异常，仍建议按 SKU 和渠道继续拆分复核。</p>
              )}
            </section>

            <section className="panel">
              <div className="panel-header">
                <div>
                  <span className="eyebrow">经营建议</span>
                  <h3>下一步动作</h3>
                </div>
              </div>
              <ul className="suggestion-list">
                {result.suggestions.map((suggestion) => (
                  <li key={suggestion}>{suggestion}</li>
                ))}
              </ul>
            </section>
          </div>
        </>
      ) : null}
    </section>
  );
}
