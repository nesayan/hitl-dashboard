import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, UUID, String, Text, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

def generate_hitl_task_id(user_id: uuid.UUID, tool_name: str, args: dict | None = None) -> uuid.UUID:
    key = f"{user_id}:{tool_name}:{json.dumps(args or {}, sort_keys=True)}"
    return uuid.uuid5(uuid.NAMESPACE_DNS, key)


class HITLTaskStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class User(Base):
    __tablename__ = 'user'

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    user_runs = relationship('UserRun', back_populates='user', cascade='all, delete-orphan')

class UserRun(Base):
    __tablename__ = 'user_run'
    user_run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.user_id'), nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    message = Column(Text, nullable=True)

    user = relationship('User', back_populates='user_runs')
    hitl_tasks = relationship('HITLTask', back_populates='user_run', cascade="all, delete-orphan")

class HITLTask(Base):
    __tablename__ = 'hitl_task'

    hitl_task_id = Column(UUID(as_uuid=True), primary_key=True)
    user_run_id = Column(UUID(as_uuid=True), ForeignKey('user_run.user_run_id'), nullable=False)
    task_name = Column(String(255), nullable=False)
    task_args = Column(JSON, nullable=True)
    task_description = Column(Text, nullable=True)
    tool_call_object = Column(JSON, nullable=True)
    status = Column(Enum(HITLTaskStatus), nullable=False, default=HITLTaskStatus.PENDING)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    output = Column(Text, nullable=True)

    user_run = relationship('UserRun', back_populates='hitl_tasks')