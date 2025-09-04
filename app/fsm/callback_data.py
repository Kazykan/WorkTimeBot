from aiogram.filters.callback_data import CallbackData

# Новый класс CallbackData
class ObjectCallback(CallbackData, prefix="object"):
    action: str
    object_id: int | None = None