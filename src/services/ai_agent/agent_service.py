"""
AI Agent Service - Main Orchestrator

This module provides the main AI Agent service that orchestrates
conversations, tool calling, and response generation using Groq LLM.
"""

from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from datetime import datetime
import json
import logging

from src.core.supabase_client import admin_supabase
from .groq_client import GroqClient
from .tools import AgentTools
from .tavily_client import TavilyClient

logger = logging.getLogger(__name__)


class AIAgentService:
    """
    Main AI Agent service that orchestrates the conversation flow:
    1. Receives user messages
    2. Determines intent and required tools
    3. Executes tools to gather information
    4. Generates contextual responses using Groq
    5. Manages conversation history
    """
    
    MAX_TOOL_ITERATIONS = 3  # Maximum tool calling iterations per request
    
    def __init__(self, user_id: str = None):
        """
        Initialize the AI Agent service.
        
        Args:
            user_id: Current user's ID for user-specific operations
        """
        self.groq = GroqClient()
        self.tools = AgentTools(admin_supabase, user_id)
        self.tavily = TavilyClient()
        self.user_id = user_id
        self.db = admin_supabase
    
    async def process_message(
        self,
        user_id: str,
        message: str,
        conversation_id: str = None
    ) -> Dict[str, Any]:
        """
        Main entry point - processes user message through the agent pipeline.
        
        Pipeline:
        1. Load or create conversation
        2. Build context from conversation history
        3. Generate response with potential tool calls
        4. Execute tools if requested
        5. Generate final response with tool results
        6. Save to conversation history
        7. Return structured response
        
        Args:
            user_id: User ID making the request
            message: User's message
            conversation_id: Optional existing conversation ID
            
        Returns:
            ChatResponse with response, conversation_id, and metadata
        """
        self.user_id = user_id
        self.tools.user_id = user_id
        
        try:
            # Step 1: Load or create conversation
            conversation = await self._get_or_create_conversation(
                user_id, conversation_id
            )
            conv_id = conversation["id"]
            
            # Step 2: Load conversation history
            history = await self._load_conversation_history(conv_id)
            
            # Step 3: Add user message to history
            history.append({"role": "user", "content": message})
            
            # Step 4: Generate response with tools
            tools_used = []
            tool_results = []
            
            # CRITICAL: Check if user is asking about their orchards or weather for orchards
            # If so, FORCE the appropriate tool calls before generating response
            message_lower = message.lower()
            orchard_keywords = ["orchards", "my orchards", "registered orchards", "listed orchards", "farms", "my farms", "what orchards"]
            weather_keywords = ["weather", "forecast", "temperature", "humidity", "rainfall", "wind"]
            price_keywords = ["price", "cost", "rate", "how much", "expensive", "cheap", "rupee", "rs", "pkr", "usd", "dollar"]
            supported_fruits = ["orange", "mango", "guava", "grapefruit"]
            
            is_orchard_query = any(keyword in message_lower for keyword in orchard_keywords)
            is_weather_query = any(keyword in message_lower for keyword in weather_keywords)
            is_price_query = any(keyword in message_lower for keyword in price_keywords) and any(fruit in message_lower for fruit in supported_fruits)
            
            # If weather query for orchards, fetch orchards first, then weather for each
            if is_weather_query and is_orchard_query:
                logger.info("Weather query for orchards detected - fetching orchards and weather")
                # Get user's orchards
                orchards_result = await self.tools.get_user_orchards()
                if orchards_result.get("found") and orchards_result.get("orchards"):
                    tool_results.append({
                        "tool_name": "get_user_orchards",
                        "success": True,
                        "data": orchards_result
                    })
                    tools_used.append("get_user_orchards")
                    
                    # Get weather for each orchard
                    for orchard in orchards_result.get("orchards", []):
                        orchard_name = orchard.get("name")
                        weather_result = await self.tools.get_weather_risk_assessment(orchard_name)
                        if weather_result.get("found"):
                            tool_results.append({
                                "tool_name": "get_weather_risk_assessment",
                                "success": True,
                                "data": weather_result
                            })
                            tools_used.append("get_weather_risk_assessment")
                else:
                    tool_results.append({
                        "tool_name": "get_user_orchards",
                        "success": True,
                        "data": orchards_result
                    })
                    tools_used.append("get_user_orchards")
            elif is_orchard_query:
                logger.info("Orchard query detected - fetching user orchards")
                # Get user's orchards
                orchards_result = await self.tools.get_user_orchards()
                tool_results.append({
                    "tool_name": "get_user_orchards",
                    "success": True,
                    "data": orchards_result
                })
                tools_used.append("get_user_orchards")
            elif is_price_query:
                logger.info("Price query detected - fetching fruit prices")
                # Extract fruit name from message
                fruit_name = None
                for fruit in supported_fruits:
                    if fruit in message_lower:
                        fruit_name = fruit
                        break
                
                if fruit_name:
                    price_result = await self.tools.get_fruit_price(fruit_name)
                    tool_results.append({
                        "tool_name": "get_fruit_price",
                        "success": True,
                        "data": price_result
                    })
                    tools_used.append("get_fruit_price")
            
            # First pass - check if tools are needed (for non-orchard/weather/price queries)
            if not tools_used:
                response = await self.groq.generate_with_tools(
                    messages=history,
                    tools=AgentTools.TOOL_DEFINITIONS
                )
            else:
                response = {"response": "", "tool_calls": []}
            
            # Step 5: Execute tools if requested (with iteration limit)
            iteration = 0
            while response.get("tool_calls") and iteration < self.MAX_TOOL_ITERATIONS:
                iteration += 1
                logger.info(f"Tool iteration {iteration}: {len(response['tool_calls'])} tools requested")
                
                for tool_call in response["tool_calls"]:
                    tool_name = tool_call.get("name")
                    tool_args = tool_call.get("arguments", {})
                    
                    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                    
                    result = await self.tools.execute_tool(tool_name, tool_args)
                    tool_results.append(result)
                    tools_used.append(tool_name)
                
                # Generate response with tool results
                if tool_results:
                    final_response = await self.groq.generate_with_tool_results(
                        original_prompt=message,
                        tool_results=tool_results,
                        conversation_history=history[:-1]  # Exclude last user message
                    )
                    response["response"] = final_response
                    response["tool_calls"] = []  # Clear tool calls after processing
            
            # If we have tool results from orchard/weather detection, generate response with them
            if tool_results and not response.get("response"):
                final_response = await self.groq.generate_with_tool_results(
                    original_prompt=message,
                    tool_results=tool_results,
                    conversation_history=history[:-1]  # Exclude last user message
                )
                response["response"] = final_response
            
            # Step 6: Save messages to conversation history
            assistant_response = response.get("response", "I apologize, but I couldn't generate a response.")
            
            await self._save_message(conv_id, "user", message)
            await self._save_message(
                conv_id, 
                "assistant", 
                assistant_response,
                tool_calls=tools_used if tools_used else None
            )
            
            # Step 7: Update conversation timestamp
            await self._update_conversation_timestamp(conv_id)
            
            # Step 8: Build and return response
            return {
                "response": assistant_response,
                "conversation_id": UUID(conv_id),
                "tools_used": list(set(tools_used)) if tools_used else None,
                "rich_content": self._extract_rich_content(tool_results),
                "actions": self._extract_actions(assistant_response, tool_results)
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                "response": "I apologize, but I encountered an error processing your request. Please try again.",
                "conversation_id": UUID(conversation_id) if conversation_id else uuid4(),
                "tools_used": None,
                "rich_content": None,
                "actions": None,
                "error": str(e)
            }
    
    async def _get_or_create_conversation(
        self,
        user_id: str,
        conversation_id: str = None
    ) -> Dict[str, Any]:
        """
        Get existing conversation or create a new one.
        
        Args:
            user_id: User ID
            conversation_id: Optional existing conversation ID
            
        Returns:
            Conversation record
        """
        if conversation_id:
            # Try to fetch existing conversation
            try:
                response = self.db.table("ai_conversations").select("*").eq(
                    "id", conversation_id
                ).eq("user_id", user_id).single().execute()
                
                if response.data:
                    return response.data
            except Exception as e:
                logger.warning(f"Could not find conversation {conversation_id}: {e}")
        
        # Create new conversation
        new_conv = {
            "id": str(uuid4()),
            "user_id": user_id,
            "title": "New Conversation",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        try:
            response = self.db.table("ai_conversations").insert(new_conv).execute()
            return response.data[0] if response.data else new_conv
        except Exception as e:
            logger.warning(f"Could not save conversation to DB: {e}")
            return new_conv
    
    async def _load_conversation_history(
        self,
        conversation_id: str,
        limit: int = 20
    ) -> List[Dict[str, str]]:
        """
        Load recent conversation history.
        
        Args:
            conversation_id: Conversation ID
            limit: Maximum messages to load
            
        Returns:
            List of message dicts with role and content
        """
        try:
            response = self.db.table("ai_messages").select(
                "role, content"
            ).eq(
                "conversation_id", conversation_id
            ).order(
                "created_at", desc=False
            ).limit(limit).execute()
            
            if response.data:
                return [{"role": m["role"], "content": m["content"]} for m in response.data]
        except Exception as e:
            logger.warning(f"Could not load conversation history: {e}")
        
        return []
    
    async def _save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_calls: List[str] = None
    ) -> None:
        """
        Save a message to the conversation history.
        
        Args:
            conversation_id: Conversation ID
            role: Message role (user/assistant)
            content: Message content
            tool_calls: Optional list of tools used
        """
        try:
            message = {
                "id": str(uuid4()),
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "tool_calls": tool_calls,
                "created_at": datetime.utcnow().isoformat()
            }
            
            self.db.table("ai_messages").insert(message).execute()
        except Exception as e:
            logger.warning(f"Could not save message to DB: {e}")
    
    async def _update_conversation_timestamp(self, conversation_id: str) -> None:
        """Update conversation's last activity timestamp."""
        try:
            self.db.table("ai_conversations").update({
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", conversation_id).execute()
        except Exception as e:
            logger.warning(f"Could not update conversation timestamp: {e}")
    
    def _extract_rich_content(
        self,
        tool_results: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Extract structured rich content from tool results for UI rendering.
        
        Args:
            tool_results: Results from tool executions
            
        Returns:
            Structured content for rich UI rendering
        """
        if not tool_results:
            return None
        
        rich_content = {}
        
        for result in tool_results:
            if not result.get("success"):
                continue
            
            tool_name = result.get("tool_name")
            data = result.get("data", {})
            
            if tool_name == "get_disease_info" and data.get("found"):
                rich_content["disease"] = {
                    "name": data.get("name"),
                    "name_urdu": data.get("name_urdu"),
                    "symptoms": data.get("symptoms", []),
                    "prevention": data.get("prevention", [])
                }
            
            elif tool_name == "get_treatments" and data.get("found"):
                rich_content["treatments"] = data.get("treatments", {})
            
            elif tool_name == "check_mrl_compliance" and data.get("found"):
                rich_content["mrl"] = {
                    "pesticide": data.get("pesticide"),
                    "fruit": data.get("fruit"),
                    "country": data.get("country"),
                    "limit": data.get("mrl_limit"),
                    "unit": data.get("unit", "mg/kg")
                }
            
            elif tool_name == "get_export_requirements" and data.get("found"):
                rich_content["export"] = data.get("requirements", {})
            
            elif tool_name == "web_search" and data.get("found"):
                rich_content["search_results"] = data.get("results", [])[:3]
        
        return rich_content if rich_content else None
    
    def _extract_actions(
        self,
        response: str,
        tool_results: List[Dict[str, Any]]
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Extract suggested actions from the response and tool results.
        
        Args:
            response: Assistant's response text
            tool_results: Results from tool executions
            
        Returns:
            List of suggested actions for the user
        """
        actions = []
        
        for result in tool_results:
            if not result.get("success"):
                continue
            
            tool_name = result.get("tool_name")
            data = result.get("data", {})
            
            # Suggest viewing disease details
            if tool_name == "get_disease_info" and data.get("found"):
                disease_name = data.get("name", "Unknown")
                actions.append({
                    "type": "navigate",
                    "label": f"View {disease_name} treatment options",
                    "action": "get_treatments",
                    "params": {"disease_name": disease_name}
                })
            
            # Suggest MRL check for treatments
            if tool_name == "get_treatments" and data.get("found"):
                treatments = data.get("treatments", {}).get("chemical", [])
                if treatments and len(treatments) > 0:
                    first_treatment = treatments[0].get("name", "")
                    if first_treatment:
                        actions.append({
                            "type": "query",
                            "label": f"Check MRL compliance for {first_treatment}",
                            "suggested_query": f"Is {first_treatment} compliant for export to EU?"
                        })
            
            # Suggest web search for more info
            if not data.get("found"):
                actions.append({
                    "type": "search",
                    "label": "Search web for more information",
                    "action": "web_search"
                })
        
        return actions if actions else None
    
    async def get_conversations(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get user's conversation list.
        
        Args:
            user_id: User ID
            limit: Maximum conversations to return
            
        Returns:
            List of conversation summaries
        """
        try:
            response = self.db.table("ai_conversations").select(
                "id, title, created_at, updated_at"
            ).eq(
                "user_id", user_id
            ).order(
                "updated_at", desc=True
            ).limit(limit).execute()
            
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching conversations: {e}")
            return []
    
    async def get_conversation_messages(
        self,
        user_id: str,
        conversation_id: str
    ) -> Dict[str, Any]:
        """
        Get all messages for a specific conversation.
        
        Args:
            user_id: User ID (for authorization)
            conversation_id: Conversation ID
            
        Returns:
            Conversation with messages
        """
        try:
            # Verify ownership
            conv_response = self.db.table("ai_conversations").select("*").eq(
                "id", conversation_id
            ).eq("user_id", user_id).single().execute()
            
            if not conv_response.data:
                return {"error": "Conversation not found"}
            
            # Get messages
            msg_response = self.db.table("ai_messages").select("*").eq(
                "conversation_id", conversation_id
            ).order("created_at", desc=False).execute()
            
            return {
                "conversation": conv_response.data,
                "messages": msg_response.data if msg_response.data else []
            }
        except Exception as e:
            logger.error(f"Error fetching conversation messages: {e}")
            return {"error": str(e)}
    
    async def delete_conversation(
        self,
        user_id: str,
        conversation_id: str
    ) -> bool:
        """
        Delete a conversation and its messages.
        
        Args:
            user_id: User ID (for authorization)
            conversation_id: Conversation ID to delete
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            # Verify ownership first
            conv_response = self.db.table("ai_conversations").select("id").eq(
                "id", conversation_id
            ).eq("user_id", user_id).single().execute()
            
            if not conv_response.data:
                return False
            
            # Delete messages first (if not using cascade)
            self.db.table("ai_messages").delete().eq(
                "conversation_id", conversation_id
            ).execute()
            
            # Delete conversation
            self.db.table("ai_conversations").delete().eq(
                "id", conversation_id
            ).execute()
            
            return True
        except Exception as e:
            logger.error(f"Error deleting conversation: {e}")
            return False
    
    async def update_conversation_title(
        self,
        user_id: str,
        conversation_id: str,
        title: str
    ) -> bool:
        """
        Update a conversation's title.
        
        Args:
            user_id: User ID (for authorization)
            conversation_id: Conversation ID
            title: New title
            
        Returns:
            True if updated, False otherwise
        """
        try:
            response = self.db.table("ai_conversations").update({
                "title": title,
                "updated_at": datetime.utcnow().isoformat()
            }).eq(
                "id", conversation_id
            ).eq("user_id", user_id).execute()
            
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error updating conversation title: {e}")
            return False