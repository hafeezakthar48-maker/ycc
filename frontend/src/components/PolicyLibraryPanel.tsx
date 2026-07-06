import { FormEvent, useEffect, useState } from "react";
import { searchPolicies } from "../services/dashboardApi";
import type { PolicySearchResponse } from "../types/policy";

const categoryOptions = ["全部", "会计准则", "税收法规"];
const sampleQueries = ["收入确认 控制权", "固定资产 折旧", "电子发票 虚开 抵扣", "企业所得税 税前扣除", "增值税 进项税额"];

export default function PolicyLibraryPanel() {
  const [query, setQuery] = useState(sampleQueries[0]);
  const [category, setCategory] = useState("全部");
  const [result, setResult] = useState<PolicySearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  async function runSearch(nextQuery = query, nextCategory = category) {
    const trimmed = nextQuery.trim();
    if (!trimmed) {
      setError("请输入法规、准则或税务关键词。");
      return;
    }

    setIsBusy(true);
    setError(null);
    try {
      setResult(await searchPolicies(trimmed, nextCategory === "全部" ? null : nextCategory, 8));
      setQuery(trimmed);
      setCategory(nextCategory);
    } catch (searchError) {
      setError(searchError instanceof Error ? searchError.message : "法规库检索失败");
    } finally {
      setIsBusy(false);
    }
  }

  useEffect(() => {
    runSearch(sampleQueries[0], "全部");
  }, []);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    runSearch();
  }

  return (
    <section id="policy-library" className="policy-section">
      <div className="section-heading">
        <div>
          <span className="eyebrow">财税法规库</span>
          <h2>可引用、可复核的本地 RAG 底座</h2>
        </div>
        <div className="qa-status-strip">
          <span>结构化来源</span>
          <span>状态标记</span>
          <span>等待实时同步</span>
        </div>
      </div>

      <form className="policy-search-form" onSubmit={handleSubmit}>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="输入法规、准则、税种或风险关键词"
        />
        <select value={category} onChange={(event) => setCategory(event.target.value)}>
          {categoryOptions.map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>
        <button type="submit" disabled={isBusy}>{isBusy ? "检索中..." : "检索"}</button>
      </form>

      <div className="qa-samples" aria-label="法规库示例检索">
        {sampleQueries.map((item) => (
          <button
            type="button"
            className="button-secondary"
            key={item}
            onClick={() => runSearch(item, category)}
            disabled={isBusy}
          >
            {item}
          </button>
        ))}
      </div>

      {error ? <p className="inline-error">{error}</p> : null}

      {result ? (
        <div className="policy-results">
          <div className="policy-result-summary">
            <strong>命中 {result.total} 条</strong>
            <span>{result.latest_policy_check_required ? "正式使用前仍需核验最新政策状态" : "已完成最新政策核验"}</span>
          </div>
          {result.results.map((item) => (
            <article className="policy-card" key={item.document.id}>
              <div className="policy-card-header">
                <div>
                  <strong>{item.document.title}</strong>
                  <p>
                    {item.document.authority}
                    {item.document.document_number ? ` · ${item.document.document_number}` : ""}
                  </p>
                </div>
                <span>{item.document.status}</span>
              </div>
              <p>{item.document.summary}</p>
              <div className="policy-snippets">
                {item.snippets.map((snippet) => (
                  <small key={snippet}>{snippet}</small>
                ))}
              </div>
              <div className="policy-meta">
                <span>发布/成文：{item.document.published_date}</span>
                <span>更新：{item.document.updated_at}</span>
                <span>相关度：{item.relevance_score.toFixed(1)}</span>
              </div>
              <a href={item.document.source_url} target="_blank" rel="noreferrer">查看官方来源</a>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
