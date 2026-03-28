from typing import Optional
from uuid import UUID
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from database.models import UserRun

import logging

logger = logging.getLogger(__name__)


class UserRunService:

    @classmethod
    async def create_user_run(
        cls,
        session: AsyncSession,
        thread_id: str = None,
    ) -> UserRun:
        '''
        Creates a new UserRun and saves it to the database.
        If no thread_id is provided, one will be auto-generated via uuid4.

        Args:
            session: The async database session.
            thread_id: Optional UUID string to use as the primary key.
                       If None, a new UUID is generated automatically.

        Returns:
            The newly created UserRun instance.

        Raises:
            IntegrityError: If the thread_id already exists or violates a constraint.
            Exception: If an unexpected error occurs during commit.
        '''

        user_run = UserRun(
            thread_id=UUID(thread_id) if thread_id else uuid.uuid4(),
        )

        session.add(user_run)
        try:
            await session.commit()
            await session.refresh(user_run)
        except IntegrityError as e:
            await session.rollback()
            logger.error(f"Failed to create UserRun: {str(e)}")
            raise e
        except Exception as e:
            await session.rollback()
            logger.error(f"Unexpected error occurred while creating UserRun: {str(e)}")
            raise e

        return user_run

    @classmethod
    async def get_user_run_by_id(
        cls,
        session: AsyncSession,
        thread_id: str,
    ) -> Optional[UserRun]:
        '''
        Retrieves a single UserRun by its primary key (thread_id).

        Args:
            session: The async database session.
            thread_id: The UUID string of the UserRun to retrieve.

        Returns:
            The UserRun if found, otherwise None.

        Raises:
            ValueError: If thread_id is not a valid UUID string.
        '''

        result = await session.get(UserRun, UUID(thread_id))
        return result

    @classmethod
    async def get_all_user_runs(
        cls,
        session: AsyncSession,
    ) -> list[UserRun]:
        '''
        Retrieves all UserRun records from the database.

        Args:
            session: The async database session.

        Returns:
            A list of all UserRun records. Returns an empty list if none exist.
        '''

        result = await session.execute(
            select(UserRun)
        )
        return result.scalars().all()

    @classmethod
    async def delete_user_run(
        cls,
        session: AsyncSession,
        thread_id: str,
    ) -> None:
        '''
        Deletes a UserRun by its thread_id.
        Due to cascade="all, delete-orphan" on the UserRun.hitl_tasks
        relationship, all associated HITLTask records are also deleted.

        Args:
            session: The async database session.
            thread_id: The UUID string of the UserRun to delete.

        Raises:
            ValueError: If thread_id is not a valid UUID string,
                        or if no UserRun exists with the given thread_id.
            IntegrityError: If the delete violates a database constraint.
            Exception: If an unexpected error occurs during commit.
        '''

        user_run = await session.get(UserRun, UUID(thread_id))
        if not user_run:
            raise ValueError(f"UserRun with thread_id {thread_id} not found.")

        try:
            await session.delete(user_run)
            await session.commit()
        except IntegrityError as e:
            await session.rollback()
            logger.error(f"Failed to delete UserRun: {str(e)}")
            raise e
        except Exception as e:
            await session.rollback()
            logger.error(f"Unexpected error occurred while deleting UserRun: {str(e)}")
            raise e
