from app.keyboards.common import Texts, get_main_keyboard, get_back_keyboard, get_cancel_keyboard
from app.keyboards.objects import (
    get_objects_list_keyboard,
    get_object_actions_keyboard,
    get_object_history_keyboard,
    get_confirm_delete_keyboard,
)

__all__ = [
    "Texts",
    "get_main_keyboard",
    "get_back_keyboard", 
    "get_cancel_keyboard",
    "get_objects_list_keyboard",
    "get_object_actions_keyboard",
    "get_object_history_keyboard",
    "get_confirm_delete_keyboard",
]
