"""
Groq LLM Client with Function Calling Support

This module provides integration with Groq API for generating
responses with tool/function calling capabilities.

Uses the Groq API via the Groq Python SDK.
"""

from groq import Groq
import json
import logging
from typing import List, Dict, Any, Optional
from src.core.config import get_settings

logger = logging.getLogger(__name__)


class GroqClient:
    """
    Client for Groq LLM with function calling support.
    """
    
    # System prompt for the agricultural AI assistant
    SYSTEM_PROMPT = """You are FRESH AI Assistant, an expert agricultural advisor specializing in fruit disease management for these fruits ONLY:
- Orange
- Guava
- Grapefruit
- Mango

You MUST only provide advice for these four fruits. If a user asks about any other fruit, politely decline and explain that you only support these four fruits.

Your specializations for these fruits:
- Disease identification, prevention, and treatment
- Pesticide recommendations and Maximum Residue Limit (MRL) compliance
- Export requirements to international markets
- Orchard management best practices
- Weather monitoring and forecasting

Your responses should be:
1. Accurate and based on scientific research
2. Practical and actionable for farmers
3. Safety-conscious regarding pesticide usage
4. Culturally aware (support Urdu where relevant)

CRITICAL DATA HANDLING RULES:
- When you receive weather data from tools, use ONLY that exact data - NEVER invent or hardcode values
- For weather queries: Present temperature, humidity, rainfall, wind speed EXACTLY as provided
- Never say "based on typical" or use assumed values - use only what you're given
- If data is missing or incomplete, clearly state that
- When user asks about their orchards: ALWAYS use get_user_orchards tool
- NEVER invent orchard names, IDs, or details - use ONLY what the database returns
- If tool shows user has no orchards, say "You have no orchards registered"
- If tool returns specific orchards, list EXACTLY what was returned with actual IDs and names

RESPONSE FORMAT REQUIREMENTS:
- Start with a clear heading (short title of the response) in UPPERCASE
- Follow with well-structured content
- Use clean, readable formatting without markdown symbols (#, *, "", +, ~, `)
- For lists: Use numbering (1., 2., 3.) or bullet points with "- " on separate lines
- Ensure complete and thorough response to the question asked
- Keep paragraphs short and clear
- NEVER include function call syntax like <function=...> in your response text

CRITICAL: NEVER include any function call syntax, code snippets, or technical formatting in your response. Your response should be plain, readable text that directly answers the user's question.

When users ask about diseases, use the available tools to fetch current information.
When discussing treatments, always consider MRL compliance for export markets.
When unsure about current regulations or prices, use web search for real-time info.
When users ask about weather for their orchards:
- ALWAYS use the get_weather_risk_assessment tool with the orchard name provided
- Present the weather data in a clear, actionable format
- Use the EXACT values returned by the tool - never invent data
When users ask about prices for fruits (Orange, Guava, Grapefruit, Mango):
- ALWAYS use the get_fruit_price tool to fetch real market prices
- Present prices in BOTH Pakistani Rupees (PKR/kg) AND US Dollars (USD/kg)
- Include market information, seasonal variations, and quality grades
- Never make up or assume fruit prices - use only database/tool values
When users ask about their orchards:
- ALWAYS call get_user_orchards tool to fetch their orchard list
- Present ONLY the orchards returned by the database
- Include orchard ID, name, fruit types, and area if available
- Do NOT invent or assume orchard names

Be concise but thorough. Prioritize safety and compliance in all recommendations."""

    # Additional constraints layered separately (base prompt remains unchanged)
    ADDITIONAL_CONSTRAINTS_PROMPT = """CRITICAL CONSTRAINTS - Must Follow:

1. FRUIT RESTRICTION: Only respond to questions about Orange, Guava, Grapefruit, and Mango. For any other fruit, say: "I apologize, I can only provide advice for Orange, Guava, Grapefruit, and Mango. Your fruit is not currently supported."

2. RESPONSE FORMAT:
   - HEADING: Start with a clear heading in UPPERCASE (short title, max 10 words)
   - NO MARKDOWN: Do not use #, *, "", +, ~, `, or any markdown symbols
   - NO FUNCTION SYNTAX: NEVER include <function=...>, code blocks, or technical syntax in response
   - CLEAN TEXT: Use plain, readable text with proper spacing
   - COMPLETE: Provide thorough answer to the entire question asked

3. LIST FORMATTING:
   - Use numbered lists: 1. Item, 2. Item, 3. Item (each on separate line)
   - OR use bullet points: - Item, - Item, - Item (each on separate line)
   - Keep items concise but complete

4. PARAGRAPH STRUCTURE:
   - Use short paragraphs (2-3 sentences maximum)
   - Add blank line between paragraphs
   - Ensure information flows logically

5. FOR TOOLS - CRITICAL FOR WEATHER:
   - When tools provide weather data (temperature, humidity, rainfall, wind), use those EXACT values
   - Never invent or assume weather values
   - Present weather measurements exactly as provided by tools
   - For orchard weather queries: Use get_weather_risk_assessment tool with orchard name
   - Always present the EXACT temperature, humidity, rainfall, and wind speed from tool data

6. FOR TOOLS - CRITICAL FOR ORCHARDS:
   - When user asks about their orchards, ALWAYS call get_user_orchards tool
   - Use ONLY the orchards returned by the database
   - NEVER invent orchard names, IDs, locations, or fruit types
   - If database returns empty list, say: "You have no orchards registered. Create an orchard to get started."
   - If database returns orchards, list them with: ID, Name, Fruit Types, Area (if available)
   - Format orchards as a clear list with actual values from database

7. NEVER:
   - Invent factual values when tools are available
   - Expose internal technical details
   - End mid-sentence or mid-list
   - Use symbols instead of plain text
   - Hardcode weather data like "27.1°C" if it's not from the tool results
   - Make up orchard names or details not from database
   - Include function call syntax like <function=get_disease_info>{...} in your response

8. EXAMPLE FORMATS:

WEATHER EXAMPLE:
NORTH FIELD FARM WEATHER STATUS

Current conditions for North Field Farm have been retrieved from the database.

Current Weather
Temperature: 22.5°C
Humidity: 65%
Rainfall: 0 mm
Wind Speed: 4.2 km/h
Last recorded at 2024-03-26 10:00 AM

DISEASE TREATMENT EXAMPLE:
ANTHRACNOSE TREATMENT IN MANGOES

Anthracnose in mangoes causes circular, sunken lesions on the fruit's skin. Here are the recommended treatments:

1. Remove infected fruit: Regularly inspect the orchard and remove any infected mangoes to prevent spread
2. Improve orchard sanitation: Remove weeds, prune diseased trees, and dispose of infected fruit
3. Apply fungicides: Use chlorothalonil or copper oxychloride according to recommended dosages

PRICE EXAMPLE:
MANGO MARKET PRICES IN PAKISTAN

Current market prices for mangoes are fluctuating based on season and quality. Here is the pricing information:

Market Rates
Local Market Price (PKR): 60-200 per kilogram
International Price (USD): 0.23-0.75 per kilogram
Average Rate (PKR): 120 per kilogram
Average Rate (USD): 0.45 per kilogram

Quality Grades
1. Premium (Anwar Ratol): 100-200 PKR/kg
2. Standard (Chaunsa): 60-120 PKR/kg
3. Economy Grade: Starting from 60 PKR/kg

Seasonal Information
Peak Season (May-August): Lower prices due to abundant supply
Off-Season: Premium pricing, limited availability
Major Markets: Karachi, Multan, Lahore

Note: Prices vary by region, season, and quality. Contact local markets for exact current quotes.

ORCHARDS EXAMPLE:
YOUR REGISTERED ORCHARDS

You have 2 registered orchards. Here are the details:

1. North Field Farm (ID: abc-123)
   Fruit types: Mango, Guava
   Area: 15 hectares

2. East Valley Orchard (ID: def-456)
   Fruit types: Orange, Grapefruit
   Area: 22 hectares"""

    def __init__(self):
        """Initialize the Groq client with API configuration."""
        settings = get_settings()
        
        if not settings.groq_api_key:
            logger.warning("GROQ_API_KEY not configured - AI Assistant will not function")
            self.client = None
            self.model_name = None
            return
        
        self.client = Groq(api_key=settings.groq_api_key)
        self.model_name = "llama-3.1-8b-instant"
        
        logger.info("Groq client initialized successfully")
    
    def _sanitize_response(self, response: str) -> str:
        """Minimal cleanup without trimming content."""
        import re
        
        # Remove function call syntax like <function=get_disease_info>{...}</function>
        cleaned = re.sub(r'<function=[^>]+>.*?</function>', '', response, flags=re.DOTALL)
        cleaned = re.sub(r'<function=[^>]+>\{[^}]*\}', '', cleaned)
        
        # Remove markdown heading symbols
        cleaned = cleaned.replace("###", "").replace("##", "").replace("#", "")
        # Remove backticks and tildes
        cleaned = cleaned.replace("`", "").replace("~", "")
        # Remove asterisks used for bold/italic
        cleaned = cleaned.replace("**", "").replace("*", "")

        unicode_bold_upper = {chr(0x1D400 + i): chr(ord('A') + i) for i in range(26)}
        unicode_bold_lower = {chr(0x1D41A + i): chr(ord('a') + i) for i in range(26)}
        unicode_bold_digits = {chr(0x1D7CE + i): str(i) for i in range(10)}
        unicode_map = {**unicode_bold_upper, **unicode_bold_lower, **unicode_bold_digits}

        for unicode_char, regular_char in unicode_map.items():
            cleaned = cleaned.replace(unicode_char, regular_char)

        cleaned_lines = []
        skip_keywords = [
            "based on the information",
            "the system can't find",
            "the system cannot find",
            "gathered data",
            "gathered information",
            "the data mentions",
        ]

        for line in cleaned.split('\n'):
            line_lower = line.lower().strip()
            if line.strip() and not any(keyword in line_lower for keyword in skip_keywords):
                cleaned_lines.append(line.strip())

        return "\n".join(cleaned_lines).strip()

    def _parse_tool_arguments(self, raw_arguments: Any) -> Dict[str, Any]:
        """Safely parse tool call arguments from Groq response."""
        if isinstance(raw_arguments, dict):
            return raw_arguments
        if isinstance(raw_arguments, str):
            try:
                parsed = json.loads(raw_arguments)
                return parsed if isinstance(parsed, dict) else {"value": parsed}
            except Exception:
                return {}
        return {}

    def _chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ):
        """Create a Groq chat completion request with optional tools."""
        request_kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools is not None:
            request_kwargs["tools"] = tools
            request_kwargs["tool_choice"] = "auto"

        return self.client.chat.completions.create(**request_kwargs)

    async def _request_continuation(self, messages_list: List[Dict[str, str]], partial_response: str) -> str:
        """Request a short continuation when model output is truncated by length."""
        try:
            continuation_messages = list(messages_list)
            continuation_messages.append({"role": "assistant", "content": partial_response})
            continuation_messages.append({
                "role": "user",
                "content": (
                    "Continue only the unfinished part. "
                    "Do not repeat prior lines. "
                    "Finish any incomplete sentence or list item concisely."
                )
            })

            continuation_response = self.client.chat.completions.create(
                model=self.model_name,
                messages=continuation_messages,
                temperature=0.3,
                max_tokens=512
            )

            if continuation_response.choices and continuation_response.choices[0].message:
                return continuation_response.choices[0].message.content or ""
            return ""
        except Exception as e:
            logger.warning(f"Continuation request failed: {str(e)}")
            return ""

    def _merge_partial_and_continuation(self, partial_response: str, continuation: str) -> str:
        """Merge primary and continuation text without duplication artifacts."""
        if not continuation.strip():
            return partial_response

        partial = partial_response.rstrip()
        cont = continuation.lstrip()

        overlap_window = min(80, len(partial), len(cont))
        for size in range(overlap_window, 10, -1):
            if partial[-size:].strip() and partial[-size:].strip() == cont[:size].strip():
                cont = cont[size:].lstrip()
                break

        return f"{partial}\n{cont}".strip()
    
    def _format_response(self, response: str) -> str:
        """
        Format response with proper heading, structured content, and clean text.
        Ensures heading is clear, content is complete, and structure is readable.
        
        Args:
            response: Raw response from Groq
            
        Returns:
            Formatted response ready for display
        """
        # Clean the response first
        cleaned = self._sanitize_response(response)
        
        if not cleaned:
            return ""
        
        lines = [line for line in cleaned.split('\n') if line.strip()]
        
        if not lines:
            return ""
        
        # If response is a single line, still provide heading-first format
        if len(lines) == 1:
            single = lines[0]
            heading_words = single.split()[:7]
            heading = " ".join(heading_words).upper() if heading_words else "RESPONSE"
            return f"{heading}\n\n{single}".strip()
        
        # Detect heading (first line, if it looks like a heading)
        first_line = lines[0].strip()
        
        # Heading detection: All caps, short, or ends with colon
        is_heading = (
            (first_line.isupper() or ':' in first_line) or 
            (len(first_line) < 70 and not first_line[0].islower())
        )
        
        if is_heading:
            # Use first line as heading
            heading = first_line.upper() if not first_line.isupper() else first_line
            # Ensure no markdown in heading
            heading = heading.replace('**', '').replace('*', '').replace('#', '')
            
            # Rest is content
            body = '\n'.join(lines[1:]).strip()
            
            # Format: Heading, blank line, then body (no markdown asterisks)
            return f"{heading}\n\n{body}".strip()
        else:
            # No clear heading - use first substantial line as heading if it's short
            if len(first_line) < 70:
                heading = first_line.upper()
                body = '\n'.join(lines[1:]).strip()
                return f"{heading}\n\n{body}".strip()
            else:
                # Long first line - just return the content as is, nicely formatted
                return '\n'.join(lines).strip()

    def _build_messages(
        self,
        user_messages: List[Dict[str, str]],
        context: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Build messages with system prompt and optional context on latest user message."""
        messages_list = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "system", "content": self.ADDITIONAL_CONSTRAINTS_PROMPT}
        ]

        conversation = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in user_messages
        ]

        if context and conversation:
            last_msg = conversation[-1]
            if last_msg.get("role") == "user":
                last_msg["content"] = f"Context: {context}\n\nUser Query: {last_msg['content']}"

        messages_list.extend(conversation)
        return messages_list
    
    def _convert_tools_to_groq_format(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert tool definitions to Groq API function calling format.
        
        Args:
            tools: List of tool definitions with name, description, and parameters
            
        Returns:
            List of tool objects for Groq API
        """
        groq_tools = []
        
        for tool in tools:
            groq_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {
                        "type": "object",
                        "properties": {},
                        "required": []
                    })
                }
            }
            groq_tools.append(groq_tool)
        
        return groq_tools
    
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
                "response": "AI Assistant is not configured. Please set the GROQ_API_KEY.",
                "tool_calls": [],
                "error": True
            }
        
        try:
            # Convert tools to Groq format
            groq_tools = self._convert_tools_to_groq_format(tools)
            
            # Build conversation messages with system prompt
            messages_list = self._build_messages(messages, context=context)
            
            # Make API request
            response = self._chat_completion(
                messages=messages_list,
                tools=groq_tools,
                temperature=0.7,
                max_tokens=2048
            )
            
            # Process response
            result = {
                "response": "",
                "tool_calls": [],
                "finish_reason": None,
                "error": False
            }
            
            # Extract message and tool calls
            if response.choices:
                choice = response.choices[0]
                
                if choice.message:
                    message = choice.message
                    
                    # Extract text content
                    if message.content:
                        merged_content = message.content
                        if choice.finish_reason == "length":
                            continuation = await self._request_continuation(messages_list, message.content)
                            merged_content = self._merge_partial_and_continuation(message.content, continuation)
                        result["response"] = self._format_response(merged_content)
                    
                    # Extract tool calls
                    if hasattr(message, 'tool_calls') and message.tool_calls:
                        for tool_call in message.tool_calls:
                            result["tool_calls"].append({
                                "name": tool_call.function.name,
                                "arguments": self._parse_tool_arguments(tool_call.function.arguments)
                            })
                
                if choice.finish_reason:
                    result["finish_reason"] = choice.finish_reason
            
            return result
            
        except Exception as e:
            logger.error(f"Groq API error: {str(e)}")
            return {
                "response": "I encountered an error processing your request. Please try again.",
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
            return "AI Assistant is not configured. Please set the GROQ_API_KEY."
        
        try:
            # Build conversation messages with system prompt
            user_messages = []
            if conversation_history:
                user_messages.extend(conversation_history)
            user_messages.append({"role": "user", "content": prompt})

            messages_list = self._build_messages(user_messages, context=context)
            
            # Make API request
            response = self._chat_completion(
                messages=messages_list,
                temperature=0.7,
                max_tokens=2048
            )
            
            # Extract response text
            if response.choices and response.choices[0].message:
                choice = response.choices[0]
                raw_response = choice.message.content or "I couldn't generate a response."
                if choice.finish_reason == "length":
                    continuation = await self._request_continuation(messages_list, raw_response)
                    raw_response = self._merge_partial_and_continuation(raw_response, continuation)
                return self._format_response(raw_response)
            
            return "I encountered an unexpected response format."
            
        except Exception as e:
            logger.error(f"Groq generation error: {str(e)}")
            return "I encountered an error. Please try again."
    
    async def generate_with_tool_results(
        self,
        original_prompt: str,
        tool_results: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate a final response incorporating tool execution results.
        Uses tool results to inform the response but does not expose data format.
        
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
            # Build structured tool results summary
            results_summary = ""
            
            for result in tool_results:
                tool_name = result.get("tool_name", "Unknown Tool")
                data = result.get("data", {})
                success = result.get("success", False)
                
                if not success:
                    logger.warning(f"Tool {tool_name} did not return success")
                    continue
                
                # Format weather data specially for clarity
                if tool_name == "get_weather_risk_assessment" and isinstance(data, dict):
                    if data.get("found"):
                        results_summary += f"\n=== WEATHER DATA FOR: {data.get('orchard_name', 'Unknown')} ===\n"
                        current = data.get("current_weather", {})
                        if current:
                            results_summary += f"Recorded at: {current.get('recorded_at', 'N/A')}\n"
                            results_summary += f"Temperature: {current.get('temperature')}°C\n"
                            results_summary += f"Humidity: {current.get('humidity')}%\n"
                            results_summary += f"Rainfall: {current.get('rainfall')} mm\n"
                            results_summary += f"Wind Speed: {current.get('wind_speed')} km/h\n"
                        
                        recent = data.get("recent_readings", [])
                        if recent:
                            results_summary += f"\nRecent readings ({len(recent)} previous records):\n"
                            for i, reading in enumerate(recent[:3], 1):
                                results_summary += f"  {i}. {reading.get('recorded_at', 'N/A')}: {reading.get('temperature')}°C, {reading.get('humidity')}% humidity, {reading.get('rainfall')}mm rain\n"
                    else:
                        results_summary += f"\nWeather data: {data.get('message', 'No data available')}\n"
                
                # Format orchard data specially
                elif tool_name == "get_user_orchards" and isinstance(data, dict):
                    if data.get("found"):
                        results_summary += f"\n=== USER ORCHARDS FROM DATABASE ===\n"
                        orchards = data.get("orchards", [])
                        results_summary += f"Total orchards: {len(orchards)}\n"
                        if orchards:
                            results_summary += "Orchard Details:\n"
                            for orchard in orchards:
                                results_summary += f"\nOrchard: {orchard.get('name', 'N/A')}\n"
                                results_summary += f"  ID: {orchard.get('id', 'N/A')}\n"
                                results_summary += f"  Fruit Types: {', '.join(orchard.get('fruit_types', [])) if orchard.get('fruit_types') else 'Not specified'}\n"
                                if orchard.get('area_hectares'):
                                    results_summary += f"  Area: {orchard.get('area_hectares')} hectares\n"
                    else:
                        results_summary += f"\n=== USER ORCHARDS ===\n"
                        results_summary += f"Status: {data.get('message', 'No orchards found')}\n"
                
                # Format price data specially
                elif tool_name == "get_fruit_price" and isinstance(data, dict):
                    if data.get("found"):
                        fruit = data.get("fruit", "Unknown")
                        results_summary += f"\n=== FRUIT PRICE DATA: {fruit.upper()} ===\n"
                        results_summary += f"Pakistan Market Price (PKR/kg): {data.get('pkr_per_kg', 'N/A')}\n"
                        results_summary += f"International Price (USD/kg): {data.get('usd_per_kg', 'N/A')}\n"
                        
                        if data.get('quality_grades'):
                            results_summary += "Quality Grades:\n"
                            for grade, price in data.get('quality_grades', {}).items():
                                results_summary += f"  {grade}: {price}\n"
                        
                        if data.get('seasonal_note'):
                            results_summary += f"Seasonal Information: {data.get('seasonal_note')}\n"
                        
                        if data.get('primary_markets'):
                            results_summary += f"Primary Markets: {', '.join(data.get('primary_markets', []))}\n"
                        
                        results_summary += f"Data Source: {data.get('data_source', 'Agricultural market data')}\n"
                    else:
                        results_summary += f"\n=== FRUIT PRICE ===\n"
                        results_summary += f"Error: {data.get('error', 'Price data not available')}\n"
                
                # Format disease/treatment results
                elif tool_name in ["get_disease_info", "get_diseases_by_fruit", "get_treatments"] and isinstance(data, dict):
                    if data.get("found"):
                        results_summary += f"\n=== {tool_name.upper().replace('_', ' ')} RESULTS ===\n"
                        # Add all relevant fields
                        for key, value in data.items():
                            if key not in ["found", "success", "tool_name"] and value:
                                results_summary += f"{key}: {str(value)[:500]}\n"
                
                # Format other results
                elif isinstance(data, dict):
                    results_summary += f"\n=== {tool_name.upper().replace('_', ' ')} ===\n"
                    for key, value in data.items():
                        if key not in ["found", "success", "tool_name", "error"] and value:
                            results_summary += f"{key}: {str(value)[:300]}\n"
            
            # Build the final prompt with explicit instructions
            full_prompt = f"""User Question: {original_prompt}

TOOL RESULTS DATA:
{results_summary}

INSTRUCTIONS:
1. Use ONLY the data provided in the TOOL RESULTS section above
2. Do NOT invent, assume, or use hardcoded values
3. If weather data is provided (temperature, humidity, etc.), use the EXACT values shown
4. If orchard data is provided, list EXACTLY what the database returned - no made-up orchards
5. Present the information naturally without saying "based on the information" or similar phrases
6. Follow the response format rules from your system prompt

Answer the user's question now:"""
            
            logger.info(f"Tool results for response generation:\n{results_summary}")
            
            response = await self.generate_response(full_prompt, conversation_history=conversation_history)
            return response
            
        except Exception as e:
            logger.error(f"Error generating response with tool results: {str(e)}")
            return "I gathered some information but encountered an error formatting the response."
