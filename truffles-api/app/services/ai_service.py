from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, List

from app.models import Prompt, Client, Message, Conversation
from app.services.llm import OpenAIProvider, LLMResponse
from app.services.knowledge_service import search_knowledge, format_knowledge_context

OPENAI_API_KEY = "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"

# Global LLM provider instance
_llm_provider = None


def get_llm_provider() -> OpenAIProvider:
    """Get or create LLM provider instance."""
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = OpenAIProvider(api_key=OPENAI_API_KEY, default_model="gpt-5-mini")
    return _llm_provider


def get_system_prompt(db: Session, client_id: UUID) -> Optional[str]:
    """Get system prompt for client."""
    print(f"Looking for prompt with client_id={client_id}")
    prompt = db.query(Prompt).filter(
        Prompt.client_id == client_id,
        Prompt.name == "system",
        Prompt.is_active == True
    ).first()
    
    if prompt:
        print(f"Found prompt: {prompt.text[:100]}...")
    else:
        print(f"No prompt found for client_id={client_id}")
    
    return prompt.text if prompt else None


def get_conversation_history(db: Session, conversation_id: UUID, limit: int = 10) -> List[dict]:
    """Get recent conversation history."""
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.desc()).limit(limit).all()
    
    # Reverse to get chronological order
    messages = list(reversed(messages))
    
    history = []
    for msg in messages:
        role = "assistant" if msg.role == "assistant" else "user"
        if msg.role == "system":
            continue  # Skip system messages
        history.append({"role": role, "content": msg.content})
    
    return history


def generate_ai_response(
    db: Session,
    client_id: UUID,
    client_slug: str,
    conversation_id: UUID,
    user_message: str,
) -> str:
    """Generate AI response using LLM with knowledge base."""
    print(f"generate_ai_response: client_id={client_id}, client_slug={client_slug}")
    
    try:
        # 1. Get system prompt
        system_prompt = get_system_prompt(db, client_id)
        if not system_prompt:
            system_prompt = "Ты полезный ассистент. Отвечай кратко и по делу."
        
        # 2. Search knowledge base
        knowledge_results = []
        try:
            knowledge_results = search_knowledge(user_message, client_slug, limit=3)
        except Exception as e:
            print(f"Knowledge search error: {e}")
        
        knowledge_context = format_knowledge_context(knowledge_results)
        
        # 3. Build messages
        messages = []
        
        # System prompt with knowledge context
        full_system = system_prompt
        if knowledge_context:
            full_system += f"\n\n{knowledge_context}"
        
        messages.append({"role": "system", "content": full_system})
        
        # 4. Add conversation history (last 10 messages for context)
        history = get_conversation_history(db, conversation_id, limit=10)
        messages.extend(history)
        
        # 5. Add current user message (if not already in history)
        if not history or history[-1].get("content") != user_message:
            messages.append({"role": "user", "content": user_message})
        
        # 6. Generate response
        llm = get_llm_provider()
        print(f"Calling LLM with {len(messages)} messages")
        response = llm.generate(messages, temperature=1.0, max_tokens=2000)
        print(f"LLM response: {response.content[:100] if response.content else 'EMPTY'}...")
        
        return response.content
        
    except Exception as e:
        print(f"AI generation error: {e}")
        import traceback
        traceback.print_exc()
        return f"Извините, произошла ошибка. Попробуйте позже."
