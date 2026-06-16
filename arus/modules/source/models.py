from sqlalchemy import Column, String, Integer, Boolean, DateTime, func, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid

from arus.shared.db.session import Base


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = {"schema": "arus_config"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    database = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)
    password_enc = Column(Text, nullable=False)
    ssl = Column(Boolean, default=False)
    uri = Column(Text, nullable=True)  # MongoDB connection string
    auth_source = Column(String(100), nullable=True)  # MongoDB auth database
    sync_method = Column(String(20), default="auto")
    table_include = Column(ARRAY(String), default=[])
    table_exclude = Column(ARRAY(String), default=[])
    schema_include = Column(ARRAY(String), default=[])
    table_count = Column(Integer, default=0)
    enabled_table_count = Column(Integer, default=0)
    status = Column(String(20), default="registered")
    last_tested = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
