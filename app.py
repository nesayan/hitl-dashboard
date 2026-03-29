import os
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from routes import routers

from database.models import Base
from database.engine import engine, AsyncSessionLocal

from services.service_user import UserService

import logging
from core.config import setup_logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    Base.metadata.create_all(bind=engine)

    async with AsyncSessionLocal() as session:
        user = await UserService.create_mock_user(session)
        logger.info(f"Mock user created with username: {user.username} and id: {user.user_id}")
    
    yield
    
app = FastAPI(lifespan=lifespan)

app.include_router(
    routers,
    prefix="/api",
)

@app.get("/health")
async def health():
    return JSONResponse(content={"status": "ok"}, status_code=200)

if __name__ == "__main__":

    port = int(os.getenv("PORT", 80))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)



