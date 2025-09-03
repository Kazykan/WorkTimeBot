from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.time_entry import TimeEntry


class TimeEntryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, entry_id: int) -> Optional[TimeEntry]:
        """Get time entry by ID"""
        result = await self.session.execute(
            select(TimeEntry).where(TimeEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def get_by_object_id(self, object_id: int) -> List[TimeEntry]:
        """Get all time entries for work object"""
        result = await self.session.execute(
            select(TimeEntry)
            .where(TimeEntry.work_object_id == object_id)
            .order_by(TimeEntry.date.desc(), TimeEntry.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_entry(
        self, 
        work_object_id: int, 
        start_time: datetime,
        end_time: datetime,
        hours: float, 
        date: datetime, 
        comment: Optional[str] = None
    ) -> TimeEntry:
        """Create new time entry"""
        entry = TimeEntry(
            work_object_id=work_object_id,
            start_time=start_time,
            end_time=end_time,
            hours=hours,
            date=date,
            comment=comment
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def update_entry(
        self, 
        entry_id: int, 
        hours: Optional[int] = None,
        date: Optional[datetime] = None,
        comment: Optional[str] = None
    ) -> Optional[TimeEntry]:
        """Update time entry"""
        entry = await self.get_by_id(entry_id)
        if entry:
            if hours is not None:
                entry.hours = hours
            if date is not None:
                entry.date = date
            if comment is not None:
                entry.comment = comment
            await self.session.flush()
        return entry

    async def delete_entry(self, entry_id: int) -> bool:
        """Delete time entry"""
        entry = await self.get_by_id(entry_id)
        if entry:
            await self.session.delete(entry)
            await self.session.flush()
            return True
        return False

    async def get_entries_in_period(
        self, 
        object_id: int, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[TimeEntry]:
        """Get time entries within date range"""
        result = await self.session.execute(
            select(TimeEntry)
            .where(
                TimeEntry.work_object_id == object_id,
                TimeEntry.date >= start_date,
                TimeEntry.date <= end_date
            )
            .order_by(TimeEntry.date.desc())
        )
        return list(result.scalars().all())
