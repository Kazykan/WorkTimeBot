from __future__ import annotations

from aiogram import Router, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.session import db_session
from app.keyboards.common import Texts, get_cancel_keyboard
from app.repositories.object_repo import WorkObjectRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.time_repo import TimeEntryRepository
from app.repositories.user_repo import UserRepository
from app.services.reporting import ReportingService
from app.utils.dateparse import parse_russian_date

router = Router()


class ReportStates(StatesGroup):
    waiting_for_start_date = State()
    waiting_for_end_date = State()


@router.message(Command("report"))
async def cmd_report(message: types.Message, state: FSMContext):
    """Handle /report command - show report options"""
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=Texts.LAST_MONTH, callback_data="report_last_month"))
    builder.add(InlineKeyboardButton(text=Texts.CUSTOM_PERIOD, callback_data="report_custom"))
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="back"))
    builder.adjust(1)
    
    await message.answer(
        "📊 <b>Отчёты</b>\n\n"
        "Выберите период для отчёта:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )


@router.message(lambda message: message.text == Texts.REPORTS)
async def reports_button(message: types.Message, state: FSMContext):
    """Handle reports button press"""
    await cmd_report(message, state)


@router.callback_query(lambda c: c.data == "report_last_month")
async def report_last_month_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle last month report callback"""
    await state.clear()
    
    start_date, end_date = ReportingService.get_last_month_period()
    if isinstance(callback.message, types.Message):
        await generate_period_report(callback.message, callback.from_user.id, start_date, end_date)
        await callback.answer()


@router.callback_query(lambda c: c.data == "report_custom")
async def report_custom_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle custom period report callback"""
    await state.set_state(ReportStates.waiting_for_start_date)
    if isinstance(callback.message, types.Message):
        await callback.message.edit_text(
            "📅 <b>Отчёт за произвольный период</b>\n\n"
            "Введите начальную дату (формат ДД.ММ.ГГ):",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()


@router.message(StateFilter(ReportStates.waiting_for_start_date))
async def process_start_date(message: types.Message, state: FSMContext):
    """Process start date input"""
    if isinstance(message, types.Message):
        await message.answer("❌ Ошибка: сообщение не от пользователя.")
        return
    start_date = parse_russian_date(message.text)
    if not start_date:
        await message.answer(
            "❌ Неверный формат даты. Используйте формат ДД.ММ.ГГ\n"
            "Например: 01.08.24",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    await state.update_data(start_date=start_date)
    await state.set_state(ReportStates.waiting_for_end_date)
    
    await message.answer(
        "📅 Введите конечную дату (формат ДД.ММ.ГГ):",
        reply_markup=get_cancel_keyboard()
    )


@router.message(StateFilter(ReportStates.waiting_for_end_date))
async def process_end_date(message: types.Message, state: FSMContext):
    """Process end date input and generate report"""
    if isinstance(message, types.Message) or not message.from_user:
        await message.answer("❌ Ошибка: сообщение не от пользователя.")
        return
    data = await state.get_data()
    start_date = data["start_date"]
    
    end_date = parse_russian_date(message.text)
    if not end_date:
        await message.answer(
            "❌ Неверный формат даты. Используйте формат ДД.ММ.ГГ\n"
            "Например: 31.08.24",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    if end_date < start_date:
        await message.answer(
            "❌ Конечная дата не может быть раньше начальной.",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    await generate_period_report(message, message.from_user.id, start_date, end_date)
    await state.clear()


async def generate_period_report(message: types.Message, user_id: int, start_date, end_date):
    """Generate and send period report"""
    async with db_session() as session:
        user_repo = UserRepository(session)
        object_repo = WorkObjectRepository(session)
        time_repo = TimeEntryRepository(session)
        payment_repo = PaymentRepository(session)
        
        # Get user
        user = await user_repo.get_by_telegram_id(user_id)
        if not user:
            await message.answer("❌ Пользователь не найден. Используйте /start для регистрации.")
            return
        
        print(f'{user.id}, {user.telegram_id}, {user.first_name}')
        
        # Get all objects for user
        objects = await object_repo.get_all_for_user(user.id, include_completed=True)
        
        # Get time entries and payments for period
        all_time_entries = []
        all_payments = []
        


        for obj in objects:
            entries = await time_repo.get_entries_in_period(obj.id, start_date, end_date)
            payments = await payment_repo.get_payments_in_period(obj.id, start_date, end_date)

            print(f"\n🔍 Объект: {obj.name} (ID: {obj.id})")

            for entry in entries:
                print(f"⏱️ TimeEntry: {entry.id}, date: {entry.date}, duration: {entry.end_time} - {entry.start_time}")

            for payment in payments:
                print(f"💰 Payment: {payment.id}, date: {payment.date}, amount: {payment.amount}")

            all_time_entries.extend(entries)
            all_payments.extend(payments)
        
        print(f"Объекты: {[obj.name for obj in objects]}")
        print(f"Записей времени: {len(all_time_entries)}")
        print(f"Платежей: {len(all_payments)}")
        # Generate report
        report = ReportingService.generate_period_report(
            objects, all_time_entries, all_payments, start_date, end_date
        )
        
        # Format date range for header
        from app.utils.formatting import format_date_range
        date_range = format_date_range(start_date, end_date)
        
        report_text = f"📊 <b>Отчёт за период {date_range}</b>\n\n{report}"
        
        await message.answer(report_text, parse_mode="HTML")


@router.callback_query(lambda c: c.data == "cancel")
async def cancel_report(callback: types.CallbackQuery, state: FSMContext):
    """Cancel report generation"""
    await state.clear()
    if isinstance(callback.message, types.Message):
        await callback.message.edit_text("❌ Генерация отчёта отменена.")
        await callback.answer()
    else:
        await callback.answer()

