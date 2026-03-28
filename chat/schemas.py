from pydantic import BaseModel, Field


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
