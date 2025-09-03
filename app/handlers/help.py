from __future__ import annotations

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from app.keyboards.common import Texts

router = Router()


@router.message(Command("help"))
async def cmd_help(message: types.Message, state: FSMContext):
    """Handle /help command"""
    await state.clear()
    
    await message.answer(
        Texts.HELP_TEXT,
        parse_mode="HTML"
    )


@router.message(lambda message: message.text == Texts.HELP)
async def help_button(message: types.Message, state: FSMContext):
    """Handle help button press"""
    await state.clear()
    
    await message.answer(
        Texts.HELP_TEXT,
        parse_mode="HTML"
    )
