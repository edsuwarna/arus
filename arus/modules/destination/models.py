from sqlalchemy import Column, String, Integer, Boolean, DateTime, func, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid

from arus.shared.db.session import Base


class Destination(Base):
    __tablename__ = "destinations"
    __table_args__ = {"schema": "arus_config"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    host = Column(String(255), nullable=True)
    port = Column(Integer, nullable=True)
    database = Column(String(255), nullable=True)
    username = Column(String(255), nullable=True)
    password_enc = Column(Text, nullable=True)
    ssl = Column(Boolean, default=False)
    raw_schema = Column(String(255), default="staging")
    target_schema = Column(String(255), default="analytics")
    is_default = Column(Boolean, default=False)
    status = Column(String(20), default="registered")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
