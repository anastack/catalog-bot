import os
import asyncio
import hmac
import hashlib
import json
import uuid
from urllib.parse import parse_qsl
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from cache import cache
from models import SubmitCartRequest, CartItem
from sheets_client import SheetsManager
from telegram_client import TelegramNotifier

app = FastAPI(title="Catalog Bot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def validate_telegram_init_data(init_data: str, bot_token: str) -> dict:
    """Проверяет подпись Telegram WebApp и возвращает распарсенные данные."""
    try:
        parsed_data = dict(parse_qsl(init_data))
        if "hash" not in parsed_data:
            return None
            
        hash_val = parsed_data.pop("hash")
        
        # Сортируем ключи и создаем строку
        data_check_string = "\n".join([f"{k}={v}" for k, v in sorted(parsed_data.items())])
        
        # Генерируем секретный ключ
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        
        # Вычисляем хеш
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if calculated_hash == hash_val:
            if "user" in parsed_data:
                parsed_data["user"] = json.loads(parsed_data["user"])
            return parsed_data
    except Exception:
        pass
    return None

from bot import start_bot

@app.on_event("startup")
async def startup_event():
    """События при запуске приложения."""
    asyncio.create_task(cache.sync_catalog_loop())
    asyncio.create_task(start_bot())

@app.get("/")
async def serve_webapp():
    """Отдаёт фронтенд Mini App."""
    return FileResponse("webapp/index.html")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/catalog")
async def get_catalog():
    """Отдаёт кэш (только visible, что уже фильтруется в cache)."""
    items = await cache.get_items()
    return items

@app.post("/invalidate-cache")
async def invalidate_cache():
    """Для Apps Script - принудительное обновление кэша."""
    await cache.force_refresh()
    return {"status": "success", "message": "Cache refreshed"}

async def process_notification(text: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    staff_chat_id = os.getenv("STAFF_CHAT_ID", "")
    notifier = TelegramNotifier(bot_token, staff_chat_id)
    await notifier.notify_staff(text)

@app.post("/submit-cart")
async def submit_cart(request: SubmitCartRequest, background_tasks: BackgroundTasks):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # 1. Проверяем подпись
    auth_data = validate_telegram_init_data(request.initData, bot_token)
    if not auth_data or "user" not in auth_data:
        raise HTTPException(status_code=403, detail="Invalid initData signature")
        
    telegram_id = str(auth_data["user"].get("id"))
    
    # 2. Находим клиента
    spreadsheet_name = os.getenv("SPREADSHEET_NAME", "CatalogSheet")
    manager = SheetsManager(spreadsheet_name)
    client = await asyncio.to_thread(manager.get_client_by_telegram_id, telegram_id)
    
    if not client:
        raise HTTPException(status_code=403, detail="Client not registered")
        
    # 3. Генерируем order_id
    order_id = str(uuid.uuid4())
    
    # 4. Собираем корзину, обогащая данными из кэша
    cached_items = await cache.get_items()
    catalog_dict = {item.id: item for item in cached_items}
    
    final_cart_items = []
    notification_lines = []
    
    for input_item in request.items:
        cat_item = catalog_dict.get(input_item.item_id)
        if not cat_item:
            continue
            
        cart_item = CartItem(
            item_id=cat_item.id,
            item_name=cat_item.name,
            category=cat_item.category,
            quantity=input_item.quantity,
            unit=cat_item.unit,
            extra_info=input_item.extra_info or ""
        )
        final_cart_items.append(cart_item)
        
        # Форматируем строку: • Ламинат дуб — 24 м²
        qty_str = f"{input_item.quantity:g}" # removes trailing zero decimals (e.g. 24.0 -> 24)
        extra_str = f" ({input_item.extra_info})" if input_item.extra_info else ""
        notification_lines.append(f"• {cat_item.name}{extra_str} — {qty_str} {cat_item.unit}")
        
    if not final_cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty or contains invalid items")
        
    # 5. Записываем в Google Sheets
    await asyncio.to_thread(manager.create_selection, order_id, client, final_cart_items)
    
    # 6. Отправляем уведомление сотрудникам
    notification_text = f"<b>{client.name}</b> ({client.phone}) отправил выбор:\n" + "\n".join(notification_lines)
    background_tasks.add_task(process_notification, notification_text)
    
    return {"status": "success", "order_id": order_id}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
