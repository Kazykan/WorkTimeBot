from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, payment_id: int) -> Optional[Payment]:
        """Get payment by ID"""
        result = await self.session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_object_id(self, object_id: int) -> List[Payment]:
        """Get all payments for work object"""
        result = await self.session.execute(
            select(Payment)
            .where(Payment.work_object_id == object_id)
            .order_by(Payment.date.desc(), Payment.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_payment(
        self, 
        work_object_id: int, 
        amount_kopecks: int, 
        date: datetime
    ) -> Payment:
        """Create new payment"""
        payment = Payment(
            work_object_id=work_object_id,
            amount=amount_kopecks,
            date=date
        )
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def update_payment(
        self, 
        payment_id: int, 
        amount_kopecks: Optional[int] = None,
        date: Optional[datetime] = None
    ) -> Optional[Payment]:
        """Update payment"""
        payment = await self.get_by_id(payment_id)
        if payment:
            if amount_kopecks is not None:
                payment.amount = amount_kopecks
            if date is not None:
                payment.date = date
            await self.session.flush()
        return payment

    async def delete_payment(self, payment_id: int) -> bool:
        """Delete payment"""
        payment = await self.get_by_id(payment_id)
        if payment:
            await self.session.delete(payment)
            await self.session.flush()
            return True
        return False

    async def get_payments_in_period(
        self, 
        object_id: int, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Payment]:
        """Get payments within date range"""
        result = await self.session.execute(
            select(Payment)
            .where(
                Payment.work_object_id == object_id,
                Payment.date >= start_date,
                Payment.date <= end_date
            )
            .order_by(Payment.date.desc())
        )
        return list(result.scalars().all())
