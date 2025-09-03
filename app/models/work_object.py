from __future__ import annotations

from datetime import datetime, UTC
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.payment import Payment
    from app.models.time_entry import TimeEntry
    from app.models.user import User


class ObjectStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"


class WorkObject(Base):
    __tablename__ = "work_objects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ObjectStatus] = mapped_column(String(20), default=ObjectStatus.ACTIVE, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="work_objects")
    time_entries: Mapped[list[TimeEntry]] = relationship("TimeEntry", back_populates="work_object", cascade="all, delete-orphan")
    payments: Mapped[list[Payment]] = relationship("Payment", back_populates="work_object", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<WorkObject(id={self.id}, name='{self.name}', status='{self.status}')>"
