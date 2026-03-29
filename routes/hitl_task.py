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
    tasks = await HITLTaskService.get_all_hitltasks(session)
    return tasks


@router.get("/user", response_model=list[HITLTaskResponse])
async def get_hitl_tasks_by_user(
    user_id: str = Query(...),
    status: Optional[HITLTaskStatus] = Query(None),
    session: AsyncSession = Depends(get_async_db),
):
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
    try:
        task = await HITLTaskService.update_hitltask(
            session=session,
            hitl_task_id=hitl_task_id,
            task_name=body.task_name,
            task_description=body.task_description,
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
    try:
        await HITLTaskService.delete_hitltask(session, hitl_task_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
