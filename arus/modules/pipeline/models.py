from sqlalchemy import Column, String, Integer, Boolean, DateTime, func, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid

from arus.shared.db.session import Base


class Pipeline(Base):
    __tablename__ = "pipelines"
    __table_args__ = {"schema": "arus_config"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    source_id = Column(UUID, ForeignKey("arus_config.sources.id", ondelete="CASCADE"), nullable=False)
    destination_id = Column(UUID, ForeignKey("arus_config.destinations.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String(20), default="active")
    schedule = Column(String(100), nullable=True)
    max_retries = Column(Integer, default=3)
    timeout_seconds = Column(Integer, default=300)
    depends_on = Column(UUID, ForeignKey("arus_config.pipelines.id", ondelete="SET NULL"), nullable=True)
    target_schema = Column(String(255), default="public")
    load_mode = Column(String(20), default="direct")  # pipeline-level default: direct or raw
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PipelineTable(Base):
    __tablename__ = "pipeline_tables"
    __table_args__ = {"schema": "arus_config"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id = Column(UUID, ForeignKey("arus_config.pipelines.id", ondelete="CASCADE"), nullable=False)
    source_table = Column(String(255), nullable=False)
    source_schema = Column(String(255), default="public")
    target_schema = Column(String(255), nullable=True)
    sync_mode = Column(String(20), default="incremental")
    load_mode = Column(String(20), default="direct")  # direct or raw
    watermark_column = Column(String(255), nullable=True)
    enabled = Column(Boolean, default=True)


class Watermark(Base):
    __tablename__ = "watermarks"
    __table_args__ = {"schema": "arus_state"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id = Column(UUID, nullable=False)
    source_table = Column(String(255), nullable=False)
    watermark_col = Column(String(255), nullable=True)
    watermark_value = Column(Text, nullable=True)
    row_count = Column(Integer, default=0)
    last_run_id = Column(UUID, nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
