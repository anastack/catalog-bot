import asyncio
import logging
import os
from typing import List
from models import CatalogItem
from sheets_client import SheetsManager

logger = logging.getLogger(__name__)

class CatalogCache:
    def __init__(self):
        self._items: List[CatalogItem] = []
        self._lock = asyncio.Lock()
        
    async def get_items(self) -> List[CatalogItem]:
        """Получение данных из кэша."""
        async with self._lock:
            return list(self._items)
            
    async def force_refresh(self):
        """Принудительное обновление кэша каталога (синхронный gspread завернут в to_thread)."""
        logger.info("Force refreshing catalog cache...")
        spreadsheet_name = os.getenv("SPREADSHEET_NAME", "CatalogSheet")
        manager = SheetsManager(spreadsheet_name)
        
        try:
            # Обертка в to_thread, так как gspread выполняет синхронные I/O вызовы
            items = await asyncio.to_thread(manager.fetch_catalog_from_sheets)
            async with self._lock:
                self._items = items
            logger.info(f"Catalog cache updated. Total visible items: {len(self._items)}")
        except Exception as e:
            logger.error(f"Failed to refresh cache: {e}")

    async def sync_catalog_loop(self):
        """Фоновый цикл обновления кэша каждые 60 секунд."""
        while True:
            await self.force_refresh()
            await asyncio.sleep(60)

# Синглтон для кэша
cache = CatalogCache()
