import httpx
import base64
from typing import Dict, Any, Optional, List
from uuid import UUID
from src.core.config import settings
import logging

logger = logging.getLogger(__name__)

class MLClient:
    """Client for communicating with ML API endpoints"""
    
    def __init__(self):
        self.base_url = settings.ml_api_url
        self.timeout = settings.ml_api_timeout
        
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
    
    async def detect_fruits_base64(
        self,
        image_base64: str,
        user_id: str,
        image_name: str = "image.jpg",
        return_visualization: bool = False,
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
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"ML API returned error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"ML detection failed: {e.response.text}")
        except Exception as e:
            logger.error(f"ML API request failed: {str(e)}")
            raise Exception(f"Failed to communicate with ML API: {str(e)}")
    
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
