import logging
from core import ollama_client, rag_service
from chat.context import chat_context_service
from chat.history import chat_history
from chat.actions import action_service
from chat.prompts import CHAT_SYSTEM_PROMPT, TITLE_GENERATION_PROMPT

logger = logging.getLogger(__name__)


class LLMService:
    """Main orchestration: context + RAG + history -> Ollama -> response."""

    async def chat(
        self,
        message: str,
        user_id: int,
        conversation_id: str | None = None,
        context_type: str = "general",
    ) -> dict:
        """Process a chat message and return AI response."""
        # Create or retrieve conversation
        is_new = conversation_id is None
        if is_new:
            conversation_id = chat_history.create_conversation(user_id)

        # Save user message
        chat_history.add_message(conversation_id, "user", message)

        # Build context
        business_context = chat_context_service.get_context_for_type(context_type)

        # Search RAG for relevant documents
        rag_context = ""
        try:
            if rag_service.get_document_count() > 0:
                rag_results = rag_service.search(message, n_results=3)
                if rag_results:
                    rag_pieces = []
                    for doc in rag_results:
                        if doc["relevance"] > 0.3:
                            rag_pieces.append(doc["content"])
                    if rag_pieces:
                        rag_context = "Relevant documents:\n" + "\n---\n".join(rag_pieces)
        except Exception as e:
            logger.warning(f"RAG search failed: {e}")

        # Build system prompt
        system_prompt = CHAT_SYSTEM_PROMPT.format(
            business_context=business_context,
            rag_context=rag_context,
        )

        # Get chat history for context
        history = chat_history.get_messages(conversation_id, limit=20)

        # Build messages for Ollama
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Call Ollama
        try:
            response = await ollama_client.chat(messages)
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            response = "I'm sorry, I'm having trouble connecting to the AI model right now. Please try again in a moment."

        # Parse action from response (if any)
        clean_response, action_data = action_service.parse_action_from_response(response)

        # Resolve action (look up IDs for customer/chemical names)
        resolved_action = None
        if action_data:
            try:
                resolved_action = action_service.resolve_action(action_data)
                if resolved_action.get("errors"):
                    # Add error info to the response text
                    error_text = "\n\nNote: " + " ".join(resolved_action["errors"])
                    clean_response += error_text
            except Exception as e:
                logger.error(f"Action resolution failed: {e}")

        # Save the clean response (without action markers)
        chat_history.add_message(conversation_id, "assistant", clean_response)

        # Generate title for new conversations
        title = None
        if is_new:
            try:
                title = await self._generate_title(message)
                chat_history.update_title(conversation_id, title)
            except Exception as e:
                logger.warning(f"Title generation failed: {e}")
                title = "New Conversation"

        # Gather sources
        sources = []
        if rag_context:
            sources.append("Indexed documents")
        if business_context and "unavailable" not in business_context.lower():
            sources.append("ERP database")

        result = {
            "response": clean_response,
            "conversation_id": conversation_id,
            "title": title,
            "sources": sources,
            "action": resolved_action,
        }

        return result

    async def _generate_title(self, message: str) -> str:
        """Generate a short title for a conversation."""
        prompt = TITLE_GENERATION_PROMPT.format(message=message[:200])
        try:
            title = await ollama_client.generate(prompt, temperature=0.3)
            # Clean up - take first line, strip quotes
            title = title.strip().split("\n")[0].strip('"\'')
            if len(title) > 50:
                title = title[:47] + "..."
            return title or "New Conversation"
        except Exception:
            return "New Conversation"


llm_service = LLMService()
