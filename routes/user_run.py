from typing import Optional
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from database.engine import get_async_db
from services.service_user_run import UserRunService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user-runs", tags=["User Runs"])


class UserRunCreateRequest(BaseModel):
    user_id: str
    message: Optional[str] = None


class UserRunResponse(BaseModel):
    user_run_id: str
    user_id: str
    created_at: datetime
    message: Optional[str] = None

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[UserRunResponse])
async def get_all_user_runs(
    session: AsyncSession = Depends(get_async_db),
):
    try:
        user_runs = await UserRunService.get_all_user_runs(session)
        return user_runs
    except Exception as e:
        logger.error(f"Failed to retrieve UserRuns: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error.")


@router.get("/{user_run_id}", response_model=UserRunResponse)
async def get_user_run(
    user_run_id: str,
    session: AsyncSession = Depends(get_async_db),
):
    try:
        user_run = await UserRunService.get_user_run_by_id(session, user_run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format.")
    except Exception as e:
        logger.error(f"Failed to retrieve UserRun: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error.")

    if not user_run:
        raise HTTPException(status_code=404, detail="UserRun not found.")

    return user_run


@router.post("/", status_code=201, response_model=UserRunResponse)
async def create_user_run(
    body: UserRunCreateRequest,
    session: AsyncSession = Depends(get_async_db),
):
    try:
        user_run = await UserRunService.create_user_run(session, user_id=body.user_id, message=body.message)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Integrity constraint violated.")
    except Exception as e:
        logger.error(f"Failed to create UserRun: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error.")

    return user_run


@router.delete("/{user_run_id}", status_code=204)
async def delete_user_run(
    user_run_id: str,
    session: AsyncSession = Depends(get_async_db),
):
    try:
        await UserRunService.delete_user_run(session, user_run_id)
    except ValueError as e:
        raise HTTPException(status_code=404 if "not found" in str(e) else 400, detail=str(e))
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Integrity constraint violated.")
    except Exception as e:
        logger.error(f"Failed to delete UserRun: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error.")
