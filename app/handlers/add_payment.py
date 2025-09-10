from __future__ import annotations
from datetime import timedelta

from aiogram import F, Router, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery

from app.db.session import db_session
from app.fsm.callback_data import AddPaymentCallback, ObjectCallback
from app.handlers.utils.db_utilits import (
    get_user_and_objects,
    process_payment_transaction,
)
from app.handlers.utils.time_entry import prompt_object_selection
from app.keyboards.common import Texts, get_cancel_keyboard, get_date_selection_keyboard
from app.repositories.object_repo import WorkObjectRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.user_repo import UserRepository
from app.utils.dateparse import get_today_in_timezone, parse_date, parse_russian_date
from app.utils.formatting import format_currency

router = Router()


class AddPaymentStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_date = State()
    waiting_for_manual_date = State()
    waiting_for_object = State()
    waiting_for_selection_object = State()


# 1. Обработка команды /payment и кнопки "Добавить оплату" -
@router.message(Command("payment"))
async def cmd_payment(message: types.Message, state: FSMContext):
    """Handle /payment command - start adding payment"""
    print("/payment command received")
    await state.clear()
    await state.set_state(AddPaymentStates.waiting_for_amount)

    await message.answer(
        "💰 <b>Добавление оплаты</b>\n\n" "Введите сумму в рублях (целое число):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(lambda message: message.text == Texts.ADD_PAYMENT)
async def add_payment_button(message: types.Message, state: FSMContext):
    """Handle add payment button press"""
    await cmd_payment(message, state)


# @router.callback_query(AddPaymentCallback.filter())
# async def add_payment_from_object(
#     callback: CallbackQuery, callback_data: AddPaymentCallback, state: FSMContext
# ):
#     """Handle inline button from object details to add payment for specific object"""
#     print("add_payment_from_object")
#     await state.clear()

#     object_id = callback_data.object_id
#     if object_id is None:
#         await callback.answer("❌ Некорректный идентификатор объекта")
#         return

#     # Verify object belongs to user
#     async with db_session() as session:
#         user_repo = UserRepository(session)
#         object_repo = WorkObjectRepository(session)
#         user = await user_repo.get_by_telegram_id(callback.from_user.id)
#         if not user:
#             await callback.answer("❌ Пользователь не найден")
#             return
#         work_object = await object_repo.get_by_id(object_id, user.id)
#         if not work_object:
#             await callback.answer("❌ Объект не найден")
#             return

#     # Store object_id and start FSM from amount step
#     await state.update_data(object_id=object_id)
#     await state.set_state(AddPaymentStates.waiting_for_amount)

#     if isinstance(callback.message, types.Message):
#         await callback.message.edit_text(
#             "💰 <b>Добавление оплаты</b>\n\nВведите сумму в рублях (целое число):",
#             reply_markup=get_cancel_keyboard(),
#             parse_mode="HTML",
#         )
#         await callback.answer()


# 2. Обработка ввода суммы оплаты -
@router.message(StateFilter(AddPaymentStates.waiting_for_amount))
async def process_amount(message: types.Message, state: FSMContext):
    """Process payment amount input"""
    try:
        amount_rubles = int(message.text)
        if amount_rubles <= 0:
            raise ValueError("Amount must be positive")

        # Convert to kopecks
        amount_kopecks = amount_rubles * 100

        await state.update_data(amount_kopecks=amount_kopecks)
        await state.set_state(AddPaymentStates.waiting_for_date)

        today = get_today_in_timezone()
        today_str = today.strftime("%d.%m.%y")

        await message.answer(
            f"📅 Введите дату (формат ДД.ММ.ГГ):\n\n"
            f"По умолчанию: <b>{today_str}</b>\n"
            f"Или отправьте дату в формате ДД.ММ.ГГ",
            reply_markup=get_date_selection_keyboard(),
            parse_mode="HTML",
        )

    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите целое положительное число для суммы оплаты.",
            reply_markup=get_date_selection_keyboard(),
        )


# 3. Обработка выбора даты из кнопок или ручного ввода -
@router.callback_query(
    StateFilter(AddPaymentStates.waiting_for_date),
    F.data.in_({"date_today", "date_yesterday", "date_manual"}),
)
async def handle_payment_date_selection(
    callback: types.CallbackQuery, state: FSMContext
):
    # логика для FSM AddPaymentStates
    if not isinstance(callback.message, types.Message):
        await callback.answer("❌ Ошибка: сообщение не найдено.")
        return

    data = callback.data
    current_state = await state.get_state()

    if data == "date_today":
        current_date = get_today_in_timezone()
    elif data == "date_yesterday":
        current_date = get_today_in_timezone() - timedelta(days=1)
    elif data == "date_manual":
        # Переводим в состояние ручного ввода
        if current_state == AddPaymentStates.waiting_for_date:
            await state.set_state(AddPaymentStates.waiting_for_date)
        elif current_state == AddPaymentStates.waiting_for_date:
            await state.set_state(AddPaymentStates.waiting_for_manual_date)
        if isinstance(callback.message, types.Message):
            await callback.message.answer(
                "📅 Пожалуйста, введите дату вручную в формате ДД.ММ.ГГ:",
                reply_markup=get_cancel_keyboard(),
            )
            await callback.answer()
            return
    await state.update_data(date=current_date)

    state_data = await state.get_data()
    object_id = state_data.get("object_id")

    if object_id:
        await callback.answer(f"Объект уже выбран.{object_id}")
        return

    user, active_objects = await get_user_and_objects(callback.from_user.id)
    if not user:
        await state.clear()
        await callback.answer(
            "❌ Пользователь не найден. Используйте /start для регистрации."
        )
        return

    await state.set_state(AddPaymentStates.waiting_for_selection_object)
    await prompt_object_selection(callback.message, active_objects)


# 📦 Хендлер: обработка ручного ввода названия объекта
@router.message(StateFilter(AddPaymentStates.waiting_for_object))
async def process_payment_object(message: types.Message, state: FSMContext):
    """Получает название объекта от пользователя и сохраняет оплату"""
    if not message.text or not message.from_user:
        await message.answer("❌ Название объекта не может быть пустым.")
        return

    data = await state.get_data()
    object_name = message.text.strip()

    if not object_name:
        await message.answer(
            "❌ Название объекта не может быть пустым.",
            reply_markup=get_cancel_keyboard(),
        )
        return

    # Добавляем название объекта в data для дальнейшей обработки
    data["object_name"] = object_name

    # Сохраняем оплату через обёртку с транзакцией
    payment = await process_payment_transaction(
        telegram_id=message.from_user.id,
        data=data,
    )

    if not payment:
        await message.answer(
            "❌ Пользователь не найден. Используйте /start для регистрации."
        )
        await state.clear()
        return

    # Форматируем сообщение об успешной оплате
    date_str = payment.date.strftime("%d.%m.%y")
    amount_str = format_currency(payment.amount)

    success_text = (
        f"✅ <b>Оплата добавлена!</b>\n\n"
        f"📅 Дата: {date_str}\n"
        f"💰 Сумма: {amount_str}\n"
        f"🏗️ Объект: {payment.work_object.name}"
    )

    await message.answer(success_text, parse_mode="HTML")
    await state.clear()


# 🧱 Хендлер: выбор объекта из списка
@router.callback_query(
    StateFilter(AddPaymentStates.waiting_for_selection_object),
    ObjectCallback.filter(F.action == "select"),
)
async def handle_object_select(
    callback: types.CallbackQuery,
    callback_data: ObjectCallback,
    state: FSMContext,
):
    """Сохраняет платеж и отправляет сообщение об успешной оплате"""
    if not isinstance(callback.message, types.Message):
        await callback.answer("❌ Ошибка: сообщение не найдено.")
        return

    await state.update_data(object_id=callback_data.object_id)
    data = await state.get_data()

    # Сохраняем оплату через обёртку с транзакцией
    payment = await process_payment_transaction(
        telegram_id=callback.from_user.id,
        data=data,
    )

    if not payment:
        await callback.message.answer(
            "❌ Пользователь не найден. Используйте /start для регистрации."
        )
        await state.clear()
        return

    # Форматируем сообщение об успешной оплате
    date_str = payment.date.strftime("%d.%m.%y")
    amount_str = format_currency(payment.amount)

    success_text = (
        f"✅ <b>Оплата добавлена!</b>\n\n"
        f"📅 Дата: {date_str}\n"
        f"💰 Сумма: {amount_str}\n"
        f"🏗️ Объект: {payment.work_object.name}"
    )

    await callback.message.answer(success_text, parse_mode="HTML")
    await state.clear()


# 🏗️ Хендлер: переход к ручному вводу названия объекта
@router.callback_query(
    StateFilter(AddPaymentStates.waiting_for_selection_object),
    ObjectCallback.filter(F.action == "manual"),
)
async def handle_manual_object_input(callback: types.CallbackQuery, state: FSMContext):
    """Переводит пользователя в состояние ввода названия объекта"""
    print("кнопка ручного ввода названия объекта")
    await state.set_state(AddPaymentStates.waiting_for_object)

    if isinstance(callback.message, types.Message):
        await callback.message.edit_text(
            "🏗️ Введите название объекта:\n\n"
            "Например: ЖК Олимпийский, Дача Марина, Ремонт квартиры",
            reply_markup=get_cancel_keyboard(),
        )
    await callback.answer()
