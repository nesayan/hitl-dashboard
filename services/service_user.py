from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from database.models import User

import logging

logger = logging.getLogger(__name__)


class UserService:

    @classmethod
    async def create_user(
        cls,
        session: AsyncSession,
        username: str,
    ) -> User:
        user = User(username=username)

        session.add(user)
        try:
            await session.commit()
            await session.refresh(user)
        except IntegrityError as e:
            await session.rollback()
            logger.error(f"Failed to create User: {str(e)}")
            raise e
        except Exception as e:
            await session.rollback()
            logger.error(f"Unexpected error occurred while creating User: {str(e)}")
            raise e

        return user

    @classmethod
    async def get_user_by_id(
        cls,
        session: AsyncSession,
        user_id: str,
    ) -> Optional[User]:
        result = await session.get(User, UUID(user_id))
        return result

    @classmethod
    async def get_user_by_username(
        cls,
        session: AsyncSession,
        username: str,
    ) -> Optional[User]:
        result = await session.execute(
            select(User).where(User.username == username)
        )
        return result.scalars().first()

    @classmethod
    async def get_all_users(
        cls,
        session: AsyncSession,
    ) -> list[User]:
        result = await session.execute(select(User))
        return result.scalars().all()

    @classmethod
    async def update_user(
        cls,
        session: AsyncSession,
        user_id: str,
        username: Optional[str] = None,
    ) -> User:
        user = await session.get(User, UUID(user_id))
        if not user:
            raise ValueError(f"User with id {user_id} not found.")

        if username is not None:
            user.username = username

        try:
            await session.commit()
            await session.refresh(user)
        except IntegrityError as e:
            await session.rollback()
            logger.error(f"Failed to update User: {str(e)}")
            raise e
        except Exception as e:
            await session.rollback()
            logger.error(f"Unexpected error occurred while updating User: {str(e)}")
            raise e

        return user

    @classmethod
    async def delete_user(
        cls,
        session: AsyncSession,
        user_id: str,
    ) -> None:
        user = await session.get(User, UUID(user_id))
        if not user:
            raise ValueError(f"User with id {user_id} not found.")

        try:
            await session.delete(user)
            await session.commit()
        except IntegrityError as e:
            await session.rollback()
            logger.error(f"Failed to delete User: {str(e)}")
            raise e
        except Exception as e:
            await session.rollback()
            logger.error(f"Unexpected error occurred while deleting User: {str(e)}")
            raise e

    # Additional methods for user-related operations can be added here

    @classmethod
    async def create_mock_user(cls, session: AsyncSession) -> User:
        mock_username = "mock"
        existing_user = await cls.get_user_by_username(session, mock_username)
        if existing_user:
            return existing_user

        return await cls.create_user(session, mock_username)