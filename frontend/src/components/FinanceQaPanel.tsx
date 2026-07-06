import { FormEvent, useEffect, useState } from "react";
import { askFinanceQuestion } from "../services/dashboardApi";
import type { FinanceQuestionResponse } from "../types/financeQa";

const sampleQuestions = [
  "电商平台订单已经发货，收入应该什么时候确认？",
  "固定资产折旧需要注意哪些会计处理？",
  "收到电子发票时要怎么检查发票风险？",
  "我们公司这个月能不能享受最新地方税收优惠？"
];

function confidenceText(confidence: number) {
  return `${Math.round(confidence * 100)}%`;
}

export default function FinanceQaPanel() {
  const [question, setQuestion] = useState(sampleQuestions[0]);
  const [answer, setAnswer] = useState<FinanceQuestionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  async function runQuestion(nextQuestion = question) {
    const trimmed = nextQuestion.trim();
    if (!trimmed) {
      setError("请输入财务或税务问题。");
      return;
    }

    setIsBusy(true);
    setError(null);
    try {
      setAnswer(await askFinanceQuestion(trimmed));
      setQuestion(trimmed);
    } catch (qaError) {
      setError(qaError instanceof Error ? qaError.message : "AI 财务问答失败");
    } finally {
      setIsBusy(false);
    }
  }

  useEffect(() => {
    runQuestion(sampleQuestions[0]);
  }, []);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    runQuestion();
  }

  return (
    <section id="finance-qa" className="finance-qa-section">
      <div className="section-heading">
        <div>
          <span className="eyebrow">AI 财务问答</span>
          <h2>带法规依据的审计式回答</h2>
        </div>
        <div className="qa-status-strip">
          <span>不编造法规</span>
          <span>输出引用依据</span>
          <span>默认人工复核</span>
        </div>
      </div>

      <form className="qa-form" onSubmit={handleSubmit}>
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          rows={3}
          placeholder="请输入财务、会计、发票或税务风险问题"
        />
        <button type="submit" disabled={isBusy}>{isBusy ? "分析中..." : "提交问题"}</button>
      </form>

      <div className="qa-samples" aria-label="示例问题">
        {sampleQuestions.map((item) => (
          <button
            type="button"
            className="button-secondary"
            key={item}
            onClick={() => runQuestion(item)}
            disabled={isBusy}
          >
            {item}
          </button>
        ))}
      </div>

      {error ? <p className="inline-error">{error}</p> : null}

      {answer ? (
        <div className="qa-result">
          <section className="panel qa-answer-card">
            <div className="panel-header">
              <div>
                <span className="eyebrow">回答</span>
                <h3>{answer.intent === "unknown" ? "需要实时政策核验" : "AI 初步判断"}</h3>
              </div>
              <div className={`qa-risk qa-risk--${answer.risk_level}`}>
                置信度 {confidenceText(answer.confidence)}
              </div>
            </div>
            <p>{answer.answer}</p>
            <div className="qa-flags">
              <span>{answer.requires_human_review ? "需要人工复核" : "可直接采用"}</span>
              <span>{answer.latest_policy_check_required ? "需要实时政策核验" : "本地法规卡已匹配"}</span>
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">检查清单</span>
                <h3>财务人员下一步动作</h3>
              </div>
            </div>
            <ul className="suggestion-list">
              {answer.action_items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>

          <section className="panel qa-citation-panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">引用依据</span>
                <h3>法规与准则来源</h3>
              </div>
            </div>
            {answer.citations.length > 0 ? (
              <div className="qa-citations">
                {answer.citations.map((citation) => (
                  <article key={`${citation.title}-${citation.published_date}`}>
                    <strong>{citation.title}</strong>
                    <p>
                      {citation.authority}
                      {citation.document_number ? ` · ${citation.document_number}` : ""}
                    </p>
                    <small>
                      发布/成文：{citation.published_date} · 状态：{citation.status} · 更新：{citation.updated_at}
                    </small>
                    <a href={citation.source_url} target="_blank" rel="noreferrer">查看来源</a>
                  </article>
                ))}
              </div>
            ) : (
              <p className="muted">未匹配到可引用的本地法规卡片，请接入实时法规库后复核。</p>
            )}
          </section>
        </div>
      ) : null}
    </section>
  );
}
