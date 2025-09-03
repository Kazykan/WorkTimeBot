from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

class ObjectSelectCallback(CallbackData, prefix="object"):
    action: str  # "select" или "manual"
    object_id: int | None = None

# Common text constants
class Texts:
    # Main menu
    MAIN_MENU = "📋 Главное меню"
    BACK = "⬅️ Назад"
    CANCEL = "❌ Отмена"
    
    # Objects
    OBJECTS = "🏗️ Объекты"
    ADD_OBJECT = "➕ Добавить объект"
    DELETE_OBJECT = "🗑️ Удалить объект"
    
    # Time tracking
    ADD_HOURS = "⏰ Добавить часы"
    EDIT_HOURS = "✏️ Редактировать часы"
    
    # Payments
    ADD_PAYMENT = "💰 Добавить оплату"
    EDIT_PAYMENT = "✏️ Редактировать оплату"
    
    # Reports
    REPORTS = "📊 Отчёты"
    LAST_MONTH = "📅 За прошлый месяц"
    CUSTOM_PERIOD = "📆 За произвольный период"
    
    # Object status
    STATUS_ACTIVE = "🔵 Активен"
    STATUS_COMPLETED = "🟢 Завершён"
    COMPLETE_OBJECT = "✅ Завершить объект"
    REOPEN_OBJECT = "🔄 Открыть заново"
    
    # Actions
    ADD_TIME = "➕ Добавить часы"
    ADD_PAY = "💰 Добавить оплату"
    
    # Help
    HELP = "❓ Справка"
    
    # Date selection
    TODAY = "📅 Сегодня"
    YESTERDAY = "📅 Вчера"
    MANUAL_DATE = "✏️ Ввести дату вручную"
    
    # Object selection
    MANUAL_OBJECT = "✏️ Ввести объект вручную"
    
    # Messages
    WELCOME = (
        "👋 Добро пожаловать в бот учёта рабочего времени!\n\n"
        "Используйте команды:\n"
        "/add - добавить часы работы\n"
        "/payment - добавить оплату\n"
        "/objects - список объектов\n"
        "/report - отчёты\n"
        "/help - справка"
    )
    
    HELP_TEXT = (
        "📋 <b>Доступные команды:</b>\n\n"
        "🔹 <b>/start</b> - регистрация пользователя\n"
        "🔹 <b>/add</b> - добавить часы работы\n"
        "🔹 <b>/payment</b> - добавить оплату\n"
        "🔹 <b>/objects</b> - список объектов\n"
        "🔹 <b>/report</b> - отчёты за месяц или период\n"
        "🔹 <b>/help</b> - эта справка\n\n"
        "📝 <b>Редактирование:</b>\n"
        "🔹 <code>/edit_time_[id]</code> - редактировать часы\n"
        "🔹 <code>/edit_pay_[id]</code> - редактировать оплату\n\n"
        "💡 <b>Подсказки:</b>\n"
        "• Даты вводите в формате ДД.ММ.ГГ\n"
        "• Суммы вводите в рублях (например: 1500)\n"
        "• Часы вводите целыми числами"
    )


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Main menu keyboard"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=Texts.ADD_HOURS))
    builder.add(KeyboardButton(text=Texts.ADD_PAYMENT))
    builder.add(KeyboardButton(text=Texts.OBJECTS))
    builder.add(KeyboardButton(text=Texts.REPORTS))
    builder.add(KeyboardButton(text=Texts.HELP))
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Back button keyboard"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=Texts.BACK, callback_data="back"))
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel button keyboard"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=Texts.CANCEL, callback_data="cancel"))
    return builder.as_markup()


def get_date_selection_keyboard() -> InlineKeyboardMarkup:
    """Date selection keyboard with today, yesterday, and manual input options"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=Texts.TODAY, callback_data="date_today"))
    builder.add(InlineKeyboardButton(text=Texts.YESTERDAY, callback_data="date_yesterday"))
    builder.add(InlineKeyboardButton(text=Texts.MANUAL_DATE, callback_data="date_manual"))
    builder.add(InlineKeyboardButton(text=Texts.CANCEL, callback_data="cancel"))
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def get_object_selection_keyboard(objects: list) -> InlineKeyboardMarkup:
    """Генерация клавиатуры выбора объекта с кнопками для каждого объекта и опцией ручного ввода"""
    builder = InlineKeyboardBuilder()

    for obj in objects:
        builder.add(
            InlineKeyboardButton(
                text=f"🔵 {obj.name}",
                callback_data=ObjectSelectCallback(action="select", object_id=obj.id).pack()
            )
        )

    builder.add(
        InlineKeyboardButton(
            text=Texts.MANUAL_OBJECT,
            callback_data=ObjectSelectCallback(action="manual").pack()
        )
    )
    builder.add(
        InlineKeyboardButton(
            text=Texts.CANCEL,
            callback_data="cancel"
        )
    )

    builder.adjust(1)
    return builder.as_markup()
