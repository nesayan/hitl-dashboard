import json
import sys
import os
from typing import TypedDict
import uuid
from typing_extensions import Annotated

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.exc import IntegrityError
from database.models import generate_hitl_task_id, HITLTaskStatus

from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.prebuilt import ToolNode, tools_condition
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage, ToolMessage

from core.config import settings

from database.engine import AsyncSessionLocal
from services.service_hitl_task import HITLTaskService
from services.service_user_run import UserRunService
from services.service_user import UserService

from modules.tools import TOOLS

import logging

logger = logging.getLogger(__name__)

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: uuid.UUID
    user_run_id: uuid.UUID

_graph = None
_checkpointer = None

async def get_graph():
    global _graph
    if _graph is not None:
        return _graph
    _graph = await build_graph()
    return _graph

async def get_checkpointer(database_name: str = "checkpointer.db"):
    global _checkpointer
    if _checkpointer is None:
        _checkpointer_conn = await aiosqlite.connect(database_name)
        _checkpointer = AsyncSqliteSaver(_checkpointer_conn)
        await _checkpointer.setup()
    return _checkpointer
    
   
async def close_checkpointer():
    global _checkpointer
    if _checkpointer is not None:
        await _checkpointer.conn.close()
        _checkpointer = None


async def build_graph():

    workflow = StateGraph(State)

    tool_node = ToolNode(TOOLS)

    async def llm_node(state: State):
        system_prompt = SystemMessage(content='''
            You are a helpful assistant to help solve user's queries.
            Instructions you MUST follow:
            1. You should always use tools for the operations whenever possible.
            2. General questions should be answered directly without using tools.
            3. If a tool returns output with some approval status, you should respond only on the current approval status.
        ''')

        llm = AzureChatOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            temperature=0,
            streaming=True
        ).bind_tools(TOOLS)

        llm_response = await llm.ainvoke([system_prompt] + state["messages"])
        logger.info(f"[LLM Node] LLM Response: {llm_response.content}")

        return {"messages": [llm_response]}
    
    def tools_router(state: State):
        last_message = state["messages"][-1]

        # if no tool calls, go to END
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return "__end__"

        tool_call_name = last_message.tool_calls[0]["name"]
        tool_def = next((t for t in TOOLS if t.name == tool_call_name), None)
        requires_approval = tool_def and tool_def.metadata.get("requires_approval")

        if requires_approval:
            return "entry_task_in_database_node"
        return "tool_node"
        
    async def entry_task_in_database_node(state: State):
        last_message = state["messages"][-1]
        response_messages = []

        for tool_call in last_message.tool_calls:
            task_name = tool_call["name"]
            task_args = tool_call["args"]

            # check if a task exist with status pending
            async with AsyncSessionLocal() as session:
                existing_task = await HITLTaskService.get_hitltask_by_user_id_task_name_args_and_status(
                    session=session,
                    user_id=str(state["user_id"]),
                    task_name=task_name,
                    task_args=task_args,
                    status=HITLTaskStatus.PENDING
                )
                if existing_task:
                    logger.info(f"[Database Node] Task with status PENDING already exists: {existing_task.hitl_task_id}")
                    response_messages.append(ToolMessage(
                        content="A similar task already exists and is pending approval. Please wait for it to be reviewed by the admin.",
                        tool_call_id=tool_call["id"],
                    ))
                    continue

            # create HITL task in database with status PENDING if not exist
            async with AsyncSessionLocal() as session:
                hitl_task = await HITLTaskService.create_hitltask(
                    session=session,
                    hitl_task_id=generate_hitl_task_id(state["user_id"], task_name, task_args),
                    user_run_id=str(state["user_run_id"]),
                    task_name=task_name,
                    task_args=task_args,
                    task_description=f"Tool call for {task_name} with args {task_args} requires approval."
                )
                logger.info(f"[Database Node] Created HITLTask with ID: {hitl_task.hitl_task_id}")
                response_messages.append(ToolMessage(
                    content="Your request has been submitted for review. Please wait for the admin to approve it.",
                    tool_call_id=tool_call["id"],
                ))

        return {"messages": response_messages}
                    

    workflow.add_node("llm_node", llm_node)
    workflow.add_node("tool_node", tool_node)
    workflow.add_node("entry_task_in_database_node", entry_task_in_database_node)

    workflow.add_edge(START, "llm_node")
    workflow.add_conditional_edges(
        "llm_node",
        tools_router,
        {
            "__end__": END,
            "tool_node": "tool_node",
            "entry_task_in_database_node": "entry_task_in_database_node"
        }
    )
    workflow.add_edge("tool_node", "llm_node")
    workflow.add_edge("entry_task_in_database_node", "llm_node")

    checkpointer = await get_checkpointer()
    graph = workflow.compile(checkpointer=checkpointer)

    # save png mermaid
    with open("graph_output.png", "wb") as f:
        f.write(graph.get_graph().draw_mermaid_png())

    return graph

if __name__ == "__main__":
    
    import asyncio
    from database.models import Base
    from database.engine import engine

    async def main():
        try:
            # Create tables
            Base.metadata.create_all(bind=engine)

            graph = await get_graph()

            # 1. Create a mock user
            async with AsyncSessionLocal() as session:
                user = await UserService.create_mock_user(session)
                user_id = str(user.user_id)
                logger.info(f"Mock user: {user.username} ({user_id})")

            # 2. Create a UserRun (represents the message they send)
            message = "Use tools and tell What is 3 - 2?"
            async with AsyncSessionLocal() as session:
                user_run = await UserRunService.create_user_run(session=session, user_id=user_id, message=message)
                user_run_id = str(user_run.user_run_id)
                logger.info(f"Created UserRun: {user_run_id}")

            # 3. Invoke graph with the user_id
            state = {
                "messages": [HumanMessage(content=message)],
                "user_id": user_id,
                "user_run_id": user_run_id,
            }
            config = {"configurable": {"thread_id": user_id}}

            final_state = await graph.ainvoke(state, config)
            print(final_state["messages"][-1].content)
        finally:
            await close_checkpointer()

    asyncio.run(main())