from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import get_async_db, AsyncSessionLocal
from services.service_user_run import UserRunService
from modules.agent import get_graph

from langchain_core.messages import HumanMessage

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["Agent"])


class AgentQueryRequest(BaseModel):
    user_id: str
    message: str


class AgentQueryResponse(BaseModel):
    user_run_id: str
    response: str


@router.post("/query", response_model=AgentQueryResponse)
async def query_graph(
    body: AgentQueryRequest,
    session: AsyncSession = Depends(get_async_db),
):
    # 1. Create a UserRun for this message
    try:
        user_run = await UserRunService.create_user_run(
            session=session,
            user_id=body.user_id,
            message=body.message,
        )
        user_run_id = str(user_run.user_run_id)
    except Exception as e:
        logger.error(f"Failed to create UserRun: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to create UserRun: {str(e)}")

    # 2. Invoke the graph
    try:
        graph = await get_graph()

        state = {
            "messages": [HumanMessage(content=body.message)],
            "user_id": body.user_id,
            "user_run_id": user_run_id,
            "fresh": True,
            "hitl_task_id_to_resume": None,
        }
        final_state = await graph.ainvoke(state)
        response_content = final_state["messages"][-1].content
    except Exception as e:
        logger.error(f"Graph execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Graph execution failed.")

    return AgentQueryResponse(
        user_run_id=user_run_id,
        response=response_content,
    )
