from typing import Optional
from aiogram import types
from aiogram.fsm.context import FSMContext

from app.db.session import db_session
from app.handlers.utils.time_entry import get_user_by_telegram_id
from app.models.payment import Payment
from app.models.work_object import WorkObject
from app.repositories.object_repo import WorkObjectRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.time_repo import TimeEntryRepository
from app.repositories.user_repo import UserRepository

def format_success_message(data: dict, object_name: str, comment: Optional[str]) -> str:
    """Форматирование сообщения об успешном добавлении"""
    date_str = data["date"].strftime("%d.%m.%y")
    start_str = data["start_time"].strftime("%H:%M")
    end_str = data["end_time"].strftime("%H:%M")
    hours_str = format_hours(data["hours"])

    message = (
        f"✅ <b>Часы работы добавлены!</b>\n\n"
        f"📅 Дата: {date_str}\n"
        f"🕐 Время: {start_str} - {end_str}\n"
        f"⏰ Часы: {hours_str}\n"
        f"🏗️ Объект: {object_name}"
    )
    if comment:
        message += f"\n💬 Комментарий: {comment}"
    return message


async def resolve_or_create_object(
    repo: WorkObjectRepository, user_id: int, data: dict
) -> Optional[WorkObject]:
    """Получить или создать объект работы"""
    if object_id := data.get("object_id"):
        return await repo.get_by_id(object_id, user_id)
    work_object = await repo.get_by_name(user_id, data["object_name"])
    return work_object or await repo.create_object(user_id, data["object_name"])


async def get_active_objects_for_user(user_id: int) -> list[WorkObject]:
    """Get active (not completed) objects for user"""
    async with db_session() as session:
        object_repo = WorkObjectRepository(session)
        return await object_repo.get_all_for_user(user_id, include_completed=False)


async def get_user_and_objects(user_id: int):
    async with db_session() as session:
        user = await get_user_by_telegram_id(session, user_id)
        if not user:
            return None, None

        active_objects = await get_active_objects_for_user(user.id)
        return user, active_objects


async def save_time_entry(
    user_id: int, data: dict, comment: Optional[str]
) :
    async with db_session() as session:
        user_repo = UserRepository(session)
        object_repo = WorkObjectRepository(session)
        time_repo = TimeEntryRepository(session)

        user = await user_repo.get_by_telegram_id(user_id)
        if not user:
            return "❌ Пользователь не найден. Используйте /start для регистрации."

        work_object = await resolve_or_create_object(object_repo, user.id, data)
        if not work_object:
            return "❌ Объект не найден."

        await time_repo.create_entry(
            work_object_id=work_object.id,
            start_time=data["start_time"],
            end_time=data["end_time"],
            hours=data["hours"],
            date=data["date"],
            comment=comment,
        )
        return format_success_message(data, work_object.name, comment)


# 💾 Обёртка: управление транзакцией и сессией
async def process_payment_transaction(
    telegram_id: int,
    data: dict,
) -> Optional[Payment]:
    """Открывает сессию и сохраняет оплату"""
    async with db_session() as session:
        return await save_payment(session=session, telegram_id=telegram_id, data=data)


# 🧠 Логика: сохранение оплаты в БД
async def save_payment(
    session,
    telegram_id: int,
    data: dict,
) -> Optional[Payment]:
    """Получает пользователя, объект и сохраняет оплату"""
    user_repo = UserRepository(session)
    object_repo = WorkObjectRepository(session)
    payment_repo = PaymentRepository(session)

    # Получаем пользователя
    user = await user_repo.get_by_telegram_id(telegram_id)
    if not user:
        return None

    # Получаем или создаём объект
    work_object = await resolve_or_create_object(object_repo, user.id, data)
    if not work_object:
        return None

    # Создаём оплату
    payment = await payment_repo.create_payment(
        work_object_id=work_object.id,
        amount_kopecks=data["amount_kopecks"],
        date=data["date"],
    )

    # Присваиваем объект вручную для отображения (если не загружается автоматически)
    payment.work_object = work_object
    return payment