export interface HomeMetric {
  key: string;
  title: string;
  value: string;
  note: string;
  status: "normal" | "warning" | "danger" | string;
}

export interface HomeMetricSection {
  key: string;
  title: string;
  metrics: HomeMetric[];
}

export interface HomeAiTip {
  category: string;
  title: string;
  content: string;
  level: "normal" | "medium" | "high" | string;
}

export interface HomeDashboard {
  period: string;
  company_name: string;
  sections: HomeMetricSection[];
  ai_tips: HomeAiTip[];
}
