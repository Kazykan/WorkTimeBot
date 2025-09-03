from __future__ import annotations

from aiogram import Router, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.db.session import db_session
from app.keyboards.common import Texts, get_cancel_keyboard
from app.repositories.object_repo import WorkObjectRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.user_repo import UserRepository
from app.utils.dateparse import get_today_in_timezone, parse_russian_date
from app.utils.formatting import format_currency

router = Router()


class AddPaymentStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_date = State()
    waiting_for_object = State()


@router.message(Command("payment"))
async def cmd_payment(message: types.Message, state: FSMContext):
    """Handle /payment command - start adding payment"""
    await state.clear()
    await state.set_state(AddPaymentStates.waiting_for_amount)
    
    await message.answer(
        "💰 <b>Добавление оплаты</b>\n\n"
        "Введите сумму в рублях (целое число):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(lambda message: message.text == Texts.ADD_PAYMENT)
async def add_payment_button(message: types.Message, state: FSMContext):
    """Handle add payment button press"""
    await cmd_payment(message, state)


@router.callback_query(lambda c: c.data.startswith("add_payment_"))
async def add_payment_from_object(callback: types.CallbackQuery, state: FSMContext):
    """Handle inline button from object details to add payment for specific object"""
    await state.clear()
    try:
        object_id = int(callback.data.split("_")[2])
    except Exception:
        await callback.answer("❌ Некорректный идентификатор объекта")
        return

    # Verify object belongs to user
    async with db_session() as session:
        user_repo = UserRepository(session)
        object_repo = WorkObjectRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return
        work_object = await object_repo.get_by_id(object_id, user.id)
        if not work_object:
            await callback.answer("❌ Объект не найден")
            return

    # Store object_id and start FSM from amount step
    await state.update_data(object_id=object_id)
    await state.set_state(AddPaymentStates.waiting_for_amount)

    await callback.message.edit_text(
        "💰 <b>Добавление оплаты</b>\n\nВведите сумму в рублях (целое число):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


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
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите целое положительное число для суммы оплаты.",
            reply_markup=get_cancel_keyboard()
        )


@router.message(StateFilter(AddPaymentStates.waiting_for_date))
async def process_payment_date(message: types.Message, state: FSMContext):
    """Process payment date input"""
    if message.text.lower() in ["сегодня", "today", "сейчас", "now"]:
        date = get_today_in_timezone()
    else:
        date = parse_russian_date(message.text)
        if not date:
            await message.answer(
                "❌ Неверный формат даты. Используйте формат ДД.ММ.ГГ\n"
                "Например: 15.08.24 или напишите 'сегодня'",
                reply_markup=get_cancel_keyboard()
            )
            return
    
    await state.update_data(date=date)
    data = await state.get_data()

    # If object_id was preset (from inline button), save immediately
    if data.get("object_id"):
        async with db_session() as session:
            user_repo = UserRepository(session)
            object_repo = WorkObjectRepository(session)
            payment_repo = PaymentRepository(session)

            user = await user_repo.get_by_telegram_id(message.from_user.id)
            if not user:
                await message.answer("❌ Пользователь не найден. Используйте /start для регистрации.")
                await state.clear()
                return

            work_object = await object_repo.get_by_id(data["object_id"], user.id)
            if not work_object:
                await message.answer("❌ Объект не найден.")
                await state.clear()
                return

            payment = await payment_repo.create_payment(
                work_object_id=work_object.id,
                amount_kopecks=data["amount_kopecks"],
                date=data["date"]
            )

        date_str = data["date"].strftime("%d.%m.%y")
        amount_str = format_currency(data["amount_kopecks"])
        success_text = (
            f"✅ <b>Оплата добавлена!</b>\n\n"
            f"📅 Дата: {date_str}\n"
            f"💰 Сумма: {amount_str}\n"
            f"🏗️ Объект: {work_object.name}"
        )
        await message.answer(success_text, parse_mode="HTML")
        await state.clear()
        return

    # Otherwise ask for object name
    await state.set_state(AddPaymentStates.waiting_for_object)
    await message.answer(
        "🏗️ Введите название объекта:\n\n"
        "Например: ЖК Олимпийский, Дача Марина, Ремонт квартиры",
        reply_markup=get_cancel_keyboard()
    )


@router.message(StateFilter(AddPaymentStates.waiting_for_object))
async def process_payment_object(message: types.Message, state: FSMContext):
    """Process payment object name input and save payment"""
    data = await state.get_data()
    
    object_name = message.text.strip()
    if not object_name:
        await message.answer(
            "❌ Название объекта не может быть пустым.",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    # Save to database
    async with db_session() as session:
        user_repo = UserRepository(session)
        object_repo = WorkObjectRepository(session)
        payment_repo = PaymentRepository(session)
        
        # Get or create user
        user = await user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден. Используйте /start для регистрации.")
            await state.clear()
            return
        
        # Get or create object
        work_object = await object_repo.get_by_name(user.id, object_name)
        if not work_object:
            work_object = await object_repo.create_object(user.id, object_name)
        
        # Create payment
        payment = await payment_repo.create_payment(
            work_object_id=work_object.id,
            amount_kopecks=data["amount_kopecks"],
            date=data["date"]
        )
    
    # Format success message
    date_str = data["date"].strftime("%d.%m.%y")
    amount_str = format_currency(data["amount_kopecks"])
    
    success_text = (
        f"✅ <b>Оплата добавлена!</b>\n\n"
        f"📅 Дата: {date_str}\n"
        f"💰 Сумма: {amount_str}\n"
        f"🏗️ Объект: {work_object.name}"
    )
    
    await message.answer(
        success_text,
        parse_mode="HTML"
    )
    
    await state.clear()


@router.callback_query(lambda c: c.data == "cancel")
async def cancel_add_payment(callback: types.CallbackQuery, state: FSMContext):
    """Cancel adding payment"""
    await state.clear()
    await callback.message.edit_text("❌ Добавление оплаты отменено.")
    await callback.answer()
