from fastapi import APIRouter

from routes import hitl_task
from routes import user_run
from routes import agent
from routes import admin


routers = APIRouter()
routers.include_router(hitl_task.router)
routers.include_router(user_run.router)
routers.include_router(agent.router)
routers.include_router(admin.router)

