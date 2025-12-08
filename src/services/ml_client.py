import httpx
import base64
from typing import Dict, Any, Optional, List
from uuid import UUID
from src.core.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)

class MLClient:
    """Client for communicating with ML API endpoints"""
    
    def __init__(self):
        self.base_url = settings.ml_api_url
        # Use proper httpx.Timeout object with extended read timeout for ML operations
        self.timeout = httpx.Timeout(
            timeout=settings.ml_api_timeout,  # Overall timeout
            connect=10.0,  # Connection timeout
            read=settings.ml_api_timeout,  # Read timeout (most important for long ML processing)
            write=10.0,  # Write timeout
            pool=5.0  # Pool timeout
        )
        self.max_retries = getattr(settings, 'ml_api_max_retries', 3)
        
        # Log ML API configuration on initialization
        logger.info(f"ðŸ¤– ML API Client initialized with base_url: {self.base_url}")
        logger.info(f"â±ï¸  ML API timeout: {settings.ml_api_timeout}s, max retries: {self.max_retries}")
        
    async def health_check(self) -> Dict[str, Any]:
        """Check ML API health status"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/api/health")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"ML API health check failed: {str(e)}")
            raise Exception(f"ML API is not available: {str(e)}")
    
    async def _retry_request(self, request_func, *args, **kwargs):
        """Helper method to retry requests with exponential backoff"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return await request_func(*args, **kwargs)
            except (httpx.TimeoutException, httpx.ReadTimeout) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(f"Request timeout, retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Request failed after {self.max_retries} attempts due to timeout")
            except Exception as e:
                # For other exceptions, don't retry
                raise e
        
        raise Exception(f"Request timed out after {self.max_retries} retries: {str(last_exception)}")
    
    async def detect_fruits_base64(
        self,
        image_base64: str,
        user_id: str,
        image_name: str = "image.jpg",
        return_visualization: bool = True,
        confidence_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Detect and classify fruits from base64 encoded image
        
        Args:
            image_base64: Base64 encoded image data
            user_id: User UUID
            image_name: Name of the image file
            return_visualization: Whether to return annotated visualization
            confidence_threshold: Custom confidence threshold
            
        Returns:
            Detection results from ML API
        """
        async def _make_request():
            try:
                payload = {
                    "user_id": user_id,
                    "image_base64": image_base64,
                    "image_name": image_name,
                    "return_visualization": return_visualization
                }
                
                if confidence_threshold is not None:
                    payload["confidence_threshold"] = confidence_threshold
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/api/detection/fruits/base64",
                        json=payload
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    # Log visualization info
                    if result.get('success') and result.get('results'):
                        first_result = result['results'][0]
                        has_viz = first_result.get('visualization_available', False)
                        viz_base64 = first_result.get('visualization_base64')
                        logger.info(f"✅ [ML Client] ML API response received")
                        logger.info(f"✅ [ML Client] visualization_available: {has_viz}")
                        if viz_base64:
                            logger.info(f"✅ [ML Client] visualization_base64 length: {len(viz_base64)} chars")
                            logger.info(f"✅ [ML Client] visualization_base64 preview: {viz_base64[:100]}...")
                        else:
                            logger.warning(f"⚠️  [ML Client] visualization_base64 is None or empty!")
                    else:
                        logger.warning(f"⚠️  [ML Client] ML API returned unsuccessful response")
                    
                    return result           
            except httpx.HTTPStatusError as e:
                logger.error(f"ML API returned error: {e.response.status_code} - {e.response.text}")
                raise Exception(f"ML detection failed: {e.response.text}")
            except httpx.TimeoutException as e:
                logger.error(f"ML API request timed out: {str(e)}")
                raise  # Re-raise to allow retry
            except httpx.ConnectError as e:
                logger.error(f"âŒ ML API connection failed to {self.base_url}: {str(e)}")
                logger.error(f"ðŸ’¡ Check if ML_API_URL environment variable is set correctly")
                raise Exception(f"Cannot connect to ML API at {self.base_url}: {str(e)}")
            except Exception as e:
                logger.error(f"ML API request failed: {str(e)}")
                logger.error(f"ML API URL being used: {self.base_url}")
                raise Exception(f"Failed to communicate with ML API: {str(e)}")
        
        return await self._retry_request(_make_request)
    
    async def detect_fruits_batch(
        self,
        images: List[Dict[str, str]],
        user_id: str,
        return_visualization: bool = False,
        confidence_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Batch detect and classify fruits from multiple base64 images
        
        Args:
            images: List of dicts with 'id' and 'data' (base64) keys
            user_id: User UUID
            return_visualization: Whether to return annotated visualizations
            confidence_threshold: Custom confidence threshold
            
        Returns:
            Batch detection results from ML API
        """
        try:
            payload = {
                "user_id": user_id,
                "images": images,
                "options": {
                    "return_visualization": return_visualization,
                    "save_to_database": True
                }
            }
            
            if confidence_threshold is not None:
                payload["options"]["confidence_threshold"] = confidence_threshold
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/detection/fruits/batch",
                    json=payload
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"ML API batch detection error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"ML batch detection failed: {e.response.text}")
        except Exception as e:
            logger.error(f"ML API batch request failed: {str(e)}")
            raise Exception(f"Failed to communicate with ML API: {str(e)}")
    
    async def detect_disease_base64(
        self,
        image_base64: str,
        user_id: str,
        image_name: str = "image.jpg",
        fruit_type: Optional[str] = None,
        confidence_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Detect diseases from base64 encoded image
        
        Args:
            image_base64: Base64 encoded image data
            user_id: User UUID
            image_name: Name of the image file
            fruit_type: Optional fruit type hint (mango, orange, grapefruit)
            confidence_threshold: Disease confidence threshold (default: 0.7)
            
        Returns:
            Disease detection results from ML API
        """
        try:
            payload = {
                "user_id": user_id,
                "image_base64": image_base64,
                "image_name": image_name
            }
            
            params = {}
            if fruit_type:
                params["fruit_type"] = fruit_type
            if confidence_threshold is not None:
                params["confidence_threshold"] = confidence_threshold
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/disease/detect/base64",
                    json=payload,
                    params=params
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"ML API disease detection error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"ML disease detection failed: {e.response.text}")
        except Exception as e:
            logger.error(f"ML API disease request failed: {str(e)}")
            raise Exception(f"Failed to communicate with ML API: {str(e)}")
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded ML models"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/api/models/info")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get ML model info: {str(e)}")
            raise Exception(f"Failed to get ML model information: {str(e)}")

# Create singleton instance
ml_client = MLClient()
