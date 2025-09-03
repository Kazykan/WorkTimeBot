from __future__ import annotations

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from app.db.session import db_session
from app.keyboards.common import Texts, get_main_keyboard
from app.repositories.user_repo import UserRepository

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Handle /start command - register user and show welcome"""
    await state.clear()
    
    async with db_session() as session:
        user_repo = UserRepository(session)
        
        # Get or create user
        user = await user_repo.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
    
    # Send welcome message with main keyboard
    await message.answer(
        Texts.WELCOME,
        reply_markup=get_main_keyboard()
    )
