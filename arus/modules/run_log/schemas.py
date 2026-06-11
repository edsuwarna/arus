from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class RunCreate(BaseModel):
    pipeline_id: str
    trigger_type: str = "scheduled"
    config_override: Optional[dict] = None


class RunResponse(BaseModel):
    id: str
    pipeline_id: str
    pipeline_name: str = ""
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    rows_extracted: int = 0
    rows_loaded: int = 0
    error_message: Optional[str] = None
