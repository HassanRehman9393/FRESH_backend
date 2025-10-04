from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

class ImageCreateResponse(BaseModel):
    id: UUID
    user_id: UUID
    file_path: str
    file_name: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

class ImageGetResponse(BaseModel):
    id: UUID
    user_id: UUID
    file_path: str
    file_name: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
