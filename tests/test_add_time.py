from unittest.mock import ANY, AsyncMock
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
import pytest
from app.handlers.add_time import cmd_add


@pytest.mark.asyncio
async def test_cmd_add():
    message = AsyncMock(spec=Message)
    message.answer = AsyncMock()
    state = AsyncMock(spec=FSMContext)

    await cmd_add(message, state)

    AddTimeStates = cmd_add.__globals__["AddTimeStates"]

    state.clear.assert_awaited_once()
    state.set_state.assert_awaited_once_with(AddTimeStates.waiting_for_date)

    message.answer.assert_awaited_once_with(
        "⏰ <b>Добавление часов работы</b>\n\n" "📅 Выберите дату:",
        reply_markup=ANY,
        parse_mode="HTML",
    )
