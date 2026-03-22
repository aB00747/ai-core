from pydantic import BaseModel, Field
from datetime import datetime


# --- Chat ---

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: str | None = None
    user_id: int = Field(..., gt=0)
    context_type: str = Field(default="general", pattern="^(general|sales|inventory|customers|orders)$")


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: str


class ActionData(BaseModel):
    type: str
    resolved: bool = False
    dashboard_link: str = ""
    params: dict = {}
    display: dict = {}
    errors: list[str] = []


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    title: str | None = None
    sources: list[str] = []
    action: ActionData | None = None


class ConversationSummary(BaseModel):
    conversation_id: str
    title: str
    last_message: str
    updated_at: str
    message_count: int


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]


class ConversationMessagesResponse(BaseModel):
    conversation_id: str
    title: str
    messages: list[ChatMessage]


# --- Insights ---

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


# --- Documents ---

class DocumentProcessRequest(BaseModel):
    file_path: str
    file_name: str
    file_type: str = Field(..., pattern="^(pdf|docx|xlsx|csv|txt)$")
    user_id: int = Field(..., gt=0)


class DocumentProcessResponse(BaseModel):
    document_id: str
    file_name: str
    summary: str
    entities: list[str]
    page_count: int
    indexed: bool


# --- Health ---

class HealthResponse(BaseModel):
    status: str
    ollama: bool
    chromadb: bool
    erp_database: bool
    model: str
    version: str = "1.0.0"
