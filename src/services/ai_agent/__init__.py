"""
AI Agent Service Module

This module provides AI-powered assistant capabilities using Google's Gemini LLM
with function calling for disease information, treatment recommendations,
MRL compliance checking, and web search functionality.
"""

from .agent_service import AIAgentService
from .tools import AgentTools
from .gemini_client import GeminiClient
from .tavily_client import TavilyClient

__all__ = [
    "AIAgentService",
    "AgentTools", 
    "GeminiClient",
    "TavilyClient"
]
