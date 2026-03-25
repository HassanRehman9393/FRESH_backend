"""
Gemini LLM Client with Function Calling Support

This module provides integration with Google's Gemini API for generating
responses with tool/function calling capabilities.

Uses the google-generativeai SDK.
"""

try:
    import google.generativeai as genai
    from google.generativeai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None
    types = None
    print("⚠️  Warning: google-generativeai not available. AI Assistant features will be disabled.")

from typing import List, Dict, Any, Optional
import json
import logging

from src.core.config import get_settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Client for Google's Gemini LLM with function calling support.
    """
    
    # System prompt for the agricultural AI assistant
    SYSTEM_PROMPT = """You are FRESH AI Assistant, an expert agricultural advisor specializing in:
- Fruit disease identification, prevention, and treatment
- Pesticide recommendations and Maximum Residue Limit (MRL) compliance
- Export requirements for fruits to international markets
- Best practices for orchard management

Your responses should be:
1. Accurate and based on scientific research
2. Practical and actionable for farmers
3. Safety-conscious regarding pesticide usage
4. Culturally aware (support Urdu where relevant)

When users ask about diseases, use the available tools to fetch current information.
When discussing treatments, always consider MRL compliance for export markets.
When unsure about current regulations or prices, use web search for real-time info.

Be concise but thorough. Prioritize safety and compliance in all recommendations."""

    def __init__(self):
        """Initialize the Gemini client with API configuration."""
        settings = get_settings()
        
        if not GENAI_AVAILABLE:
            logger.warning("google-generativeai not available - AI Assistant will not function")
            self.client = None
            self.model_name = None
            return
        
        if not settings.gemini_api_key:
            logger.warning("GEMINI_API_KEY not configured - AI Assistant will not function")
            self.client = None
            self.model_name = None
            return
        
        # Initialize the new genai client
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model_name = "gemini-2.5-flash"
        
        logger.info("Gemini client initialized successfully")
    
    def _convert_tools_to_genai_format(self, tools: List[Dict[str, Any]]):
        """
        Convert tool definitions to google-genai function calling format.
        
        Args:
            tools: List of tool definitions with name, description, and parameters
            
        Returns:
            List of Tool objects for google-genai
        """
        if not GENAI_AVAILABLE or not types:
            return []
            
        function_declarations = []
        
        for tool in tools:
            params = tool.get("parameters", {})
            properties = params.get("properties", {})
            required = params.get("required", [])
            
            # Build schema properties
            schema_properties = {}
            for prop_name, prop_schema in properties.items():
                prop_type = prop_schema.get("type", "STRING").upper()
                schema_properties[prop_name] = types.Schema(
                    type=prop_type,
                    description=prop_schema.get("description", "")
                )
            
            function_declarations.append(
                types.FunctionDeclaration(
                    name=tool["name"],
                    description=tool["description"],
                    parameters=types.Schema(
                        type="OBJECT",
                        properties=schema_properties,
                        required=required
                    ) if schema_properties else None
                )
            )
        
        return [types.Tool(function_declarations=function_declarations)]
    
    async def generate_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a response with function calling capabilities.
        
        Args:
            messages: Conversation history with 'role' and 'content'
            tools: Available tool definitions
            context: Optional additional context to include
            
        Returns:
            Dict containing response text, tool calls, and metadata
        """
        if not self.client:
            return {
                "response": "AI Assistant is not configured. Please set the GEMINI_API_KEY.",
                "tool_calls": [],
                "error": True
            }
        
        try:
            # Convert tools to Gemini format
            gemini_tools = self._convert_tools_to_genai_format(tools)
            
            # Build conversation content with system instruction
            contents = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
            
            # Add context if provided
            if context and contents:
                last_content = contents[-1].parts[0].text
                contents[-1] = types.Content(
                    role=contents[-1].role,
                    parts=[types.Part(text=f"Context: {context}\n\nUser Query: {last_content}")]
                )
            
            # Generate response with tools using the new SDK
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_PROMPT,
                    tools=gemini_tools
                )
            )
            
            # Process response
            result = {
                "response": "",
                "tool_calls": [],
                "finish_reason": None,
                "error": False
            }
            
            # Check for function calls
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        func_call = part.function_call
                        result["tool_calls"].append({
                            "name": func_call.name,
                            "arguments": dict(func_call.args) if func_call.args else {}
                        })
                    elif part.text:
                        result["response"] += part.text
            
            # Get finish reason if available
            if response.candidates:
                result["finish_reason"] = str(response.candidates[0].finish_reason)
            
            return result
            
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return {
                "response": f"I encountered an error processing your request. Please try again.",
                "tool_calls": [],
                "error": True,
                "error_message": str(e)
            }
    
    async def generate_response(
        self,
        prompt: str,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate a simple response without tool calling.
        
        Args:
            prompt: The user's prompt
            context: Optional additional context
            conversation_history: Optional conversation history
            
        Returns:
            Generated response text
        """
        if not self.client:
            return "AI Assistant is not configured. Please set the GEMINI_API_KEY."
        
        try:
            # Build full prompt with context
            full_prompt = prompt
            if context:
                full_prompt = f"Context:\n{context}\n\nUser Query:\n{prompt}"
            
            # Build conversation if history provided
            if conversation_history:
                contents = []
                for msg in conversation_history:
                    role = "user" if msg["role"] == "user" else "model"
                    contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
                contents.append(types.Content(role="user", parts=[types.Part(text=full_prompt)]))
                
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(system_instruction=self.SYSTEM_PROMPT)
                )
            else:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(system_instruction=self.SYSTEM_PROMPT)
                )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini generation error: {str(e)}")
            return f"I encountered an error. Please try again."
    
    async def generate_with_tool_results(
        self,
        original_prompt: str,
        tool_results: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate a final response incorporating tool execution results.
        
        Args:
            original_prompt: The original user query
            tool_results: Results from tool executions
            conversation_history: Optional conversation history
            
        Returns:
            Final response incorporating tool results
        """
        if not self.client:
            return "AI Assistant is not configured."
        
        try:
            # Format tool results as context
            results_context = "I've gathered the following information:\n\n"
            for result in tool_results:
                tool_name = result.get("tool_name", "Unknown Tool")
                data = result.get("data", {})
                results_context += f"**{tool_name}:**\n{json.dumps(data, indent=2, default=str)}\n\n"
            
            # Generate response with tool results as context
            full_prompt = f"""Based on the user's question and the information I gathered:

User Question: {original_prompt}

{results_context}

Please provide a helpful, comprehensive response that addresses the user's question using the information above. 
Be specific, practical, and include relevant details from the gathered data."""
            
            response = await self.generate_response(full_prompt, conversation_history=conversation_history)
            return response
            
        except Exception as e:
            logger.error(f"Error generating response with tool results: {str(e)}")
            return "I gathered some information but encountered an error formatting the response."
