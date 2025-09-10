from __future__ import annotations
from typing import Optional

from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.fsm.callback_data import ObjectCallback
from app.handlers.utils.db_utilits import get_user_and_objects, save_time_entry
from app.handlers.utils.time_entry import (
    prompt_for_comment,
    prompt_object_selection,
    validate_end_time,
)
from app.keyboards.common import (
    get_cancel_keyboard,
    get_date_selection_keyboard,
)
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
    waiting_for_select_object = State()
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
    return


@router.message(StateFilter(AddTimeStates.waiting_for_end_time))
async def process_end_time(message: types.Message, state: FSMContext):
    if not message.text or not message.from_user:
        await message.answer("❌ Пожалуйста, введите время окончания.")
        return

    data = await state.get_data()
    date = data["date"]
    start_time = data["start_time"]

    end_time = parse_time(message.text, date)
    if end_time is None:
        await message.answer(
            "❌ Неверный формат времени. Используйте формат ЧЧ:ММ\n"
            "Например: 17:30, 20:00, 22:45",
            reply_markup=get_cancel_keyboard(),
        )
        return

    if not await validate_end_time(end_time, start_time, message):
        return

    hours = calculate_hours(start_time, end_time)
    await state.update_data(end_time=end_time, hours=hours)

    if data.get("object_id"):
        await state.set_state(AddTimeStates.waiting_for_comment)
        await prompt_for_comment(message)
        return

    user, active_objects = await get_user_and_objects(message.from_user.id)
    if not user:
        await state.clear()
        await message.answer(
            "❌ Пользователь не найден. Используйте /start для регистрации."
        )
        return

    await state.set_state(AddTimeStates.waiting_for_select_object)
    await prompt_object_selection(message, active_objects)


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

    response = await save_time_entry(message.from_user.id, data, comment)

    if response is not None:
        if response.startswith("❌"):
            await message.answer(response)
        else:
            await message.answer(response, parse_mode="HTML")
    else:
        await message.answer("❌ Не удалось сохранить запись времени.")
    await state.clear()


@router.callback_query(lambda c: c.data == "cancel")
async def cancel_add_time(callback: types.CallbackQuery, state: FSMContext):
    """Cancel adding time entry"""
    await state.clear()
    if isinstance(callback.message, types.Message):
        await callback.message.edit_text("❌ Добавление часов отменено.")
    await callback.answer()


# 5. Обработка выбора объекта из списка -
@router.callback_query(
    StateFilter(AddTimeStates.waiting_for_select_object),
    ObjectCallback.filter(F.action == "select"),
)
async def handle_object_select(
    callback: types.CallbackQuery,
    callback_data: ObjectCallback,
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
@router.callback_query(
    StateFilter(AddTimeStates.waiting_for_select_object),
    ObjectCallback.filter(F.action == "manual"),
)
async def handle_manual_object_input(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddTimeStates.waiting_for_object)
    if isinstance(callback.message, types.Message):
        await callback.message.edit_text(
            "🏗️ Введите название объекта:\n\n"
            "Например: ЖК Олимпийский, Дача Марина, Ремонт квартиры",
            reply_markup=get_cancel_keyboard(),
        )
    await callback.answer()
