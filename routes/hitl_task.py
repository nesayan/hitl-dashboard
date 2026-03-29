import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from database.engine import get_async_db
from database.models import HITLTaskStatus
from services.service_hitl_task import HITLTaskService

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hitl", tags=["HITL Tasks"])


class HITLTaskUpdateRequest(BaseModel):
    task_name: Optional[str] = None
    task_description: Optional[str] = None
    status: Optional[HITLTaskStatus] = None
    output: Optional[str] = None


class HITLTaskCreateRequest(BaseModel):
    user_run_id: str
    task_name: str
    task_args: Optional[dict] = None
    task_description: Optional[str] = None
    tool_call_object: Optional[dict] = None


class HITLTaskResponse(BaseModel):
    hitl_task_id: str
    user_run_id: str
    task_name: str
    task_args: Optional[dict] = None
    task_description: Optional[str] = None
    tool_call_object: Optional[dict] = None
    status: str
    output: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[HITLTaskResponse])
async def get_all_hitl_tasks(
    session: AsyncSession = Depends(get_async_db),
):
    """Retrieve all HITL tasks."""
    tasks = await HITLTaskService.get_all_hitltasks(session)
    return tasks


@router.post("/", status_code=201, response_model=HITLTaskResponse)
async def create_hitl_task(
    body: HITLTaskCreateRequest,
    session: AsyncSession = Depends(get_async_db),
):
    """Create a new HITL task manually.

    Generates a new UUID for the task and persists it with PENDING status.
    The user_run_id must reference an existing UserRun.
    """
    try:
        task = await HITLTaskService.create_hitltask(
            session=session,
            hitl_task_id=uuid.uuid4(),
            user_run_id=body.user_run_id,
            task_name=body.task_name,
            task_args=body.task_args,
            task_description=body.task_description,
            tool_call_object=body.tool_call_object,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format.")
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Integrity constraint violated. Check user_run_id.")

    return task


@router.get("/user", response_model=list[HITLTaskResponse])
async def get_hitl_tasks_by_user(
    user_id: str = Query(...),
    status: Optional[HITLTaskStatus] = Query(None),
    session: AsyncSession = Depends(get_async_db),
):
    """Retrieve HITL tasks for a specific user.

    Optionally filter by task status (e.g. pending, approved, rejected).
    """
    try:
        if status:
            tasks = await HITLTaskService.get_all_tasks_by_user_id_and_status(session, user_id, status)
        else:
            tasks = await HITLTaskService.get_hitltasks_by_user_id(session, user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format.")

    return tasks


@router.get("/{hitl_task_id}", response_model=HITLTaskResponse)
async def get_hitl_task(
    hitl_task_id: str,
    session: AsyncSession = Depends(get_async_db),
):
    """Retrieve a single HITL task by its ID."""
    try:
        task = await HITLTaskService.get_hitltask_by_id(session, hitl_task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format.")

    if not task:
        raise HTTPException(status_code=404, detail="HITLTask not found.")

    return task


@router.patch("/{hitl_task_id}", response_model=HITLTaskResponse)
async def update_hitl_task(
    hitl_task_id: str,
    body: HITLTaskUpdateRequest,
    session: AsyncSession = Depends(get_async_db),
):
    """Partially update a HITL task.

    Supports updating task_name, task_description, status, and output.
    Only provided fields are modified.
    """
    try:
        task = await HITLTaskService.update_hitltask(
            session=session,
            hitl_task_id=hitl_task_id,
            task_name=body.task_name,
            task_description=body.task_description,
            status=body.status,
            output=body.output,
        )
    except ValueError as e:
        raise HTTPException(status_code=404 if "not found" in str(e) else 400, detail=str(e))
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Integrity constraint violated.")

    return task


@router.delete("/{hitl_task_id}", status_code=204)
async def delete_hitl_task(
    hitl_task_id: str,
    session: AsyncSession = Depends(get_async_db),
):
    """Delete a HITL task by its ID."""
    try:
        await HITLTaskService.delete_hitltask(session, hitl_task_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
