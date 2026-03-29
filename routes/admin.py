from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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


@router.post("/approve", response_model=TaskActionResponse)
async def approve_task(body: ApproveTaskRequest):
    """
    Approve a PENDING HITL task and resume graph execution.

    Updates the task status to APPROVED, then invokes the graph in resume mode
    to execute the originally requested tool and return the result.
    """
    # 1. Update status to APPROVED
    try:
        async with AsyncSessionLocal() as session:
            task = await HITLTaskService.update_hitltask_status(
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

    # 2. Invoke graph in resume mode
    try:
        graph = await get_graph()

        state = {
            "messages": [HumanMessage(content="Resuming approved task.")],
            "user_id": body.user_id,
            "user_run_id": body.user_run_id,
            "fresh": False,
            "hitl_task_id_to_resume": body.hitl_task_id,
        }
        final_state = await graph.ainvoke(state)
        response_content = final_state["messages"][-1].content
    except Exception as e:
        logger.error(f"Resume execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Resume execution failed.")

    return TaskActionResponse(message=response_content)


@router.post("/reject", response_model=TaskActionResponse)
async def reject_task(body: RejectTaskRequest):
    """
    Reject a PENDING HITL task.

    Updates the task status to REJECTED. No graph execution occurs.
    """
    try:
        async with AsyncSessionLocal() as session:
            task = await HITLTaskService.update_hitltask_status(
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
