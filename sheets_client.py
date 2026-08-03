import os
import json
import gspread
import re
from datetime import datetime
from google.oauth2.service_account import Credentials
import logging
from typing import List, Optional

from models import CatalogItem, Client, CartItem

logger = logging.getLogger(__name__)

def get_sheets_client() -> gspread.Client:
    """Инициализация клиента Google Sheets с использованием Service Account из переменных окружения."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    creds_info_str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_info_str:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON is not set in environment variables.")
        
    creds_info = json.loads(creds_info_str)
    credentials = Credentials.from_service_account_info(creds_info, scopes=scopes)
    
    return gspread.authorize(credentials)

def extract_drive_direct_url(raw_url: str) -> Optional[str]:
    """Нормализует любую ссылку Drive в https://drive.google.com/uc?export=view&id=FILE_ID"""
    if not raw_url:
        return None
        
    file_id = None
    # Check for id= format
    match_id = re.search(r'id=([a-zA-Z0-9_-]+)', raw_url)
    # Check for /d/ format
    match_d = re.search(r'/d/([a-zA-Z0-9_-]+)', raw_url)
    
    if match_id:
        file_id = match_id.group(1)
    elif match_d:
        file_id = match_d.group(1)
        
    if file_id:
        # Из-за новых политик Google Drive, обычные ссылки (uc?export=view) больше не встраиваются в <img>
        # Используем endpoint для thumbnails (работает для файлов с доступом "По ссылке")
        return f"https://drive.google.com/thumbnail?id={file_id}&sz=w800"
    return raw_url

class SheetsManager:
    def __init__(self, spreadsheet_name: str):
        self.spreadsheet_name = spreadsheet_name
        self._client: Optional[gspread.Client] = None
        self._spreadsheet = None

    def _get_spreadsheet(self):
        try:
            if not self._client:
                self._client = get_sheets_client()
            if not self._spreadsheet:
                self._spreadsheet = self._client.open(self.spreadsheet_name)
            return self._spreadsheet
        except Exception as e:
            logger.error(f"Failed to authenticate or open spreadsheet: {e}")
            self._client = None
            self._spreadsheet = None
            return None

    def _get_worksheet(self, title: str):
        spreadsheet = self._get_spreadsheet()
        if not spreadsheet:
            return None
        try:
            return spreadsheet.worksheet(title)
        except gspread.exceptions.WorksheetNotFound:
            # Create if not exists with header
            try:
                ws = spreadsheet.add_worksheet(title, 100, 20)
                if title == "Catalog":
                    ws.append_row(["id", "category", "name", "image_url", "status", "visible", "unit"])
                elif title == "Clients":
                    ws.append_row(["telegram_id", "name", "phone", "username", "registered_at"])
                elif title == "Selections":
                    ws.append_row(["timestamp", "order_id", "client_name", "phone", "telegram_id", "item_id", "item_name", "category", "quantity", "unit"])
                return ws
            except Exception as e:
                logger.error(f"Failed to create worksheet {title}: {e}")
                return None
        except Exception as e:
            logger.error(f"Error accessing worksheet {title}: {e}")
            return None

    def fetch_catalog_from_sheets(self) -> List[CatalogItem]:
        ws = self._get_worksheet("Catalog")
        if not ws:
            return []
            
        try:
            records = ws.get_all_records()
            items = []
            for r in records:
                visible_str = str(r.get("visible", "")).strip().lower()
                is_visible = visible_str in ["true", "1", "yes", "да"]
                
                if is_visible:
                    image_url = extract_drive_direct_url(str(r.get("image_url", "")))
                    items.append(CatalogItem(
                        id=str(r.get("id", "")),
                        category=str(r.get("category", "")),
                        name=str(r.get("name", "")),
                        image_url=image_url,
                        status=str(r.get("status", "")),
                        visible=True,
                        unit=str(r.get("unit", ""))
                    ))
            return items
        except Exception as e:
            logger.error(f"Error fetching catalog: {e}")
            return []

    def get_client_by_telegram_id(self, telegram_id: str) -> Optional[Client]:
        ws = self._get_worksheet("Clients")
        if not ws:
            return None
            
        try:
            values = ws.get_all_values()
            if not values or len(values) < 2:
                return None
                
            headers = [str(h).lower().strip() for h in values[0]]
            telegram_id_str = str(telegram_id).strip()
            
            for row in values[1:]:
                r_lower = dict(zip(headers, row))
                sheet_tg_id = str(r_lower.get("telegram_id", "")).replace(".0", "").replace("'", "").strip()
                
                if sheet_tg_id == telegram_id_str:
                    return Client(
                        telegram_id=sheet_tg_id,
                        name=str(r_lower.get("name", "")),
                        phone=str(r_lower.get("phone", "")),
                        username=str(r_lower.get("username", "")),
                        registered_at=str(r_lower.get("registered_at", ""))
                    )
            return None
        except Exception as e:
            logger.error(f"Error getting client: {e}")
            return None

    def save_or_update_client(self, telegram_id: str, name: str, phone: str, username: str = ""):
        ws = self._get_worksheet("Clients")
        if not ws:
            return
            
        try:
            telegram_id_str = str(telegram_id).strip()
            values = ws.get_all_values()
            
            # Если лист совсем пустой (даже без заголовков), пропишем заголовки
            if not values:
                ws.append_row(["telegram_id", "name", "phone", "username", "registered_at"])
                values = ws.get_all_values()
                
            headers = [str(h).lower().strip() for h in values[0]]
            
            row_index = -1
            for i, row in enumerate(values[1:]):
                r_lower = dict(zip(headers, row))
                sheet_tg_id = str(r_lower.get("telegram_id", "")).replace(".0", "").replace("'", "").strip()
                if sheet_tg_id == telegram_id_str:
                    row_index = i + 2 # +2 for 1-based index and skipping header
                    break
                    
            now_str = datetime.now().isoformat()
            if row_index != -1:
                # Row exists, let's update it (preserve registered_at)
                r_lower = dict(zip(headers, values[row_index - 1]))
                existing_registered_at = r_lower.get("registered_at", now_str)
                # In gspread v6+, values is the first parameter
                ws.update(values=[[telegram_id_str, name, phone, username, existing_registered_at]], range_name=f"A{row_index}:E{row_index}")
            else:
                # Append new client
                ws.append_row([telegram_id_str, name, phone, username, now_str])
        except Exception as e:
            logger.error(f"Error saving client: {e}")

    def create_selection(self, order_id: str, client: Client, items: List[CartItem]):
        ws = self._get_worksheet("Selections")
        if not ws:
            return
            
        try:
            timestamp = datetime.now().isoformat()
            rows_to_insert = []
            for item in items:
                row = [
                    timestamp,
                    order_id,
                    client.name,
                    client.phone,
                    client.telegram_id,
                    item.item_id,
                    item.item_name,
                    item.category,
                    item.quantity,
                    item.unit
                ]
                rows_to_insert.append(row)
                
            if rows_to_insert:
                ws.append_rows(rows_to_insert)
        except Exception as e:
            logger.error(f"Error creating selection: {e}")
