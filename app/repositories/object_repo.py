from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.work_object import ObjectStatus, WorkObject


class WorkObjectRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, object_id: int, user_id: int) -> Optional[WorkObject]:
        """Get work object by ID for specific user"""
        result = await self.session.execute(
            select(WorkObject).where(
                WorkObject.id == object_id,
                WorkObject.user_id == user_id,
                WorkObject.is_deleted == False
            )
        )
        return result.scalar_one_or_none()

    async def get_all_for_user(
        self, 
        user_id: int, 
        include_completed: bool = True
    ) -> List[WorkObject]:
        """Get all work objects for user"""
        query = select(WorkObject).where(
            WorkObject.user_id == user_id,
            WorkObject.is_deleted == False
        )
        
        if not include_completed:
            query = query.where(WorkObject.status == ObjectStatus.ACTIVE)
        
        query = query.order_by(WorkObject.created_at.desc())
        
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_object(self, user_id: int, name: str) -> WorkObject:
        """Create new work object"""
        work_object = WorkObject(
            user_id=user_id,
            name=name,
            status=ObjectStatus.ACTIVE
        )
        self.session.add(work_object)
        await self.session.flush()
        return work_object

    async def update_status(self, object_id: int, user_id: int, status: ObjectStatus) -> Optional[WorkObject]:
        """Update work object status"""
        work_object = await self.get_by_id(object_id, user_id)
        if work_object:
            work_object.status = status
            await self.session.flush()
        return work_object

    async def delete_object(self, object_id: int, user_id: int) -> bool:
        """Soft delete work object"""
        work_object = await self.get_by_id(object_id, user_id)
        if work_object:
            work_object.is_deleted = True
            await self.session.flush()
            return True
        return False

    async def get_by_name(self, user_id: int, name: str) -> Optional[WorkObject]:
        """Get work object by name for specific user"""
        result = await self.session.execute(
            select(WorkObject).where(
                WorkObject.user_id == user_id,
                WorkObject.name == name,
                WorkObject.is_deleted == False
            )
        )
        return result.scalar_one_or_none()

async def get_active_objects_for_user(user_id: int) -> list[WorkObject]:
    """Get active (not completed) objects for user"""
    async with db_session() as session:
        object_repo = WorkObjectRepository(session)
        return await object_repo.get_all_for_user(user_id, include_completed=False)
    

    