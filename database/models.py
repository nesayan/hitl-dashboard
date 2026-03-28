import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, UUID, String, Text, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

def generate_hitl_task_id(thread_id: uuid.UUID, tool_name: str, args: dict | None = None) -> uuid.UUID:
    key = f"{thread_id}:{tool_name}:{json.dumps(args or {}, sort_keys=True)}"
    return uuid.uuid5(uuid.NAMESPACE_DNS, key)


class HITLTaskStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"



class UserRun(Base):
    __tablename__ = 'user_run'

    thread_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    hitl_tasks = relationship('HITLTask', back_populates='user_run', cascade="all, delete-orphan")

class HITLTask(Base):
    __tablename__ = 'hitl_task'

    hitl_task_id = Column(UUID(as_uuid=True), primary_key=True)
    thread_id = Column(UUID(as_uuid=True), ForeignKey('user_run.thread_id'), nullable=False)
    task_name = Column(String(255), nullable=False)
    task_args = Column(JSON, nullable=True)
    task_description = Column(Text, nullable=True)
    status = Column(Enum(HITLTaskStatus), nullable=False, default=HITLTaskStatus.PENDING)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    output = Column(Text, nullable=True)

    user_run = relationship('UserRun', back_populates='hitl_tasks')