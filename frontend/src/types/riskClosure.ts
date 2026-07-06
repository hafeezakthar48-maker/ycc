import type { RiskItem } from "./dashboard";

export type RiskClosureStatus = "open" | "assigned" | "processing" | "resolved" | "closed";

export interface RiskProcessRecord {
  id: string;
  handler: string;
  action: string;
  note: string;
  created_at: string;
}

export interface RiskReviewRecord {
  id: string;
  reviewer: string;
  conclusion: string;
  created_at: string;
}

export interface RiskClosureItem {
  period: string;
  risk: RiskItem;
  status: RiskClosureStatus;
  owner: string | null;
  due_date: string | null;
  process_records: RiskProcessRecord[];
  review_records: RiskReviewRecord[];
}

export interface RiskClosureListResponse {
  period: string;
  total: number;
  open_count: number;
  closed_count: number;
  items: RiskClosureItem[];
}

export interface RiskAssignRequest {
  period: string;
  owner: string;
  due_date: string;
  note?: string;
}

export interface RiskProcessRecordRequest {
  period: string;
  handler: string;
  action: string;
  note: string;
  next_status: "assigned" | "processing" | "resolved";
}

export interface RiskReviewRecordRequest {
  period: string;
  reviewer: string;
  conclusion: string;
  next_status: "processing" | "resolved" | "closed";
}
