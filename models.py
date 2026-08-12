from pydantic import BaseModel
from typing import List, Optional

class CatalogItem(BaseModel):
    id: str
    category: str
    name: str
    image_url: Optional[str] = None
    status: str
    visible: bool
    unit: str

class Client(BaseModel):
    telegram_id: str
    name: str
    phone: str
    username: Optional[str] = None
    registered_at: Optional[str] = None

class CartItem(BaseModel):
    item_id: str
    item_name: str
    category: str
    quantity: float
    unit: str
    extra_info: str = ""

class SelectionPayload(BaseModel):
    order_id: str
    client: Client
    items: List[CartItem]

class CartItemInput(BaseModel):
    item_id: str
    quantity: float
    extra_info: Optional[str] = ""

class SubmitCartRequest(BaseModel):
    initData: str
    items: List[CartItemInput]
