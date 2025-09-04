from __future__ import annotations
from typing import Optional

from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.db.session import db_session
from app.keyboards.common import (
    ObjectSelectCallback,
    Texts,
    get_cancel_keyboard,
    get_date_selection_keyboard,
    get_object_selection_keyboard,
)
from app.models.work_object import WorkObject
from app.repositories.object_repo import WorkObjectRepository
from app.repositories.time_repo import TimeEntryRepository
from app.repositories.user_repo import UserRepository
from app.utils.dateparse import (
    get_today_in_timezone,
    parse_date,
    parse_time,
    calculate_hours,
)
from app.utils.formatting import format_hours

router = Router()


class AddTimeStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_start_time = State()
    waiting_for_end_time = State()
    waiting_for_object = State()
    waiting_for_comment = State()


@router.message(Command("add"))
async def cmd_add(message: types.Message, state: FSMContext):
    """Handle /add command - start adding work hours"""
    await state.clear()
    await state.set_state(AddTimeStates.waiting_for_date)

    await message.answer(
        "⏰ <b>Добавление часов работы</b>\n\n" "📅 Выберите дату:",
        reply_markup=get_date_selection_keyboard(),
        parse_mode="HTML",
    )


@router.message(StateFilter(AddTimeStates.waiting_for_date))
async def process_date(message: types.Message, state: FSMContext):
    """Process date input"""
    if message.text and message.text.lower() in ["сегодня", "today", "сейчас", "now"]:
        date = get_today_in_timezone()
    else:
        if not message.text:
            await message.answer("❌ Пожалуйста, введите дату.")
            return
        parse_date_data = parse_date(message.text)
        if not parse_date_data:
            await message.answer(
                "❌ Неверный формат даты. Используйте формат ДД.ММ.ГГ\n"
                "Например: 15.08.24 или напишите 'сегодня'",
                reply_markup=get_cancel_keyboard(),
            )
            return
        date = parse_date_data

    await state.update_data(date=date)
    await state.set_state(AddTimeStates.waiting_for_start_time)

    await message.answer(
        "🕐 Введите время начала работы (формат ЧЧ:ММ):\n\n"
        "Например: 09:30, 14:00, 18:45",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(StateFilter(AddTimeStates.waiting_for_start_time))
async def process_start_time(message: types.Message, state: FSMContext):
    """Process start time input"""
    if not message.text:
        await message.answer("❌ Пожалуйста, введите время начала.")
        return

    data = await state.get_data()
    date = data["date"]

    start_time = parse_time(message.text, date)
    if not start_time:
        await message.answer(
            "❌ Неверный формат времени. Используйте формат ЧЧ:ММ\n"
            "Например: 09:30, 14:00, 18:45",
            reply_markup=get_cancel_keyboard(),
        )
        return

    await state.update_data(start_time=start_time)
    await state.set_state(AddTimeStates.waiting_for_end_time)

    await message.answer(
        "🕐 Введите время окончания работы (формат ЧЧ:ММ):\n\n"
        "Например: 17:30, 20:00, 22:45",
        reply_markup=get_cancel_keyboard(),
    )


async def get_active_objects_for_user(user_id: int) -> list[WorkObject]:
    """Get active (not completed) objects for user"""
    async with db_session() as session:
        object_repo = WorkObjectRepository(session)
        return await object_repo.get_all_for_user(user_id, include_completed=False)


@router.message(StateFilter(AddTimeStates.waiting_for_end_time))
async def process_end_time(message: types.Message, state: FSMContext):
    if not message.text or not message.from_user:
        await message.answer("❌ Пожалуйста, введите время окончания.")
        return

    data = await state.get_data()
    date = data["date"]
    start_time = data["start_time"]

    end_time = parse_time(message.text, date)
    if not end_time:
        await message.answer(
            "❌ Неверный формат времени. Используйте формат ЧЧ:ММ\n"
            "Например: 17:30, 20:00, 22:45",
            reply_markup=get_cancel_keyboard(),
        )
        return

    if end_time <= start_time:
        await message.answer(
            "❌ Время окончания должно быть позже времени начала.",
            reply_markup=get_cancel_keyboard(),
        )
        return

    hours = calculate_hours(start_time, end_time)
    await state.update_data(end_time=end_time, hours=hours)

    if data.get("object_id"):
        await state.set_state(AddTimeStates.waiting_for_comment)
        await message.answer(
            "💬 Добавить комментарий? (необязательно)\n\n"
            "Например: Монтаж труб, Покраска стен, Укладка плитки\n"
            "Или отправьте 'нет' для пропуска",
            reply_markup=get_cancel_keyboard(),
        )
        return

    async with db_session() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer(
                "❌ Пользователь не найден. Используйте /start для регистрации."
            )
            await state.clear()
            return

        active_objects = await get_active_objects_for_user(user.id)

    await state.set_state(AddTimeStates.waiting_for_object)

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


@router.message(StateFilter(AddTimeStates.waiting_for_object))
async def process_object(message: types.Message, state: FSMContext):
    """Process object name input"""
    if not message.text:
        await message.answer("❌ Название объекта не может быть пустым.")
        return

    object_name = message.text.strip()
    if not object_name:
        await message.answer(
            "❌ Название объекта не может быть пустым.",
            reply_markup=get_cancel_keyboard(),
        )
        return

    await state.update_data(object_name=object_name)
    await state.set_state(AddTimeStates.waiting_for_comment)

    await message.answer(
        "💬 Добавить комментарий? (необязательно)\n\n"
        "Например: Монтаж труб, Покраска стен, Укладка плитки\n"
        "Или отправьте 'нет' для пропуска",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(StateFilter(AddTimeStates.waiting_for_comment))
async def process_comment(message: types.Message, state: FSMContext):
    """Обработка комментария и сохранение записи времени"""
    if isinstance(message, types.Message) and not message.from_user:
        await message.answer("❌ Ошибка: сообщение не от пользователя.")
        return

    data = await state.get_data()
    comment = (
        message.text.strip()
        if message.text
        and message.text.lower() not in {"нет", "no", "пропустить", "skip", ""}
        else None
    )

    async with db_session() as session:
        user_repo = UserRepository(session)
        object_repo = WorkObjectRepository(session)
        time_repo = TimeEntryRepository(session)

        user = await user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer(
                "❌ Пользователь не найден. Используйте /start для регистрации."
            )
            return await state.clear()

        work_object = await resolve_or_create_object(object_repo, user.id, data)
        if not work_object:
            await message.answer("❌ Объект не найден.")
            return await state.clear()

        await time_repo.create_entry(
            work_object_id=work_object.id,
            start_time=data["start_time"],
            end_time=data["end_time"],
            hours=data["hours"],
            date=data["date"],
            comment=comment,
        )

    await message.answer(
        format_success_message(data, work_object.name, comment), parse_mode="HTML"
    )
    await state.clear()


async def resolve_or_create_object(
    repo: WorkObjectRepository, user_id: int, data: dict
) -> Optional[WorkObject]:
    """Получить или создать объект работы"""
    if object_id := data.get("object_id"):
        return await repo.get_by_id(object_id, user_id)
    work_object = await repo.get_by_name(user_id, data["object_name"])
    return work_object or await repo.create_object(user_id, data["object_name"])


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


@router.callback_query(lambda c: c.data == "cancel")
async def cancel_add_time(callback: types.CallbackQuery, state: FSMContext):
    """Cancel adding time entry"""
    await state.clear()
    if isinstance(callback.message, types.Message):
        await callback.message.edit_text("❌ Добавление часов отменено.")
    await callback.answer()


# 5. Обработка выбора объекта из списка -
@router.callback_query(ObjectSelectCallback.filter(F.action == "select"))
async def handle_object_select(
    callback: types.CallbackQuery,
    callback_data: ObjectSelectCallback,
    state: FSMContext,
):
    await state.update_data(object_id=callback_data.object_id)
    await state.set_state(AddTimeStates.waiting_for_comment)
    if isinstance(callback.message, types.Message):
        await callback.message.edit_text(
            "💬 Добавить комментарий? (необязательно)\n\n"
            "Например: Монтаж труб, Покраска стен, Укладка плитки\n"
            "Или отправьте 'нет' для пропуска",
            reply_markup=get_cancel_keyboard(),
        )
    await callback.answer()


# 6. Обработка ручного ввода объекта
@router.callback_query(ObjectSelectCallback.filter(F.action == "manual"))
async def handle_manual_object_input(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddTimeStates.waiting_for_object)
    if isinstance(callback.message, types.Message):
        await callback.message.edit_text(
            "🏗️ Введите название объекта:\n\n"
            "Например: ЖК Олимпийский, Дача Марина, Ремонт квартиры",
            reply_markup=get_cancel_keyboard(),
        )
    await callback.answer()
