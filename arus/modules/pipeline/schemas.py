from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PipelineCreate(BaseModel):
    name: str
    source_id: str
    destination_id: str
    schedule: str = "*/5 * * * *"
    tables: list[str] = []
    depends_on: Optional[str] = None


class PipelineUpdate(BaseModel):
    name: Optional[str] = None
    schedule: Optional[str] = None
    status: Optional[str] = None
    tables: Optional[list[str]] = None
    depends_on: Optional[str] = None


class PipelineResponse(BaseModel):
    id: str
    name: str
    source_id: str
    source_name: str = ""
    status: str
    schedule: Optional[str] = None
    depends_on: Optional[str] = None
    enabled_table_count: int = 0
    last_run: Optional[dict] = None
    total_rows_synced: int = 0
    error_count_7d: int = 0
    created_at: Optional[datetime] = None


class PipelineDetailResponse(BaseModel):
    id: str
    name: str
    source: dict
    destination: dict
    status: str
    schedule: Optional[str] = None
    depends_on: Optional[str] = None
    tables: list[dict] = []
    stats: dict = {}
    created_at: Optional[datetime] = None
