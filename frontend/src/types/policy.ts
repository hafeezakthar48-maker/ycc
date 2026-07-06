export interface PolicyDocument {
  id: string;
  title: string;
  authority: string;
  document_number: string | null;
  category: string;
  published_date: string;
  effective_date: string | null;
  status: string;
  source_url: string;
  updated_at: string;
  keywords: string[];
  summary: string;
  content: string;
}

export interface PolicySearchResult {
  document: PolicyDocument;
  relevance_score: number;
  snippets: string[];
}

export interface PolicySearchResponse {
  query: string;
  total: number;
  results: PolicySearchResult[];
  latest_policy_check_required: boolean;
}
