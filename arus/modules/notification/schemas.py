from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class NotificationTargetCreate(BaseModel):
    name: str
    type: str  # telegram, discord, slack
    config: dict


class NotificationTargetUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None


class NotificationTargetResponse(BaseModel):
    id: str
    name: str
    type: str
    config: dict
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PipelineNotificationCreate(BaseModel):
    pipeline_id: str
    target_id: str
    event_types: list[str] = ["failure"]


class PipelineNotificationUpdate(BaseModel):
    event_types: Optional[list[str]] = None


class PipelineNotificationResponse(BaseModel):
    id: str
    pipeline_id: str
    target_id: str
    target_name: str = ""
    target_type: str = ""
    event_types: list[str] = []
    created_at: Optional[datetime] = None


class TestNotificationRequest(BaseModel):
    target_id: str = ""
    message: str = "🔔 Arus: This is a test notification from your Arus data pipeline platform."
    event_type: Optional[str] = None  # test, success, failure, dead_letter, schema_drift, quality_breach
