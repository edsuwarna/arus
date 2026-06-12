from sqlalchemy import Column, String, Boolean, DateTime, func, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid

from arus.shared.db.session import Base


class NotificationTarget(Base):
    __tablename__ = "notification_targets"
    __table_args__ = {"schema": "arus_config"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(String(20), nullable=False)  # telegram, discord, slack
    config = Column(Text, nullable=False)  # JSON string
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PipelineNotification(Base):
    __tablename__ = "pipeline_notifications"
    __table_args__ = {"schema": "arus_config"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id = Column(UUID, ForeignKey("arus_config.pipelines.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(UUID, ForeignKey("arus_config.notification_targets.id", ondelete="CASCADE"), nullable=False)
    event_types = Column(ARRAY(String), nullable=False, default=list)  # ['failure', 'success', 'dead_letter', 'schema_drift', 'quality_breach']
    created_at = Column(DateTime(timezone=True), server_default=func.now())
