from fastapi import APIRouter, Depends, HTTPException, Query
from dependencies import verify_api_key
from models.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationListResponse,
    ConversationMessagesResponse,
)
from services.llm_service import llm_service
from services.chat_history import chat_history

router = APIRouter(prefix="/chat", tags=["Chat"], dependencies=[Depends(verify_api_key)])


@router.post("/", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """Send a message to the AI assistant and get a response."""
    result = await llm_service.chat(
        message=request.message,
        user_id=request.user_id,
        conversation_id=request.conversation_id,
        context_type=request.context_type,
    )
    return ChatResponse(**result)


@router.get("/conversations/", response_model=ConversationListResponse)
async def list_conversations(user_id: int = Query(..., gt=0)):
    """List all conversations for a user."""
    conversations = chat_history.get_conversations(user_id)
    return ConversationListResponse(conversations=conversations)


@router.get("/conversations/{conversation_id}/messages/", response_model=ConversationMessagesResponse)
async def get_conversation_messages(conversation_id: str):
    """Get all messages in a conversation."""
    conversation = chat_history.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = chat_history.get_messages(conversation_id)
    return ConversationMessagesResponse(
        conversation_id=conversation_id,
        title=conversation["title"],
        messages=messages,
    )


@router.delete("/conversations/{conversation_id}/")
async def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages."""
    deleted = chat_history.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"detail": "Conversation deleted"}
