export interface FinanceQuestionRequest {
  question: string;
}

export interface FinanceCitation {
  title: string;
  authority: string;
  document_number: string | null;
  published_date: string;
  status: string;
  source_url: string;
  updated_at: string;
}

export interface FinanceQuestionResponse {
  question: string;
  intent: string;
  answer: string;
  confidence: number;
  action_items: string[];
  citations: FinanceCitation[];
  risk_level: "low" | "medium" | "high" | string;
  requires_human_review: boolean;
  latest_policy_check_required: boolean;
}
