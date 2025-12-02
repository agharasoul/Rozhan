"""💳 Payment API"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
import db, auth
from datetime import datetime
import hashlib

router = APIRouter(prefix="/api/payment", tags=["Payment"])

class PayReq(BaseModel):
    order_id: int
    amount: int

@router.post("/create")
def create_payment(req: PayReq, authorization: str = Header(None)):
    user = auth.get_user_from_token(authorization.replace("Bearer ", "") if authorization else "")
    if not user: raise HTTPException(401, "Login")
    
    authority = hashlib.md5(f"{req.order_id}{datetime.now()}".encode()).hexdigest()[:36]
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO payments (order_id, user_id, amount, authority, status, created_at) VALUES (?,?,?,?,'pending',?)",
            (req.order_id, user['id'], req.amount, authority, datetime.now()))
        conn.commit()
    
    return {"success": True, "authority": authority, "url": f"https://sandbox.zarinpal.com/pg/StartPay/{authority}"}

@router.post("/verify")
def verify_payment(authority: str, authorization: str = Header(None)):
    user = auth.get_user_from_token(authorization.replace("Bearer ", "") if authorization else "")
    if not user: raise HTTPException(401, "Login")
    
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE payments SET status='paid' WHERE authority=? AND user_id=?", (authority, user['id']))
        cur.execute("UPDATE orders SET status='paid' WHERE id=(SELECT order_id FROM payments WHERE authority=?)", (authority,))
        conn.commit()
    return {"success": True, "status": "paid"}
