from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DestinationCreate(BaseModel):
    name: str
    type: str = "postgresql"
    host: str = "localhost"
    port: int = 5432
    database: str = "arus_warehouse"
    username: str = "arus"
    password: str = "arus_secret"
    raw_schema: str = "staging"
    analytics_schema: str = "analytics"
    is_default: bool = False


class DestinationResponse(BaseModel):
    id: str
    name: str
    type: str
    host: str
    port: int
    database: str
    status: str
    raw_schema: str
    analytics_schema: str
    is_default: bool
    created_at: Optional[datetime] = None
