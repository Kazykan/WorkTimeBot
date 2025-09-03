from __future__ import annotations

import re
from aiogram import Router, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.db.session import db_session
from app.keyboards.common import get_cancel_keyboard
from app.repositories.payment_repo import PaymentRepository
from app.repositories.time_repo import TimeEntryRepository
from app.repositories.user_repo import UserRepository
from app.utils.dateparse import parse_russian_date
from app.utils.formatting import format_currency, format_hours

router = Router()


class EditTimeStates(StatesGroup):
    waiting_for_hours = State()
    waiting_for_date = State()
    waiting_for_comment = State()


class EditPaymentStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_date = State()


@router.message(lambda message: message.text and message.text.startswith("/edit_time_"))
async def cmd_edit_time(message: types.Message, state: FSMContext):
    """Handle /edit_time_[id] command"""
    await state.clear()
    
    # Extract entry ID from command
    match = re.match(r"/edit_time_(\d+)", message.text)
    if not match:
        await message.answer("❌ Неверный формат команды. Используйте: /edit_time_[id]")
        return
    
    entry_id = int(match.group(1))
    
    # Get entry details
    async with db_session() as session:
        time_repo = TimeEntryRepository(session)
        user_repo = UserRepository(session)
        
        entry = await time_repo.get_by_id(entry_id)
        if not entry:
            await message.answer("❌ Запись не найдена.")
            return
        
        # Verify user owns this entry
        user = await user_repo.get_by_telegram_id(message.from_user.id)
        if not user or entry.work_object.user_id != user.id:
            await message.answer("❌ У вас нет доступа к этой записи.")
            return
        
        # Store entry info in state
        await state.update_data(entry_id=entry_id)
        await state.set_state(EditTimeStates.waiting_for_hours)
        
        # Show current entry info
        date_str = entry.date.strftime("%d.%m.%y")
        hours_str = format_hours(entry.hours)
        comment_str = f"\n💬 Комментарий: {entry.comment}" if entry.comment else ""
        
        await message.answer(
            f"✏️ <b>Редактирование записи часов</b>\n\n"
            f"📅 Дата: {date_str}\n"
            f"⏰ Часы: {hours_str}\n"
            f"🏗️ Объект: {entry.work_object.name}{comment_str}\n\n"
            f"Введите новое количество часов:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )


@router.message(lambda message: message.text and message.text.startswith("/edit_pay_"))
async def cmd_edit_payment(message: types.Message, state: FSMContext):
    """Handle /edit_pay_[id] command"""
    await state.clear()
    
    # Extract payment ID from command
    match = re.match(r"/edit_pay_(\d+)", message.text)
    if not match:
        await message.answer("❌ Неверный формат команды. Используйте: /edit_pay_[id]")
        return
    
    payment_id = int(match.group(1))
    
    # Get payment details
    async with db_session() as session:
        payment_repo = PaymentRepository(session)
        user_repo = UserRepository(session)
        
        payment = await payment_repo.get_by_id(payment_id)
        if not payment:
            await message.answer("❌ Запись оплаты не найдена.")
            return
        
        # Verify user owns this payment
        user = await user_repo.get_by_telegram_id(message.from_user.id)
        if not user or payment.work_object.user_id != user.id:
            await message.answer("❌ У вас нет доступа к этой записи.")
            return
        
        # Store payment info in state
        await state.update_data(payment_id=payment_id)
        await state.set_state(EditPaymentStates.waiting_for_amount)
        
        # Show current payment info
        date_str = payment.date.strftime("%d.%m.%y")
        amount_str = format_currency(payment.amount)
        
        await message.answer(
            f"✏️ <b>Редактирование записи оплаты</b>\n\n"
            f"📅 Дата: {date_str}\n"
            f"💰 Сумма: {amount_str}\n"
            f"🏗️ Объект: {payment.work_object.name}\n\n"
            f"Введите новую сумму в рублях:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )


# Time entry editing handlers
@router.message(StateFilter(EditTimeStates.waiting_for_hours))
async def process_edit_hours(message: types.Message, state: FSMContext):
    """Process new hours input"""
    try:
        hours = int(message.text)
        if hours <= 0:
            raise ValueError("Hours must be positive")
        
        await state.update_data(hours=hours)
        await state.set_state(EditTimeStates.waiting_for_date)
        
        await message.answer(
            "📅 Введите новую дату (формат ДД.ММ.ГГ):",
            reply_markup=get_cancel_keyboard()
        )
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите целое положительное число для часов работы.",
            reply_markup=get_cancel_keyboard()
        )


@router.message(StateFilter(EditTimeStates.waiting_for_date))
async def process_edit_date(message: types.Message, state: FSMContext):
    """Process new date input"""
    date = parse_russian_date(message.text)
    if not date:
        await message.answer(
            "❌ Неверный формат даты. Используйте формат ДД.ММ.ГГ",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    await state.update_data(date=date)
    await state.set_state(EditTimeStates.waiting_for_comment)
    
    await message.answer(
        "💬 Введите новый комментарий (или 'нет' для удаления):",
        reply_markup=get_cancel_keyboard()
    )


@router.message(StateFilter(EditTimeStates.waiting_for_comment))
async def process_edit_comment(message: types.Message, state: FSMContext):
    """Process new comment input and save changes"""
    data = await state.get_data()
    
    # Handle comment
    comment = None
    if message.text.lower() not in ["нет", "no", "удалить", "delete", ""]:
        comment = message.text.strip()
    
    # Update entry
    async with db_session() as session:
        time_repo = TimeEntryRepository(session)
        
        entry = await time_repo.update_entry(
            entry_id=data["entry_id"],
            hours=data["hours"],
            date=data["date"],
            comment=comment
        )
        
        if not entry:
            await message.answer("❌ Ошибка при обновлении записи.")
            await state.clear()
            return
    
    # Format success message
    date_str = data["date"].strftime("%d.%m.%y")
    hours_str = format_hours(data["hours"])
    
    success_text = (
        f"✅ <b>Запись обновлена!</b>\n\n"
        f"📅 Дата: {date_str}\n"
        f"⏰ Часы: {hours_str}\n"
        f"🏗️ Объект: {entry.work_object.name}"
    )
    
    if comment:
        success_text += f"\n💬 Комментарий: {comment}"
    
    await message.answer(success_text, parse_mode="HTML")
    await state.clear()


# Payment editing handlers
@router.message(StateFilter(EditPaymentStates.waiting_for_amount))
async def process_edit_amount(message: types.Message, state: FSMContext):
    """Process new amount input"""
    try:
        amount_rubles = int(message.text)
        if amount_rubles <= 0:
            raise ValueError("Amount must be positive")
        
        # Convert to kopecks
        amount_kopecks = amount_rubles * 100
        
        await state.update_data(amount_kopecks=amount_kopecks)
        await state.set_state(EditPaymentStates.waiting_for_date)
        
        await message.answer(
            "📅 Введите новую дату (формат ДД.ММ.ГГ):",
            reply_markup=get_cancel_keyboard()
        )
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите целое положительное число для суммы оплаты.",
            reply_markup=get_cancel_keyboard()
        )


@router.message(StateFilter(EditPaymentStates.waiting_for_date))
async def process_edit_payment_date(message: types.Message, state: FSMContext):
    """Process new payment date input and save changes"""
    data = await state.get_data()
    
    date = parse_russian_date(message.text)
    if not date:
        await message.answer(
            "❌ Неверный формат даты. Используйте формат ДД.ММ.ГГ",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    # Update payment
    async with db_session() as session:
        payment_repo = PaymentRepository(session)
        
        payment = await payment_repo.update_payment(
            payment_id=data["payment_id"],
            amount_kopecks=data["amount_kopecks"],
            date=date
        )
        
        if not payment:
            await message.answer("❌ Ошибка при обновлении записи оплаты.")
            await state.clear()
            return
    
    # Format success message
    date_str = date.strftime("%d.%m.%y")
    amount_str = format_currency(data["amount_kopecks"])
    
    success_text = (
        f"✅ <b>Запись оплаты обновлена!</b>\n\n"
        f"📅 Дата: {date_str}\n"
        f"💰 Сумма: {amount_str}\n"
        f"🏗️ Объект: {payment.work_object.name}"
    )
    
    await message.answer(success_text, parse_mode="HTML")
    await state.clear()


@router.callback_query(lambda c: c.data == "cancel")
async def cancel_edit(callback: types.CallbackQuery, state: FSMContext):
    """Cancel editing"""
    await state.clear()
    await callback.message.edit_text("❌ Редактирование отменено.")
    await callback.answer()
