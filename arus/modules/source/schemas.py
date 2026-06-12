from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SourceCreate(BaseModel):
    name: str
    type: str
    host: str = "localhost"
    port: int = 5432
    database: str = ""
    username: str = ""
    password: str = ""
    ssl: bool = False
    uri: Optional[str] = None  # MongoDB connection string
    auth_source: Optional[str] = "admin"  # MongoDB auth database
    sync_method: str = "auto"
    table_include: list[str] = []
    table_exclude: list[str] = []
    schema_include: list[str] = []


class SourceUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssl: Optional[bool] = None
    uri: Optional[str] = None
    auth_source: Optional[str] = None
    sync_method: Optional[str] = None
    table_include: Optional[list[str]] = None
    table_exclude: Optional[list[str]] = None
    schema_include: Optional[list[str]] = None


class SourceResponse(BaseModel):
    id: str
    name: str
    type: str
    host: str
    port: int
    database: str
    status: str
    uri: Optional[str] = None
    auth_source: Optional[str] = None
    table_count: int = 0
    enabled_table_count: int = 0
    last_tested: Optional[datetime] = None
    created_at: Optional[datetime] = None


class DiscoveredTable(BaseModel):
    name: str
    schema: str = "public"
    row_count_estimate: int = 0
    columns: list[dict] = []
    detected_sync: str = "incremental"
    watermark_column: Optional[str] = None
    enabled: bool = True


class TablesUpdate(BaseModel):
    tables: list[dict]
