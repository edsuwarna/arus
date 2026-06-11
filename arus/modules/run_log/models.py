from sqlalchemy import Column, String, Integer, DateTime, func, Text, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid

from arus.shared.db.session import Base


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = {"schema": "arus_run_logs"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id = Column(UUID, nullable=False)
    status = Column(String(20), default="running")
    started_at = Column(DateTime(timezone=True), default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    trigger_type = Column(String(20), default="scheduled")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RunTableStat(Base):
    __tablename__ = "run_table_stats"
    __table_args__ = {"schema": "arus_run_logs"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID, ForeignKey("arus_run_logs.runs.id", ondelete="CASCADE"), nullable=False)
    table_name = Column(String(255), nullable=False)
    rows_extracted = Column(Integer, default=0)
    rows_loaded_raw = Column(Integer, default=0)
    rows_loaded_analytics = Column(Integer, default=0)
    rows_failed = Column(Integer, default=0)
    watermark_before = Column(Text, nullable=True)
    watermark_after = Column(Text, nullable=True)
    duration_ms = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)


class RunLog(Base):
    __tablename__ = "run_logs"
    __table_args__ = {"schema": "arus_run_logs"}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(UUID, ForeignKey("arus_run_logs.runs.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    level = Column(String(10), default="INFO")
    message = Column(Text, nullable=False)
