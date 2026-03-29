"""
AI Assistant API Endpoints

FastAPI router for AI Assistant chat and conversation management.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from uuid import UUID
import logging

from src.schemas.ai_assistant import (
    ChatRequest,
    ChatResponse,
    ConversationSummary,
    ConversationDetail,
    ConversationsListResponse,
    MRLCheckRequest,
    MRLCheckResponse,
    ExportRequirementsRequest,
    ExportRequirementsResponse,
    WebSearchRequest,
    WebSearchResponse,
    WebSearchResult,
    UpdateConversationTitleRequest,
    DeleteConversationResponse
)
from src.services.ai_agent import AIAgentService
from src.api.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["AI Assistant"])


@router.post("/chat", response_model=ChatResponse, summary="Chat with AI Assistant")
async def chat_with_assistant(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Send a message to the AI Assistant and receive a response.
    
    The assistant can:
    - Answer questions about fruit diseases and their prevention
    - Provide treatment recommendations
    - Check MRL (Maximum Residue Limit) compliance for pesticides
    - Explain export requirements for different countries
    - Search the web for current agricultural news and regulations
    
    **Example queries:**
    - "What is anthracnose and how do I treat it?"
    - "Is Mancozeb safe for exporting mangoes to EU?"
    - "What are the export requirements for citrus to USA?"
    - "What diseases commonly affect apples in Pakistan?"
    """
    try:
        service = AIAgentService(user_id=current_user["user_id"])
        
        result = await service.process_message(
            user_id=current_user["user_id"],
            message=request.message,
            conversation_id=str(request.conversation_id) if request.conversation_id else None
        )
        
        return ChatResponse(
            response=result.get("response", ""),
            conversation_id=result.get("conversation_id"),
            rich_content=result.get("rich_content"),
            actions=result.get("actions"),
            tools_used=result.get("tools_used")
        )
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.get(
    "/conversations", 
    response_model=ConversationsListResponse,
    summary="Get conversation history"
)
async def get_conversations(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of user's conversation history.
    
    Returns recent conversations sorted by last activity.
    """
    try:
        service = AIAgentService(user_id=current_user["user_id"])
        conversations = await service.get_conversations(
            user_id=current_user["user_id"],
            limit=limit
        )
        
        return ConversationsListResponse(
            conversations=[
                ConversationSummary(
                    id=UUID(c["id"]),
                    title=c.get("title", "Untitled"),
                    created_at=c["created_at"],
                    updated_at=c["updated_at"]
                )
                for c in conversations
            ],
            count=len(conversations)
        )
        
    except Exception as e:
        logger.error(f"Get conversations error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversations"
        )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
    summary="Get specific conversation"
)
async def get_conversation(
    conversation_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific conversation with all its messages.
    """
    try:
        service = AIAgentService(user_id=current_user["user_id"])
        result = await service.get_conversation_messages(
            user_id=current_user["user_id"],
            conversation_id=str(conversation_id)
        )
        
        if "error" in result and result["error"] == "Conversation not found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        conv = result["conversation"]
        messages = result["messages"]
        
        return ConversationDetail(
            conversation=ConversationSummary(
                id=UUID(conv["id"]),
                title=conv.get("title", "Untitled"),
                created_at=conv["created_at"],
                updated_at=conv["updated_at"]
            ),
            messages=[
                {
                    "role": m["role"],
                    "content": m["content"],
                    "tool_calls": m.get("tool_calls"),
                    "timestamp": m.get("created_at")
                }
                for m in messages
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get conversation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation"
        )


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationSummary,
    summary="Update conversation title"
)
async def update_conversation(
    conversation_id: UUID,
    request: UpdateConversationTitleRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a conversation's title.
    """
    try:
        service = AIAgentService(user_id=current_user["user_id"])
        success = await service.update_conversation_title(
            user_id=current_user["user_id"],
            conversation_id=str(conversation_id),
            title=request.title
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or update failed"
            )
        
        # Return updated conversation
        result = await service.get_conversation_messages(
            user_id=current_user["user_id"],
            conversation_id=str(conversation_id)
        )
        
        conv = result["conversation"]
        return ConversationSummary(
            id=UUID(conv["id"]),
            title=conv.get("title", request.title),
            created_at=conv["created_at"],
            updated_at=conv["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update conversation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update conversation"
        )


@router.delete(
    "/conversations/{conversation_id}",
    response_model=DeleteConversationResponse,
    summary="Delete conversation"
)
async def delete_conversation(
    conversation_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a conversation and all its messages.
    """
    try:
        service = AIAgentService(user_id=current_user["user_id"])
        success = await service.delete_conversation(
            user_id=current_user["user_id"],
            conversation_id=str(conversation_id)
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        return DeleteConversationResponse(
            success=True,
            message="Conversation deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete conversation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation"
        )


# Direct tool endpoints for specific queries without chat context

@router.get(
    "/detection-summary",
    summary="Get Supabase-backed detection summary"
)
async def get_detection_summary(
    period: str = "this_month",
    orchard_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detection totals and trends for this month or up to last 6 months.
    """
    try:
        service = AIAgentService(user_id=current_user["user_id"])
        return await service.tools.get_detection_summary(
            period=period,
            orchard_id=orchard_id
        )
    except Exception as e:
        logger.error(f"Detection summary error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get detection summary"
        )


@router.get(
    "/orchard-weather/{orchard_id}",
    summary="Get orchard weather and detection signals"
)
async def get_orchard_weather_summary(
    orchard_id: str,
    days: int = 3,
    current_user: dict = Depends(get_current_user)
):
    """
    Get orchard profile, current weather, short forecast, and this-month detection signals.
    """
    try:
        service = AIAgentService(user_id=current_user["user_id"])
        return await service.tools.get_orchard_weather(
            orchard_id=orchard_id,
            days=days
        )
    except Exception as e:
        logger.error(f"Orchard weather summary error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get orchard weather summary"
        )

@router.post(
    "/mrl-check",
    response_model=MRLCheckResponse,
    summary="Check MRL compliance"
)
async def check_mrl_compliance(
    request: MRLCheckRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Directly check MRL (Maximum Residue Limit) compliance for a pesticide.
    
    This is useful for quick compliance checks without going through chat.
    """
    try:
        service = AIAgentService(user_id=current_user["user_id"])
        result = await service.tools.check_mrl_compliance(
            pesticide=request.pesticide,
            fruit=request.fruit,
            country=request.country
        )
        
        return MRLCheckResponse(
            pesticide=request.pesticide,
            fruit=request.fruit,
            country=request.country,
            mrl_limit=result.get("mrl_limit"),
            unit=result.get("unit", "mg/kg"),
            is_compliant=None,  # Would need actual residue value to determine
            recommendation=result.get("recommendation"),
            found=result.get("found", False)
        )
        
    except Exception as e:
        logger.error(f"MRL check error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check MRL compliance"
        )


@router.post(
    "/export-requirements",
    response_model=ExportRequirementsResponse,
    summary="Get export requirements"
)
async def get_export_requirements(
    request: ExportRequirementsRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Get export requirements for a fruit to a specific country.
    
    Returns certifications, phytosanitary requirements, and standards.
    """
    try:
        service = AIAgentService(user_id=current_user["user_id"])
        result = await service.tools.get_export_requirements(
            country=request.country,
            fruit=request.fruit
        )
        
        requirements = result.get("requirements", {})
        
        return ExportRequirementsResponse(
            country=request.country,
            fruit=request.fruit,
            certifications=requirements.get("certifications", []),
            mrl_standard=requirements.get("mrl_standard"),
            phytosanitary=requirements.get("phytosanitary"),
            packaging=requirements.get("packaging"),
            additional_requirements={
                k: v for k, v in requirements.items() 
                if k not in ["certifications", "mrl_standard", "phytosanitary", "packaging"]
            } if requirements else None,
            found=result.get("found", False)
        )
        
    except Exception as e:
        logger.error(f"Export requirements error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get export requirements"
        )


@router.post(
    "/search",
    response_model=WebSearchResponse,
    summary="Search web for agricultural info"
)
async def web_search(
    request: WebSearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Search the web for current agricultural information.
    
    Useful for finding:
    - Current regulations and policies
    - Market prices
    - Latest research on diseases
    - News and updates
    """
    try:
        service = AIAgentService(user_id=current_user["user_id"])
        result = await service.tools.web_search(query=request.query)
        
        return WebSearchResponse(
            query=request.query,
            results=[
                WebSearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    content=r.get("content", ""),
                    score=r.get("score")
                )
                for r in result.get("results", [])[:request.max_results]
            ],
            count=result.get("count", 0)
        )
        
    except Exception as e:
        logger.error(f"Web search error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform web search"
        )
