from datetime import datetime
from aiogram import types
from app.keyboards.common import get_cancel_keyboard, get_object_selection_keyboard
from app.repositories.user_repo import UserRepository


async def validate_end_time(
    end_time: datetime | None, start_time: datetime, message: types.Message
) -> bool:
    """Проверка корректности времени окончания"""
    if not end_time:
        await message.answer(
            "❌ Неверный формат времени. Используйте формат ЧЧ:ММ\n"
            "Например: 17:30, 20:00, 22:45",
            reply_markup=get_cancel_keyboard(),
        )
        return False

    if end_time <= start_time:
        await message.answer(
            "❌ Время окончания должно быть позже времени начала.",
            reply_markup=get_cancel_keyboard(),
        )
        return False

    return True


async def prompt_for_comment(message: types.Message):
    """Запрос комментария"""
    await message.answer(
        "💬 Добавить комментарий? (необязательно)\n\n"
        "Например: Монтаж труб, Покраска стен, Укладка плитки\n"
        "Или отправьте 'нет' для пропуска",
        reply_markup=get_cancel_keyboard(),
    )


async def get_user_by_telegram_id(session, telegram_id: int):
    user_repo = UserRepository(session)
    return await user_repo.get_by_telegram_id(telegram_id)


async def prompt_object_selection(message: types.Message, active_objects: list):
    if active_objects:
        await message.answer(
            "🏗️ Выберите объект или введите новый:",
            reply_markup=get_object_selection_keyboard(active_objects),
        )
    else:
        await message.answer(
            "🏗️ Введите название объекта:\n\n"
            "Например: ЖК Олимпийский, Дача Марина, Ремонт квартиры",
            reply_markup=get_cancel_keyboard(),
        )
