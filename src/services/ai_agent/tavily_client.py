"""
Tavily Web Search Client

This module provides integration with the Tavily API for real-time
web search capabilities, useful for fetching current regulations,
prices, and agricultural news.
"""

import httpx
from typing import List, Dict, Any, Optional
import logging

from src.core.config import settings

logger = logging.getLogger(__name__)


class TavilyClient:
    """
    Client for Tavily web search API.
    
    Provides real-time web search capabilities for:
    - Current agricultural regulations
    - Market prices
    - Latest research on plant diseases
    - Export requirements updates
    """
    
    BASE_URL = "https://api.tavily.com"
    
    def __init__(self):
        """Initialize the Tavily client."""
        self.api_key = settings.tavily_api_key
        
        if not self.api_key:
            logger.warning("TAVILY_API_KEY not configured - web search will not function")
    
    async def search(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "basic",
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search the web using Tavily API.
        
        Args:
            query: Search query string
            max_results: Maximum number of results (default: 5)
            search_depth: "basic" or "advanced" (default: "basic")
            include_domains: Optional list of domains to include
            exclude_domains: Optional list of domains to exclude
            
        Returns:
            List of search results with title, url, content, and score
        """
        if not self.api_key:
            logger.warning("Tavily API key not configured")
            return []
        
        try:
            payload = {
                "api_key": self.api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": search_depth
            }
            
            if include_domains:
                payload["include_domains"] = include_domains
            
            if exclude_domains:
                payload["exclude_domains"] = exclude_domains
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/search",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                logger.info(f"Tavily search returned {len(results)} results for: {query[:50]}...")
                
                return results
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Tavily API HTTP error: {e.response.status_code}")
            return []
        except httpx.RequestError as e:
            logger.error(f"Tavily API request error: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Tavily search error: {str(e)}")
            return []
    
    async def search_agricultural_news(
        self,
        topic: str,
        country: Optional[str] = None,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for agricultural news and updates.
        
        Args:
            topic: Agricultural topic to search for
            country: Optional country to focus on
            max_results: Maximum results
            
        Returns:
            List of relevant news articles
        """
        query = f"{topic} agriculture farming"
        if country:
            query = f"{query} {country}"
        
        # Include trusted agricultural sources
        include_domains = [
            "fao.org",
            "agriculture.gov.pk",
            "dawn.com",
            "tribune.com.pk",
            "agriwatch.com",
            "freshfruitportal.com"
        ]
        
        return await self.search(
            query=query,
            max_results=max_results,
            include_domains=include_domains
        )
    
    async def search_mrl_regulations(
        self,
        pesticide: str,
        fruit: str,
        country: str,
        max_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Search for Maximum Residue Limit regulations.
        
        Args:
            pesticide: Name of the pesticide
            fruit: Type of fruit
            country: Target export country
            max_results: Maximum results
            
        Returns:
            List of MRL regulation information
        """
        query = f"MRL maximum residue limit {pesticide} {fruit} {country} regulation"
        
        # Include regulatory sources
        include_domains = [
            "codexalimentarius.org",
            "ec.europa.eu",
            "fda.gov",
            "epa.gov",
            "pfa.gov.pk"
        ]
        
        return await self.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",
            include_domains=include_domains
        )
    
    async def search_disease_treatment(
        self,
        disease: str,
        crop: str,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for disease treatment information.
        
        Args:
            disease: Name of the disease
            crop: Type of crop/fruit
            max_results: Maximum results
            
        Returns:
            List of treatment information
        """
        query = f"{disease} {crop} treatment fungicide pesticide control"
        
        return await self.search(
            query=query,
            max_results=max_results,
            search_depth="advanced"
        )
