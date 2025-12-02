"""
🏪 Restaurant & Order API
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
import db
import auth
from datetime import datetime

router = APIRouter(prefix="/api", tags=["Restaurant"])


@router.get("/restaurants")
def get_restaurants():
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM restaurants WHERE is_active = true")
        return {"restaurants": [dict(r) for r in cur.fetchall()]}


@router.get("/restaurants/{rid}/menu")
def get_menu(rid: int):
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM menu_categories WHERE restaurant_id = ?", (rid,))
        cats = [dict(c) for c in cur.fetchall()]
        cur.execute("SELECT * FROM menu_items WHERE restaurant_id = ? AND is_available = true", (rid,))
        items = [dict(i) for i in cur.fetchall()]
    return {"categories": cats, "items": items}


class OrderItem(BaseModel):
    menu_item_id: int
    quantity: int = 1


class CreateOrder(BaseModel):
    restaurant_id: int
    items: List[OrderItem]
    address: Optional[str] = None
    notes: Optional[str] = None


@router.post("/orders")
def create_order(req: CreateOrder, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(401, "Login required")
    user = auth.get_user_from_token(authorization.replace("Bearer ", ""))
    if not user:
        raise HTTPException(401, "Invalid token")
    
    with db.get_connection() as conn:
        cur = conn.cursor()
        total = 0
        for item in req.items:
            cur.execute("SELECT price FROM menu_items WHERE id = ?", (item.menu_item_id,))
            r = cur.fetchone()
            if r:
                total += r['price'] * item.quantity
        
        cur.execute("""
            INSERT INTO orders (user_id, restaurant_id, total_amount, status, 
                              delivery_address, notes, created_at)
            VALUES (?, ?, ?, 'pending', ?, ?, ?)
        """, (user['id'], req.restaurant_id, total, req.address, req.notes, datetime.now()))
        conn.commit()
        order_id = cur._cursor.lastrowid or 1
        
    return {"success": True, "order_id": order_id, "total": total}


@router.get("/orders")
def get_orders(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(401, "Login required")
    user = auth.get_user_from_token(authorization.replace("Bearer ", ""))
    if not user:
        raise HTTPException(401, "Invalid token")
    
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC", (user['id'],))
        return {"orders": [dict(o) for o in cur.fetchall()]}
