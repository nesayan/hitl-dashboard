import logging
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langchain_core.messages import HumanMessage

from database.engine import AsyncSessionLocal
from database.models import HITLTaskStatus
from services.service_hitl_task import HITLTaskService
from modules.agent import get_graph

logger = logging.getLogger(__name__)


async def approve_and_resume(hitl_task_id: str, user_id: str, user_run_id: str) -> str:
    """
    Updates a HITLTask status to APPROVED and invokes the graph in resume mode.

    Returns:
        The final LLM response content.
    """
    # 1. Update the task status to APPROVED
    async with AsyncSessionLocal() as session:
        task = await HITLTaskService.update_hitltask_status(
            session=session,
            hitl_task_id=hitl_task_id,
            status=HITLTaskStatus.APPROVED,
        )
        logger.info(f"Task {task.hitl_task_id} status updated to APPROVED.")

    # 2. Invoke the graph in resume mode
    graph = await get_graph()

    state = {
        "messages": [HumanMessage(content="Resuming approved task.")],
        "user_id": user_id,
        "user_run_id": user_run_id,
        "fresh": False,
        "hitl_task_id_to_resume": hitl_task_id,
    }
    final_state = await graph.ainvoke(state)
    response = final_state["messages"][-1].content

    logger.info(f"Resume complete. Response: {response}")
    return response


async def reject_task(hitl_task_id: str) -> str:
    """
    Updates a HITLTask status to REJECTED.

    Returns:
        A confirmation message.
    """
    async with AsyncSessionLocal() as session:
        task = await HITLTaskService.update_hitltask_status(
            session=session,
            hitl_task_id=hitl_task_id,
            status=HITLTaskStatus.REJECTED,
        )
        logger.info(f"Task {task.hitl_task_id} status updated to REJECTED.")

    return f"Task {hitl_task_id} has been rejected."

if __name__ == "__main__":
    import asyncio

    from core.config import setup_logging
    setup_logging()

    async def main():
        user_id = input("Enter user_id: ").strip()
        hitl_task_id = input("Enter hitl_task_id to approve: ").strip()
        user_run_id = input("Enter user_run_id: ").strip()

        print(f"\n--- Approving task {hitl_task_id} ---")
        response = await approve_and_resume(
            hitl_task_id=hitl_task_id,
            user_id=user_id,
            user_run_id=user_run_id,
        )
        print(f"\n--- Resume response ---\n{response}\n")

    asyncio.run(main())