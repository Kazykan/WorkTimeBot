from __future__ import annotations

from datetime import datetime, UTC
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.work_object import WorkObject


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_object_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("work_objects.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # Amount in kopecks (1 ruble = 100 kopecks)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=datetime.utcnow, nullable=False)

    # Relationships
    work_object: Mapped[WorkObject] = relationship("WorkObject", back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, amount={self.amount}, date='{self.date}')>"
