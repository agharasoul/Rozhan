"""🎁 Coupon & Reviews API"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
import db, auth
from datetime import datetime

router = APIRouter(prefix="/api", tags=["Extras"])

# --- کوپن ---
@router.post("/coupons/apply")
def apply_coupon(code: str, order_id: int, authorization: str = Header(None)):
    user = auth.get_user_from_token(authorization.replace("Bearer ", "") if authorization else "")
    if not user: raise HTTPException(401, "Login")
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM coupons WHERE code=? AND is_active=true", (code,))
        c = cur.fetchone()
        if not c: raise HTTPException(400, "Invalid coupon")
        discount = c['discount_percent'] or c['discount_amount'] or 0
    return {"success": True, "discount": discount, "code": code}

# --- رزرو میز ---
class ReserveReq(BaseModel):
    date: str
    time: str
    guests: int = 2

@router.post("/reserve")
def reserve_table(req: ReserveReq, authorization: str = Header(None)):
    user = auth.get_user_from_token(authorization.replace("Bearer ", "") if authorization else "")
    if not user: raise HTTPException(401, "Login")
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO reservations (user_id, date, time, guests, status, created_at) VALUES (?,?,?,?,'pending',?)",
            (user['id'], req.date, req.time, req.guests, datetime.now()))
        conn.commit()
    return {"success": True, "message": "رزرو ثبت شد"}

# --- نظرات ---
class ReviewReq(BaseModel):
    order_id: int
    rating: int
    comment: str = ""

@router.post("/reviews")
def add_review(req: ReviewReq, authorization: str = Header(None)):
    user = auth.get_user_from_token(authorization.replace("Bearer ", "") if authorization else "")
    if not user: raise HTTPException(401, "Login")
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO reviews (user_id, order_id, rating, comment, created_at) VALUES (?,?,?,?,?)",
            (user['id'], req.order_id, req.rating, req.comment, datetime.now()))
        conn.commit()
    return {"success": True}

@router.get("/reviews/{rid}")
def get_reviews(rid: int):
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT r.*, u.name FROM reviews r LEFT JOIN users u ON r.user_id=u.id WHERE r.restaurant_id=? ORDER BY created_at DESC LIMIT 20", (rid,))
        return {"reviews": [dict(r) for r in cur.fetchall()]}
