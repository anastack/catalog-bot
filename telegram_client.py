import os
import httpx
import logging

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, bot_token: str, staff_chat_id: str):
        self.bot_token = bot_token
        self.staff_chat_id = staff_chat_id
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    async def notify_staff(self, text: str):
        """Отправка уведомления сотрудникам."""
        if not self.bot_token or not self.staff_chat_id:
            logger.warning("Bot token or staff chat id missing, skipping notification.")
            return

        async with httpx.AsyncClient() as client:
            payload = {
                "chat_id": self.staff_chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            try:
                response = await client.post(self.api_url, json=payload)
                response.raise_for_status()
            except Exception as e:
                logger.error(f"Failed to send telegram notification: {e}")
