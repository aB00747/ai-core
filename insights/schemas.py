from pydantic import BaseModel, Field


class InsightRequest(BaseModel):
    insight_type: str = Field(
        ...,
        pattern="^(sales_trend|inventory_health|customer_analysis|revenue_summary|anomaly_detection)$",
    )
    period_days: int = Field(default=30, ge=1, le=365)


class InsightResponse(BaseModel):
    insight_type: str
    title: str
    content: str
    data: dict | None = None
    generated_at: str


class QuickInsight(BaseModel):
    title: str
    summary: str
    category: str
    priority: str = "info"


class QuickInsightsResponse(BaseModel):
    insights: list[QuickInsight]
    generated_at: str
