from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import asyncio

from database.engine import AsyncSessionLocal
from services.service_hitl_task import HITLTaskService
from database.models import HITLTaskStatus
from modules.agent import get_graph

from langchain_core.messages import HumanMessage

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


class ApproveTaskRequest(BaseModel):
    """Request body for approving a HITL task."""
    hitl_task_id: str
    user_id: str
    user_run_id: str


class RejectTaskRequest(BaseModel):
    """Request body for rejecting a HITL task."""
    hitl_task_id: str


class TaskActionResponse(BaseModel):
    """Response body for approve/reject actions."""
    message: str


async def _run_graph_in_background(hitl_task_id: str, user_id: str, user_run_id: str):
    """Run the graph resume in the background. Updates task to COMPLETED or logs errors."""
    try:
        graph = await get_graph()

        state = {
            "messages": [HumanMessage(content="Resuming approved task.")],
            "user_id": user_id,
            "user_run_id": user_run_id,
            "fresh": False,
            "hitl_task_id_to_resume": hitl_task_id,
        }
        final_state = await graph.ainvoke(state)
        response_content = final_state["messages"][-1].content
        logger.info(f"Graph resume completed for task {hitl_task_id}: {response_content[:100]}")
    except Exception as e:
        logger.error(f"Background graph execution failed for task {hitl_task_id}: {str(e)}")


@router.post("/approve", response_model=TaskActionResponse)
async def approve_task(body: ApproveTaskRequest):
    """
    Approve a PENDING HITL task and resume graph execution in the background.

    Updates the task status to APPROVED, then kicks off graph execution
    without blocking the response.
    """
    # 1. Update status to APPROVED
    try:
        async with AsyncSessionLocal() as session:
            task = await HITLTaskService.update_hitltask(
                session=session,
                hitl_task_id=body.hitl_task_id,
                status=HITLTaskStatus.APPROVED,
            )
            logger.info(f"Task {task.hitl_task_id} status updated to APPROVED.")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to approve task: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to approve task.")

    # 2. Fire off graph resume in background — don't block the response
    asyncio.create_task(_run_graph_in_background(body.hitl_task_id, body.user_id, body.user_run_id))

    return TaskActionResponse(message=f"Task {body.hitl_task_id} approved. Graph execution started.")


@router.post("/reject", response_model=TaskActionResponse)
async def reject_task(body: RejectTaskRequest):
    """
    Reject a PENDING HITL task.

    Updates the task status to REJECTED. No graph execution occurs.
    """
    try:
        async with AsyncSessionLocal() as session:
            task = await HITLTaskService.update_hitltask(
                session=session,
                hitl_task_id=body.hitl_task_id,
                status=HITLTaskStatus.REJECTED,
            )
            logger.info(f"Task {task.hitl_task_id} status updated to REJECTED.")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to reject task: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to reject task.")

    return TaskActionResponse(message=f"Task {body.hitl_task_id} has been rejected.")
