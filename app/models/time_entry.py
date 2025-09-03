from __future__ import annotations

from datetime import datetime, UTC
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.work_object import WorkObject


class TimeEntry(Base):
    __tablename__ = "time_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_object_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("work_objects.id"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    hours: Mapped[float] = mapped_column(Float, nullable=False)  # Calculated hours with minutes
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda:datetime.now(UTC), onupdate=datetime.utcnow, nullable=False)

    # Relationships
    work_object: Mapped[WorkObject] = relationship("WorkObject", back_populates="time_entries")

    def __repr__(self) -> str:
        return f"<TimeEntry(id={self.id}, hours={self.hours}, date='{self.date}')>"
