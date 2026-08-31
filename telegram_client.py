import os
import httpx
import logging

logger = logging.getLogger(__name__)

# Фиксированный ID администратора, которому всегда приходят уведомления
ADMIN_CHAT_ID = "1057175921"

class TelegramNotifier:
    def __init__(self, bot_token: str, staff_chat_id: str):
        self.bot_token = bot_token
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        # Собираем список получателей: staff_chat_id + ADMIN_CHAT_ID (без дублей)
        recipients = []
        if staff_chat_id:
            recipients.append(staff_chat_id)
        if ADMIN_CHAT_ID and ADMIN_CHAT_ID not in recipients:
            recipients.append(ADMIN_CHAT_ID)
        self.recipients = recipients

    async def _send_to(self, client: httpx.AsyncClient, chat_id: str, text: str):
        """Отправляет одно сообщение в указанный чат."""
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        try:
            response = await client.post(self.api_url, json=payload)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send telegram notification to {chat_id}: {e}")

    async def notify_staff(self, text: str):
        """Отправка уведомления всем получателям."""
        if not self.bot_token or not self.recipients:
            logger.warning("Bot token or recipients missing, skipping notification.")
            return

        async with httpx.AsyncClient() as client:
            for chat_id in self.recipients:
                await self._send_to(client, chat_id, text)
