import os
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

def get_webapp_keyboard() -> InlineKeyboardMarkup:
    miniapp_url = os.getenv("MINIAPP_URL", "https://example.com")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть каталог",
                    web_app=WebAppInfo(url=miniapp_url)
                )
            ]
        ]
    )
    return keyboard
