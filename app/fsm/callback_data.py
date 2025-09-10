from sys import prefix
from aiogram.filters.callback_data import CallbackData


# Новый класс CallbackData
class ObjectCallback(CallbackData, prefix="objects"):
    action: str
    object_id: int | None = None


class AddPaymentCallback(CallbackData, prefix="add_payment"):
    object_id: int | None = None
