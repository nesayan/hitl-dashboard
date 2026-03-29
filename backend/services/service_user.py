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
        '''Create a new User.

        Args:
            session: The async database session.
            username: The unique username for the new user.

        Returns:
            The newly created User instance.

        Raises:
            IntegrityError: If the username already exists.
            Exception: If an unexpected error occurs during commit.
        '''
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
        '''Retrieve a User by their ID.

        Args:
            session: The async database session.
            user_id: The UUID string of the user to retrieve.

        Returns:
            The User if found, otherwise None.

        Raises:
            ValueError: If user_id is not a valid UUID string.
        '''
        result = await session.get(User, UUID(user_id))
        return result

    @classmethod
    async def get_user_by_username(
        cls,
        session: AsyncSession,
        username: str,
    ) -> Optional[User]:
        '''Retrieve a User by their username.

        Args:
            session: The async database session.
            username: The username to search for.

        Returns:
            The User if found, otherwise None.
        '''
        result = await session.execute(
            select(User).where(User.username == username)
        )
        return result.scalars().first()

    @classmethod
    async def get_all_users(
        cls,
        session: AsyncSession,
    ) -> list[User]:
        '''Retrieve all Users from the database.

        Args:
            session: The async database session.

        Returns:
            A list of all User records.
        '''
        result = await session.execute(select(User))
        return result.scalars().all()

    @classmethod
    async def update_user(
        cls,
        session: AsyncSession,
        user_id: str,
        username: Optional[str] = None,
    ) -> User:
        '''Update an existing User. Only non-None fields are modified.

        Args:
            session: The async database session.
            user_id: The UUID string of the user to update.
            username: New username, or None to leave unchanged.

        Returns:
            The updated User instance.

        Raises:
            ValueError: If no User exists with the given user_id.
            IntegrityError: If the new username already exists.
            Exception: If an unexpected error occurs during commit.
        '''
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
        '''Delete a User by their ID.

        Args:
            session: The async database session.
            user_id: The UUID string of the user to delete.

        Raises:
            ValueError: If no User exists with the given user_id.
            IntegrityError: If the user has associated runs (FK constraint).
            Exception: If an unexpected error occurs during commit.
        '''
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
        '''Create a mock user for development/testing.

        Returns the existing mock user if one already exists,
        otherwise creates a new one with username "mock".
        '''
        mock_username = "mock"
        existing_user = await cls.get_user_by_username(session, mock_username)
        if existing_user:
            return existing_user

        return await cls.create_user(session, mock_username)