import os
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from routes import routers

from database.models import Base
from database.engine import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield
    from modules.agent import close_checkpointer
    await close_checkpointer()
    
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



