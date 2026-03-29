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
    """Graph state shared across all nodes.

    Attributes:
        messages: Conversation history. Uses LangGraph's add_messages reducer to append.
        user_id: The authenticated user's UUID.
        user_run_id: The UserRun UUID for this interaction (used to link HITL tasks).
        fresh: If True, routes to llm_node (new query). If False, routes to resume_task_node.
        hitl_task_id_to_resume: The UUID of an approved HITL task to resume. None for fresh queries.
    """
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: uuid.UUID
    user_run_id: uuid.UUID
    fresh: bool
    hitl_task_id_to_resume: uuid.UUID | None

_graph = None

async def get_graph():
    global _graph
    if _graph is not None:
        return _graph
    _graph = await build_graph()
    return _graph


async def build_graph():
    """
    Builds and compiles the LangGraph workflow.

    Graph Flow:
        Fresh Query (fresh=True):
            START → llm_node → tools_router
                → tool_node (no approval needed) → llm_node → ...
                → entry_task_in_database_node (approval needed) → llm_node → END
                → END (no tool calls)

        Resume Task (fresh=False):
            START → resume_task_node → resume_task_router
                → tool_node (if approved, executes tool) → llm_node → tools_router → END
                → END (if not approved)

    Nodes:
        llm_node: Sends messages to Azure OpenAI LLM with tool bindings.
        tool_node: Executes the tool call (LangGraph prebuilt ToolNode).
        entry_task_in_database_node: Creates a PENDING HITL task in DB for admin approval.
        resume_task_node: Fetches an approved HITL task and reconstructs its tool call.

    Routers:
        check_fresh_or_resume_task: Routes based on state["fresh"].
        tools_router: Routes LLM output to tool_node, entry_task_in_database_node, or END.
            - Skips approval gate during resume (tool was already approved).
            - Saves tool output to HITL task on resume completion.
        resume_task_router: Routes to tool_node if task is approved, else END.
    """

    workflow = StateGraph(State)

    tool_node = ToolNode(TOOLS)

    async def check_fresh_or_resume_task(state: State):
        """Entry router: directs to llm_node for fresh queries, resume_task_node for approved tasks."""
        if state.get("fresh"):
            logger.info("[Graph] Starting fresh execution.")
            return "llm_node"
        
        return "resume_task_node"

    async def llm_node(state: State):
        """Invokes Azure OpenAI LLM with the current messages and tool bindings."""
        system_prompt = SystemMessage(content='''
            You are a helpful assistant to help solve user's queries.
            Instructions you MUST follow:
            1. You should always use tools for the operations whenever possible.
            2. General questions should be answered directly without using tools.
            3. If a tool isnt approved, you must not answer the query even if you know the answer from your training knowledge..
        '''
        )
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
    
    async def tools_router(state: State):
        """Routes LLM output based on tool calls and approval requirements.

        - No tool calls → saves output if resuming, then END.
        - Tool needs approval (and not resuming) → entry_task_in_database_node.
        - Otherwise → tool_node (execute directly).
        """
        last_message = state["messages"][-1]

        # if no tool calls, it's the final answer if resuming. Save the answer and go to __end__
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            # Save output to HITL task if resuming
            hitl_task_id = state.get("hitl_task_id_to_resume")
            if hitl_task_id:
                async with AsyncSessionLocal() as session:
                    await HITLTaskService.update_hitltask(
                        session=session,
                        hitl_task_id=str(hitl_task_id),
                        output=last_message.content,
                        status=HITLTaskStatus.COMPLETED,
                    )
                    logger.info(f"[Tools Router] Saved output to HITL task {hitl_task_id}")
            return "__end__"

        tool_call_name = last_message.tool_calls[0]["name"]
        tool_def = next((t for t in TOOLS if t.name == tool_call_name), None)
        requires_approval = tool_def and tool_def.metadata.get("requires_approval")

        logger.info(f"[Tools Router] Tool call detected: {tool_call_name}, requires approval: {requires_approval}")

        if requires_approval and not state.get("hitl_task_id_to_resume"):
            return "entry_task_in_database_node"
        return "tool_node"
        
    async def entry_task_in_database_node(state: State):
        """Creates a PENDING HITL task in the database for admin approval.

        If a PENDING task with the same user_id, task_name, and task_args already exists,
        returns a message indicating it's already pending instead of creating a duplicate.
        Stores the full tool_call_object for later replay on approval.
        """
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
                    hitl_task_id=uuid.uuid4(),
                    user_run_id=str(state["user_run_id"]),
                    task_name=task_name,
                    task_args=task_args,
                    tool_call_object= tool_call,
                    task_description=f"Tool call for {task_name} with args {task_args} requires approval."
                )
                logger.info(f"[Database Node] Created HITLTask with ID: {hitl_task.hitl_task_id}")
                response_messages.append(ToolMessage(
                    content="You must say a request has been submitted for review. Please wait for the admin to approve it.",
                    tool_call_id=tool_call["id"],
                ))

        return {"messages": response_messages}
    
    # Fetches an approved HITL task and reconstructs its tool call as an AIMessage.
    async def resume_task_node(state: State):
        """Resumes an approved HITL task by reconstructing the original tool call.

        Reads the stored tool_call_object from the DB and returns an AIMessage
        with tool_calls, which the resume_task_router then sends to tool_node.
        If the task is not APPROVED, returns a status message and routes to END.
        """
        hitl_task_to_resume = state.get("hitl_task_id_to_resume")

        async with AsyncSessionLocal() as session:
            task = await HITLTaskService.get_hitltask_by_id(session, hitl_task_to_resume)

            if not task:
                logger.error(f"[Resume Node] No task found with ID: {hitl_task_to_resume}")
                return {
                    "messages": [AIMessage(content="Error: The task you are trying to resume does not exist.")]
                }

            if task.status == HITLTaskStatus.APPROVED:
                tool_call = task.tool_call_object
                logger.info(f"[Resume Node] Task {task.hitl_task_id} is approved. Executing tool.")
                return {
                    "messages": [AIMessage(content="", tool_calls=[tool_call])]
                }
            else:
                logger.info(f"[Resume Node] Task {task.hitl_task_id} status: {task.status}")
                return {
                    "messages": [AIMessage(content=f"Task status: {task.status.value}. Cannot execute.")]
                }

    def resume_task_router(state: State):
        """Routes resume output: to tool_node if tool calls exist, else END."""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tool_node"
        return "__end__"



                    
    workflow.add_node("llm_node", llm_node)
    workflow.add_node("tool_node", tool_node)
    workflow.add_node("entry_task_in_database_node", entry_task_in_database_node)
    workflow.add_node("resume_task_node", resume_task_node)

    # Workflow start
    workflow.add_conditional_edges(
        START,
        check_fresh_or_resume_task,
        {
            "llm_node": "llm_node",
            "resume_task_node": "resume_task_node"
        }
    )

    # Logic for fresh execution workflow
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

    # Logic for resuming: approved → tool_node → llm_node, not approved → END
    workflow.add_conditional_edges(
        "resume_task_node",
        resume_task_router,
        {
            "tool_node": "tool_node",
            "__end__": END,
        }
    )

    graph = workflow.compile()

    # save png mermaid
    with open("graph_output.png", "wb") as f:
        f.write(graph.get_graph().draw_mermaid_png())

    return graph

if __name__ == "__main__":
    
    import asyncio
    from database.models import Base
    from database.engine import engine

    from core.config import setup_logging
    setup_logging()

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
            message = "Tell me about recent Apple product launches."
            async with AsyncSessionLocal() as session:
                user_run = await UserRunService.create_user_run(session=session, user_id=user_id, message=message)
                user_run_id = str(user_run.user_run_id)
                logger.info(f"Created UserRun: {user_run_id}")

            # 3. Invoke graph with user_run_id as thread_id for isolated history
            state = {
                "messages": [HumanMessage(content=message)],
                "user_id": user_id,
                "user_run_id": user_run_id,
                "fresh": True,
                "hitl_task_id_to_resume": None,

            }
            final_state = await graph.ainvoke(state)
            print(final_state["messages"][-1].content)
        finally:
            pass

    asyncio.run(main())