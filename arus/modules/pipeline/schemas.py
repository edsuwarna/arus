from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TableConfig(BaseModel):
    """Per-table configuration for pipeline create/update."""
    name: str
    load_mode: str = "direct"  # direct or raw
    sync_mode: str = "incremental"  # incremental or full_refresh
    watermark_column: Optional[str] = None
    transform_config: Optional[list[dict]] = None  # array of transform step objects


class PipelineCreate(BaseModel):
    name: str
    source_id: str
    destination_id: str
    schedule: str = "*/5 * * * *"
    target_schema: str = "public"
    load_mode: str = "direct"  # pipeline-level default: direct or raw
    tables: list[TableConfig] = []
    depends_on: Optional[str] = None


class PipelineUpdate(BaseModel):
    name: Optional[str] = None
    schedule: Optional[str] = None
    status: Optional[str] = None
    target_schema: Optional[str] = None
    load_mode: Optional[str] = None
    tables: Optional[list[TableConfig]] = None
    depends_on: Optional[str] = None


class PipelineResponse(BaseModel):
    id: str
    name: str
    source_id: str
    source_name: str = ""
    status: str
    schedule: Optional[str] = None
    target_schema: str = "public"
    load_mode: str = "direct"
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
    target_schema: str = "public"
    load_mode: str = "direct"
    depends_on: Optional[str] = None
    tables: list[dict] = []
    stats: dict = {}
    created_at: Optional[datetime] = None
