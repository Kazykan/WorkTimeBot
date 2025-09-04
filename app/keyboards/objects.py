from __future__ import annotations

from typing import List

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.fsm.callback_data import ObjectCallback
from app.models.work_object import ObjectStatus, WorkObject
from app.utils.formatting import format_currency, format_hours


def get_objects_list_keyboard(objects: List[WorkObject], include_completed: bool = True) -> InlineKeyboardMarkup:
    """Keyboard for listing work objects"""
    builder = InlineKeyboardBuilder()

    for obj in objects:
        if not include_completed and obj.status == ObjectStatus.COMPLETED:
            continue
            
        status_emoji = "🔵" if obj.status == ObjectStatus.ACTIVE else "🟢"
        button_text = f"{status_emoji} {obj.name}"
        # ✅ Изменение 1: Заменяем строковый колбэк на экземпляр CallbackData
        callback_data = ObjectCallback(action="select", object_id=obj.id)
        
        builder.add(InlineKeyboardButton(text=button_text, callback_data=callback_data.pack()))
    
    # ✅ Изменение 2: Заменяем строковые колбэки на экземпляры CallbackData для кнопок фильтра
    if include_completed:
        builder.add(InlineKeyboardButton(text="🔵 Только активные", callback_data=ObjectCallback(action="active_only").pack()))
    else:
        builder.add(InlineKeyboardButton(text="🔵🟢 Все объекты", callback_data=ObjectCallback(action="all").pack()))
    
    # ✅ Изменение 3: Заменяем строковые колбэки на экземпляры CallbackData для остальных кнопок
    builder.add(InlineKeyboardButton(text="➕ Добавить объект", callback_data=ObjectCallback(action="add").pack()))
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data=ObjectCallback(action="back").pack()))
    
    builder.adjust(1)
    return builder.as_markup()

def get_object_actions_keyboard(
    work_object: WorkObject,
    total_hours: int = 0,
    total_payments: int = 0
) -> InlineKeyboardMarkup:
    """Keyboard for object actions"""
    builder = InlineKeyboardBuilder()
    
    # Object info header
    status_emoji = "🔵" if work_object.status == ObjectStatus.ACTIVE else "🟢"
    status_text = "Активен" if work_object.status == ObjectStatus.ACTIVE else "Завершён"
    
    # Action buttons
    builder.add(InlineKeyboardButton(text="➕ Добавить часы", callback_data=f"add_time_{work_object.id}"))
    builder.add(InlineKeyboardButton(text="💰 Добавить оплату", callback_data=f"add_payment_{work_object.id}"))
    
    # Status toggle
    if work_object.status == ObjectStatus.ACTIVE:
        builder.add(InlineKeyboardButton(text="✅ Завершить объект", callback_data=f"complete_{work_object.id}"))
    else:
        builder.add(InlineKeyboardButton(text="🔄 Открыть заново", callback_data=f"reopen_{work_object.id}"))
    
    # Delete button
    builder.add(InlineKeyboardButton(text="🗑️ Удалить объект", callback_data=f"delete_{work_object.id}"))
    
    # Back button
    builder.add(InlineKeyboardButton(text="⬅️ К списку объектов", callback_data="objects_list"))
    
    builder.adjust(1)  # One button per row
    return builder.as_markup()


def get_object_history_keyboard(
    work_object: WorkObject,
    time_entries: List,
    payments: List
) -> InlineKeyboardMarkup:
    """Keyboard showing object history with edit buttons"""
    builder = InlineKeyboardBuilder()
    
    # Time entries
    for entry in time_entries:
        date_str = entry.date.strftime("%d.%m.%y")
        button_text = f"⏰ {date_str} - {format_hours(entry.hours)}"
        if entry.comment:
            button_text += f" ({entry.comment[:20]}...)" if len(entry.comment) > 20 else f" ({entry.comment})"
        
        builder.add(InlineKeyboardButton(
            text=button_text, 
            callback_data=f"edit_time_{entry.id}"
        ))
    
    # Payments
    for payment in payments:
        date_str = payment.date.strftime("%d.%m.%y")
        amount_str = format_currency(payment.amount)
        button_text = f"💰 {date_str} - {amount_str}"
        
        builder.add(InlineKeyboardButton(
            text=button_text, 
            callback_data=f"edit_payment_{payment.id}"
        ))
    
    # Back to object actions
    builder.add(InlineKeyboardButton(text="⬅️ К объекту", callback_data=f"object_{work_object.id}"))
    
    builder.adjust(1)  # One button per row
    return builder.as_markup()


def get_confirm_delete_keyboard(object_id: int) -> InlineKeyboardMarkup:
    """Confirmation keyboard for object deletion"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="🗑️ Да, удалить", callback_data=f"confirm_delete_{object_id}"))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data=f"object_{object_id}"))
    
    builder.adjust(2)
    return builder.as_markup()
