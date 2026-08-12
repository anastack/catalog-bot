import os
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

def get_webapp_keyboard() -> InlineKeyboardMarkup:
    miniapp_url = os.getenv("MINIAPP_URL", "https://example.com")
    
    # Добавляем параметр для сброса жесткого кэша в Telegram
    if "?" in miniapp_url:
        miniapp_url += "&v=2"
    else:
        miniapp_url += "?v=2"

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
