from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from database.models import HITLTask, HITLTaskStatus

import logging

logger = logging.getLogger(__name__)

class HITLTaskService:

    @classmethod
    async def create_hitltask(
        cls,
        session: AsyncSession,
        hitl_task_id: UUID,
        thread_id: str,
        task_name: str,
        task_args: Optional[dict] = None,
        task_description: Optional[str] = None,
    ) -> HITLTask:
        '''
        Creates a new HITLTask and saves it to the database.

        Args:
            session: The async database session.
            thread_id: The thread_id of the parent UserRun.
            task_name: The name of the task.
            task_args: Optional dict of tool call arguments.
            task_description: Optional description of the task.

        Returns:
            The newly created HITLTask.

        Raises:
            ValueError: If thread_id is not a valid UUID string.
            IntegrityError: If the operation violates database constraints (e.g. invalid foreign key).
            Exception: If an unexpected error occurs during commit.
        '''

        hitl_task = HITLTask(
            hitl_task_id=hitl_task_id,
            thread_id=UUID(thread_id),
            task_name=task_name,
            task_args=task_args,
            task_description=task_description,
        )

        session.add(hitl_task)
        try:
            await session.commit()
            await session.refresh(hitl_task)
        except IntegrityError as e:
            await session.rollback()
            logger.error(f"Failed to create HITLTask: {str(e)}")
            raise e
        except Exception as e:
            await session.rollback()
            logger.error(f"Unexpected error occurred while creating HITLTask: {str(e)}")
            raise e

        return hitl_task
    
    @classmethod
    async def get_hitltask_by_id(
        cls,
        session: AsyncSession,
        hitl_task_id: str,
    ) -> Optional[HITLTask]:
        '''
        Retrieves a HITLTask by its ID.

        Args:
            session: The async database session.
            hitl_task_id: The ID of the HITLTask to retrieve.

        Returns:
            The HITLTask if found, otherwise None.

        Raises:
            ValueError: If hitl_task_id is not a valid UUID string.
        '''

        result = await session.get(HITLTask, UUID(hitl_task_id))
        return result
    
    @classmethod
    async def get_all_hitltasks(
        cls,
        session: AsyncSession,
    ) -> list[HITLTask]:
        '''
        Retrieves all HITLTasks from the database.

        Args:
            session: The async database session.

        Returns:
            A list of all HITLTask records.
        '''

        result = await session.execute(
            select(HITLTask)
        )
        return result.scalars().all()
    
    @classmethod
    async def update_hitltask(
        cls,
        session: AsyncSession,
        hitl_task_id: str,
        task_name: Optional[str] = None,
        task_description: Optional[str] = None,
    ) -> Optional[HITLTask]:
        '''
        Updates an existing HITLTask with the provided fields.

        Args:
            session: The async database session.
            hitl_task_id: The ID of the HITLTask to update.
            task_name: New task name, or None to leave unchanged.
            task_description: New task description, or None to leave unchanged.

        Returns:
            The updated HITLTask.

        Raises:
            ValueError: If hitl_task_id is not a valid UUID string, or if the HITLTask does not exist.
            IntegrityError: If the update violates database constraints.
            Exception: If an unexpected error occurs during commit.
        '''

        hitl_task = await session.get(HITLTask, UUID(hitl_task_id))
        if not hitl_task:
            raise ValueError(f"HITLTask with id {hitl_task_id} not found.")
        
        if task_name is not None:
            hitl_task.task_name = task_name
        if task_description is not None:
            hitl_task.task_description = task_description
        
        try:
            await session.commit()
            await session.refresh(hitl_task)
        except IntegrityError as e:
            await session.rollback()
            logger.error(f"Failed to update HITLTask: {str(e)}")
            raise e
        except Exception as e:
            await session.rollback()
            logger.error(f"Unexpected error occurred while updating HITLTask: {str(e)}")
            raise e

        return hitl_task
    
    @classmethod
    async def delete_hitltask(
        cls,
        session: AsyncSession,
        hitl_task_id: str,
    ) -> bool:
        '''
        Deletes a HITLTask by its ID.

        Args:
            session: The async database session.
            hitl_task_id: The ID of the HITLTask to delete.
        
        Returns:
            True if deletion was successful.

        Raises:
            ValueError: If hitl_task_id is not a valid UUID string, or if the HITLTask does not exist.
            IntegrityError: If the delete violates database constraints.
            Exception: If an unexpected error occurs during commit.
        '''

        hitl_task = await session.get(HITLTask, UUID(hitl_task_id))
        if not hitl_task:
            raise ValueError(f"HITLTask with id {hitl_task_id} not found.")
        
        try:
            await session.delete(hitl_task)
            await session.commit()
        except IntegrityError as e:
            await session.rollback()
            logger.error(f"Failed to delete HITLTask: {str(e)}")
            raise e
        except Exception as e:
            await session.rollback()
            logger.error(f"Unexpected error occurred while deleting HITLTask: {str(e)}")
            raise e

        return True
    
    @classmethod
    async def get_hitltasks_by_thread_id(
        cls,
        session: AsyncSession,
        thread_id: str,
    ) -> list[HITLTask]:
        '''
        Retrieves all HITLTasks associated with a specific UserRun.

        Args:
            session: The async database session.
            thread_id: The thread_id of the UserRun to filter by.

        Returns:
            A list of HITLTasks associated with the given thread_id.

        Raises:
            ValueError: If thread_id is not a valid UUID string.
        '''

        result = await session.execute(
            select(HITLTask).where(HITLTask.thread_id == UUID(thread_id))
        )
        return result.scalars().all()
    
    @classmethod
    async def get_hitltask_by_thread_id_and_task_name(
        cls,
        session: AsyncSession,
        thread_id: str,
        task_name: str,
    ) -> Optional[HITLTask]:
        '''
        Retrieves a HITLTask by its UserRun thread_id and task name.

        Args:
            session: The async database session.
            thread_id: The thread_id of the UserRun to filter by.
            task_name: The name of the task to filter by.

        Returns:
            The HITLTask if found, otherwise None.

        Raises:
            ValueError: If thread_id is not a valid UUID string.
        '''
        result = await session.execute(
            select(HITLTask).where(
                (HITLTask.thread_id == UUID(thread_id)) &
                (HITLTask.task_name == task_name)
            )
        )
        return result.scalars().first()
    
    # check if a task exist with a userrun, task, args and status 
    @classmethod
    async def get_hitltask_by_thread_id_task_name_args_and_status(
        cls,
        session: AsyncSession,
        thread_id: str,
        task_name: str,
        task_args: dict,
        status: HITLTaskStatus = HITLTaskStatus.PENDING,
    ) -> Optional[HITLTask]:
        '''
        Retrieves a HITLTask by its UserRun thread_id, task name, task args and status.

        Args:
            session: The async database session.
            thread_id: The thread_id of the UserRun to filter by.
            task_name: The name of the task to filter by.
            task_args: The arguments of the task to filter by.
            status: The status of the HITLTask to filter by (default is PENDING).
        Returns:
            The HITLTask if found, otherwise None.
        Raises:
            ValueError: If thread_id is not a valid UUID string.
        '''
        result = await session.execute(
            select(HITLTask).where(
                (HITLTask.thread_id == UUID(thread_id)) &
                (HITLTask.task_name == task_name) &
                (HITLTask.task_args == task_args) &
                (HITLTask.status == status)
            )
        )

        return result.scalars().first()
