from pydantic import BaseModel


class HomeMetric(BaseModel):
    key: str
    title: str
    value: str
    note: str
    status: str = "normal"


class HomeMetricSection(BaseModel):
    key: str
    title: str
    metrics: list[HomeMetric]


class HomeAiTip(BaseModel):
    category: str
    title: str
    content: str
    level: str


class HomeDashboardResponse(BaseModel):
    period: str
    company_name: str
    sections: list[HomeMetricSection]
    ai_tips: list[HomeAiTip]
