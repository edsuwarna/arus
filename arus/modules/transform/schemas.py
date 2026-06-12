from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TransformScriptCreate(BaseModel):
    name: str
    description: Optional[str] = None
    content: str  # Python script content


class TransformScriptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None


class TransformScriptResponse(BaseModel):
    id: str
    pipeline_id: str
    name: str
    description: Optional[str] = None
    content: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
