from typing import Optional
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from database.engine import get_async_db
from services.service_user import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


class UserCreateRequest(BaseModel):
    username: str


class UserUpdateRequest(BaseModel):
    username: Optional[str] = None


class UserResponse(BaseModel):
    user_id: str
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[UserResponse])
async def get_all_users(
    session: AsyncSession = Depends(get_async_db),
):
    """Retrieve all users."""
    try:
        users = await UserService.get_all_users(session)
        return users
    except Exception as e:
        logger.error(f"Failed to retrieve Users: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error.")


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    session: AsyncSession = Depends(get_async_db),
):
    """Retrieve a single user by their ID."""
    try:
        user = await UserService.get_user_by_id(session, user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format.")
    except Exception as e:
        logger.error(f"Failed to retrieve User: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error.")

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    return user


@router.post("/", status_code=201, response_model=UserResponse)
async def create_user(
    body: UserCreateRequest,
    session: AsyncSession = Depends(get_async_db),
):
    """Create a new user.

    The username must be unique. Returns 409 if it already exists.
    """
    try:
        user = await UserService.create_user(session, username=body.username)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Username already exists.")
    except Exception as e:
        logger.error(f"Failed to create User: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error.")

    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: UserUpdateRequest,
    session: AsyncSession = Depends(get_async_db),
):
    """Partially update a user.

    Currently supports updating the username. Returns 409 if the new username already exists.
    """
    try:
        user = await UserService.update_user(session, user_id=user_id, username=body.username)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Username already exists.")
    except Exception as e:
        logger.error(f"Failed to update User: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error.")

    return user


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    session: AsyncSession = Depends(get_async_db),
):
    """Delete a user by their ID.

    Returns 409 if the user has existing runs due to FK constraints.
    """
    try:
        await UserService.delete_user(session, user_id=user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found.")
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Cannot delete user with existing runs.")
    except Exception as e:
        logger.error(f"Failed to delete User: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error.")
