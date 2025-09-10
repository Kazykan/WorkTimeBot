from __future__ import annotations
from operator import call

from aiogram import Router, types, F
from aiogram.types import Message
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


from app.db.session import db_session
from app.fsm.callback_data import ObjectCallback
from app.keyboards.common import Texts
from app.keyboards.objects import (
    get_confirm_delete_keyboard,
    get_object_actions_keyboard,
    get_objects_list_keyboard,
)
from app.models.work_object import ObjectStatus
from app.repositories.object_repo import WorkObjectRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.time_repo import TimeEntryRepository
from app.repositories.user_repo import UserRepository
from app.utils.formatting import format_currency, format_hours

router = Router()


class ObjectStates(StatesGroup):
    waiting_for_object = State()


@router.callback_query(
    StateFilter(ObjectStates.waiting_for_object),
    ObjectCallback.filter(F.action == "select"),
)
async def cmd_select_object(
    query: types.CallbackQuery, callback_data: ObjectCallback, state: FSMContext
):
    """Handle object selection"""
    print("cmd_select_object")
    await state.clear()
    print(f"cmd_select_object {callback_data.object_id}")
    object_id = callback_data.object_id  # теперь берём ID из callback_data
    if not object_id:
        await query.answer("❌ Некорректный идентификатор объекта")
        return

    async with db_session() as session:
        user_repo = UserRepository(session)
        object_repo = WorkObjectRepository(session)
        time_repo = TimeEntryRepository(session)
        payment_repo = PaymentRepository(session)

        # Получаем пользователя
        user = await user_repo.get_by_telegram_id(query.from_user.id)
        if not user:
            await query.answer("❌ Пользователь не найден")
            return

        # Получаем объект
        work_object = await object_repo.get_by_id(object_id, user.id)
        if not work_object:
            await query.answer("❌ Объект не найден")
            return

        # Получаем данные по объекту
        time_entries = await time_repo.get_by_object_id(object_id)
        payments = await payment_repo.get_by_object_id(object_id)

        total_hours = int(sum(entry.hours for entry in time_entries))
        total_payments = sum(payment.amount for payment in payments)

        # Формируем текст
        status_emoji = "🔵" if work_object.status == ObjectStatus.ACTIVE else "🟢"
        status_text = (
            "Активен" if work_object.status == ObjectStatus.ACTIVE else "Завершён"
        )

        info_text = (
            f"🏗️ <b>{work_object.name}</b>\n"
            f"Статус: {status_emoji} {status_text}\n"
            f"Всего часов: {format_hours(total_hours)}\n"
            f"Всего оплат: {format_currency(total_payments)}\n"
            f"Дата создания: {work_object.created_at.strftime('%d.%m.%y')}"
        )

        if time_entries:
            first_date = min(entry.date for entry in time_entries).strftime("%d.%m.%y")
            info_text += f"\nНачало работ: {first_date}"

        if work_object.status == ObjectStatus.COMPLETED and time_entries:
            last_date = max(entry.date for entry in time_entries).strftime("%d.%m.%y")
            info_text += f"\nЗавершение: {last_date}"

        # Добавляем список работ
        if time_entries:
            info_text += "\n\n🕒 <b>Записи работ:</b>"
            for entry in sorted(time_entries, key=lambda x: x.date):
                info_text += f"\n• {entry.date.strftime('%d.%m.%y')} — {format_hours(entry.hours)}"

        # Добавляем список оплат
        if payments:
            info_text += "\n\n💰 <b>Записи оплат:</b>"
            for payment in sorted(payments, key=lambda x: x.date):
                info_text += f"\n• {payment.date.strftime('%d.%m.%y')} — {format_currency(payment.amount)}"

        if isinstance(query.message, Message):
            # Редактируем сообщение с информацией
            await query.message.edit_text(
                info_text,
                reply_markup=get_object_actions_keyboard(
                    work_object, total_hours, total_payments
                ),
                parse_mode="HTML",
            )

    await query.answer()


# Остальные обработчики
@router.message(Command("objects"))
async def cmd_objects(message: types.Message, state: FSMContext):
    """Handle /objects command"""
    await state.clear()
    await show_objects_list(message, include_completed=True)


@router.message(lambda message: message.text == Texts.OBJECTS)
async def objects_button(message: types.Message, state: FSMContext):
    """Handle objects button press"""
    await state.clear()
    await show_objects_list(message, include_completed=True)


async def show_objects_list(message: types.Message, include_completed: bool = True):
    """Show list of work objects"""
    async with db_session() as session:
        user_repo = UserRepository(session)
        object_repo = WorkObjectRepository(session)

        user = await user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer(
                "❌ Пользователь не найден. Используйте /start для регистрации."
            )
            return

        objects = await object_repo.get_all_for_user(user.id, include_completed)

        if not objects:
            await message.answer(
                "📝 У вас пока нет объектов.\n\n"
                "Создайте первый объект, добавив часы работы или оплату.",
                reply_markup=get_objects_list_keyboard([], include_completed),
            )
            return

        status_text = "всех" if include_completed else "активных"
        await message.answer(
            f"🏗️ Ваши объекты ({status_text}):",
            reply_markup=get_objects_list_keyboard(objects, include_completed),
        )


@router.callback_query(lambda c: c.data == "objects_list")
async def objects_list_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle objects list callback"""
    await state.clear()
    await show_objects_list(callback.message, include_completed=True)
    await callback.answer()


@router.callback_query(lambda c: c.data == "objects_active_only")
async def objects_active_only_callback(
    callback: types.CallbackQuery, state: FSMContext
):
    """Handle active only filter callback"""
    await state.clear()
    await show_objects_list(callback.message, include_completed=False)
    await callback.answer()


@router.callback_query(lambda c: c.data == "objects_all")
async def objects_all_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle all objects filter callback"""
    await state.clear()
    await show_objects_list(callback.message, include_completed=True)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("complete_"))
async def complete_object_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle complete object callback"""
    object_id = int(callback.data.split("_")[1])

    async with db_session() as session:
        user_repo = UserRepository(session)
        object_repo = WorkObjectRepository(session)

        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        work_object = await object_repo.update_status(
            object_id, user.id, ObjectStatus.COMPLETED
        )
        if work_object:
            await callback.answer("✅ Объект завершён")
            # Refresh object details
            await object_details_callback(callback, state)
        else:
            await callback.answer("❌ Ошибка при завершении объекта")


@router.callback_query(lambda c: c.data.startswith("reopen_"))
async def reopen_object_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle reopen object callback"""
    object_id = int(callback.data.split("_")[1])

    async with db_session() as session:
        user_repo = UserRepository(session)
        object_repo = WorkObjectRepository(session)

        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        work_object = await object_repo.update_status(
            object_id, user.id, ObjectStatus.ACTIVE
        )
        if work_object:
            await callback.answer("🔄 Объект открыт заново")
            # Refresh object details
            await object_details_callback(callback, state)
        else:
            await callback.answer("❌ Ошибка при открытии объекта")


@router.callback_query(lambda c: c.data.startswith("delete_"))
async def delete_object_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle delete object callback"""
    object_id = int(callback.data.split("_")[1])

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

        await callback.message.edit_text(
            f"🗑️ <b>Удаление объекта</b>\n\n"
            f"Вы действительно хотите удалить объект <b>«{work_object.name}»</b>?\n\n"
            f"⚠️ Это действие нельзя отменить!",
            reply_markup=get_confirm_delete_keyboard(object_id),
            parse_mode="HTML",
        )

    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("confirm_delete_"))
async def confirm_delete_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle confirm delete callback"""
    object_id = int(callback.data.split("_")[2])

    async with db_session() as session:
        user_repo = UserRepository(session)
        object_repo = WorkObjectRepository(session)

        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        success = await object_repo.delete_object(object_id, user.id)
        if success:
            await callback.answer("🗑️ Объект удалён")
            await show_objects_list(callback.message, include_completed=True)
        else:
            await callback.answer("❌ Ошибка при удалении объекта")
