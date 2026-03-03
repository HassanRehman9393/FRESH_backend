"""
AI Assistant Schemas

Pydantic models for AI Assistant API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from uuid import UUID
from datetime import datetime


class ChatMessage(BaseModel):
    """Schema for a single chat message."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    tool_calls: Optional[List[str]] = Field(None, description="Tools used for this message")
    timestamp: Optional[datetime] = Field(None, description="Message timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "What is anthracnose and how do I treat it?",
                "tool_calls": None,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class PageContext(BaseModel):
    """Schema for page context to make AI responses more relevant."""
    page: str = Field(..., description="Current page name (e.g., 'detection', 'orchard_detail')")
    orchard_id: Optional[str] = Field(None, description="Currently selected orchard ID")
    orchard_name: Optional[str] = Field(None, description="Currently selected orchard name")
    path: str = Field(..., description="Current page path")
    timestamp: str = Field(..., description="Context timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "page": "detection",
                "orchard_id": "123e4567-e89b-12d3-a456-426614174000",
                "orchard_name": "Mango Farm",
                "path": "/dashboard/detection",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class ChatRequest(BaseModel):
    """Schema for chat request from client."""
    message: str = Field(..., min_length=1, max_length=4000, description="User's message")
    conversation_id: Optional[UUID] = Field(None, description="Existing conversation ID to continue")
    page_context: Optional[PageContext] = Field(None, description="Current page context for better responses")
    conversation_history: Optional[List[ChatMessage]] = Field(
        None, 
        max_items=10,
        description="Recent conversation history (max 10 messages)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "What diseases affect mangoes and how can I prevent them?",
                "conversation_id": None,
                "page_context": {
                    "page": "detection",
                    "orchard_id": "123e4567-e89b-12d3-a456-426614174000",
                    "orchard_name": "Mango Farm",
                    "path": "/dashboard/detection",
                    "timestamp": "2024-01-15T10:30:00Z"
                },
                "conversation_history": []
            }
        }


class ChatResponse(BaseModel):
    """Schema for chat response to client."""
    response: str = Field(..., description="Assistant's response text")
    conversation_id: UUID = Field(..., description="Conversation ID for continuing the chat")
    rich_content: Optional[Dict[str, Any]] = Field(
        None, 
        description="Structured content for rich UI rendering (disease info, treatments, etc.)"
    )
    actions: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Suggested follow-up actions for the user"
    )
    tools_used: Optional[List[str]] = Field(
        None,
        description="List of tools used to generate this response"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "Mangoes are susceptible to several diseases...",
                "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
                "rich_content": {
                    "disease": {
                        "name": "Anthracnose",
                        "symptoms": ["Dark spots", "Fruit rot"]
                    }
                },
                "actions": [
                    {"type": "query", "label": "Get treatment options"}
                ],
                "tools_used": ["get_diseases_by_fruit", "get_disease_info"]
            }
        }


class ConversationSummary(BaseModel):
    """Schema for conversation list item."""
    id: UUID = Field(..., description="Conversation ID")
    title: str = Field(..., description="Conversation title")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last activity timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Mango disease discussion",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class ConversationDetail(BaseModel):
    """Schema for detailed conversation with messages."""
    conversation: ConversationSummary
    messages: List[ChatMessage] = Field(default=[], description="Conversation messages")


class ConversationsListResponse(BaseModel):
    """Schema for list of conversations response."""
    conversations: List[ConversationSummary] = Field(default=[], description="User's conversations")
    count: int = Field(..., description="Total number of conversations")


class DiseaseInfoResponse(BaseModel):
    """Schema for disease information response."""
    name: str = Field(..., description="Disease name in English")
    name_urdu: Optional[str] = Field(None, description="Disease name in Urdu")
    description: Optional[str] = Field(None, description="Disease description")
    symptoms: List[str] = Field(default=[], description="List of symptoms")
    causes: Optional[str] = Field(None, description="Disease causes")
    prevention: List[str] = Field(default=[], description="Prevention methods")
    affected_fruits: List[str] = Field(default=[], description="Fruits affected by this disease")
    treatments: Optional[List[Dict[str, Any]]] = Field(None, description="Treatment options")
    favorable_conditions: Optional[str] = Field(None, description="Conditions that favor disease")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Anthracnose",
                "name_urdu": "اینتھراکنوز",
                "description": "A fungal disease causing dark lesions on fruits",
                "symptoms": ["Dark sunken lesions", "Fruit rot", "Leaf spots"],
                "causes": "Caused by Colletotrichum fungi",
                "prevention": ["Use disease-free seedlings", "Apply fungicides"],
                "affected_fruits": ["mango", "papaya", "avocado"],
                "treatments": None,
                "favorable_conditions": "Warm, humid weather"
            }
        }


class MRLCheckRequest(BaseModel):
    """Schema for MRL compliance check request."""
    pesticide: str = Field(..., description="Pesticide name")
    fruit: str = Field(..., description="Fruit type")
    country: str = Field(..., description="Export target country")
    
    class Config:
        json_schema_extra = {
            "example": {
                "pesticide": "Mancozeb",
                "fruit": "mango",
                "country": "EU"
            }
        }


class MRLCheckResponse(BaseModel):
    """Schema for MRL compliance check response."""
    pesticide: str = Field(..., description="Pesticide name")
    fruit: str = Field(..., description="Fruit type")
    country: str = Field(..., description="Export target country")
    mrl_limit: Optional[float] = Field(None, description="Maximum Residue Limit")
    unit: str = Field(default="mg/kg", description="Unit of measurement")
    is_compliant: Optional[bool] = Field(None, description="Whether compliant with limit")
    recommendation: Optional[str] = Field(None, description="Compliance recommendation")
    found: bool = Field(..., description="Whether MRL data was found")
    
    class Config:
        json_schema_extra = {
            "example": {
                "pesticide": "Mancozeb",
                "fruit": "mango",
                "country": "EU",
                "mrl_limit": 2.0,
                "unit": "mg/kg",
                "is_compliant": True,
                "recommendation": "Ensure residue levels are below 2.0 mg/kg",
                "found": True
            }
        }


class ExportRequirementsRequest(BaseModel):
    """Schema for export requirements request."""
    country: str = Field(..., description="Target export country")
    fruit: str = Field(..., description="Fruit type")
    
    class Config:
        json_schema_extra = {
            "example": {
                "country": "EU",
                "fruit": "mango"
            }
        }


class ExportRequirementsResponse(BaseModel):
    """Schema for export requirements response."""
    country: str = Field(..., description="Target export country")
    fruit: str = Field(..., description="Fruit type")
    certifications: List[str] = Field(default=[], description="Required certifications")
    mrl_standard: Optional[str] = Field(None, description="MRL standard reference")
    phytosanitary: Optional[str] = Field(None, description="Phytosanitary requirements")
    packaging: Optional[str] = Field(None, description="Packaging requirements")
    additional_requirements: Optional[Dict[str, Any]] = Field(None, description="Other requirements")
    found: bool = Field(..., description="Whether requirements were found")
    
    class Config:
        json_schema_extra = {
            "example": {
                "country": "EU",
                "fruit": "mango",
                "certifications": ["GlobalGAP", "Phytosanitary Certificate"],
                "mrl_standard": "EU MRL Database",
                "phytosanitary": "Pest-free certification required",
                "packaging": "EU packaging directives compliant",
                "additional_requirements": {"traceability": "Full supply chain"},
                "found": True
            }
        }


class WebSearchRequest(BaseModel):
    """Schema for web search request."""
    query: str = Field(..., min_length=3, max_length=500, description="Search query")
    max_results: int = Field(default=5, ge=1, le=10, description="Maximum results")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "mango export regulations Pakistan to EU 2024",
                "max_results": 5
            }
        }


class WebSearchResult(BaseModel):
    """Schema for a single web search result."""
    title: str = Field(..., description="Result title")
    url: str = Field(..., description="Result URL")
    content: str = Field(..., description="Result snippet/content")
    score: Optional[float] = Field(None, description="Relevance score")


class WebSearchResponse(BaseModel):
    """Schema for web search response."""
    query: str = Field(..., description="Search query")
    results: List[WebSearchResult] = Field(default=[], description="Search results")
    count: int = Field(..., description="Number of results")


class UpdateConversationTitleRequest(BaseModel):
    """Schema for updating conversation title."""
    title: str = Field(..., min_length=1, max_length=200, description="New conversation title")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Mango disease prevention discussion"
            }
        }


class DeleteConversationResponse(BaseModel):
    """Schema for delete conversation response."""
    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Status message")
