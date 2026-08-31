import os
from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
import asyncio

from states import Registration
from keyboards import get_webapp_keyboard
from sheets_client import SheetsManager

router = Router()

def get_sheets_manager():
    spreadsheet_name = os.getenv("SPREADSHEET_NAME", "CatalogSheet")
    return SheetsManager(spreadsheet_name)

@router.message(CommandStart())
async def command_start_handler(message: types.Message, state: FSMContext):
    telegram_id = str(message.from_user.id)
    username = message.from_user.username or ""
    
    manager = get_sheets_manager()
    client = await asyncio.to_thread(manager.get_client_by_telegram_id, telegram_id)
    
    if client:
        await message.answer(
            "Добро пожаловать назад! Нажмите кнопку ниже, чтобы открыть каталог.",
            reply_markup=get_webapp_keyboard()
        )
    else:
        await message.answer("Добро пожаловать! Давайте зарегистрируемся.\nКак вас зовут?")
        await state.update_data(username=username)
        await state.set_state(Registration.waiting_for_name)

@router.message(Registration.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Отлично! Теперь введите ваш номер телефона (в любом удобном формате):")
    await state.set_state(Registration.waiting_for_phone)

@router.message(Registration.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("Введите название вашего ЖК (или напишите «—» если не применимо):")
    await state.set_state(Registration.waiting_for_lcd)

@router.message(Registration.waiting_for_lcd)
async def process_lcd(message: types.Message, state: FSMContext):
    await state.update_data(lcd=message.text)
    await message.answer("Введите номер вашей квартиры (или напишите «—» если не применимо):")
    await state.set_state(Registration.waiting_for_apt)

@router.message(Registration.waiting_for_apt)
async def process_apt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name = data.get("name")
    phone = data.get("phone")
    lcd = data.get("lcd", "—")
    apt = message.text
    username = data.get("username", "")
    telegram_id = str(message.from_user.id)
    
    manager = get_sheets_manager()
    await asyncio.to_thread(manager.save_or_update_client, telegram_id, name, phone, username, lcd, apt)
    
    await state.clear()
    await message.answer(
        "Регистрация завершена! Нажмите кнопку ниже, чтобы открыть каталог материалов.",
        reply_markup=get_webapp_keyboard()
    )

@router.message(~F.state)
async def any_other_message(message: types.Message, state: FSMContext):
    telegram_id = str(message.from_user.id)
    manager = get_sheets_manager()
    client = await asyncio.to_thread(manager.get_client_by_telegram_id, telegram_id)
    
    if client:
        await message.answer(
            "Для выбора материалов откройте каталог по кнопке ниже:",
            reply_markup=get_webapp_keyboard()
        )
    else:
        await command_start_handler(message, state)
