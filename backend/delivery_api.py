"""🚴 Delivery API"""
from fastapi import APIRouter, HTTPException, Header
import db, auth
from datetime import datetime

router = APIRouter(prefix="/api", tags=["Delivery"])

@router.get("/orders/{oid}/track")
def track(oid: int, authorization: str = Header(None)):
    user = auth.get_user_from_token(authorization.replace("Bearer ", "") if authorization else "")
    if not user: raise HTTPException(401, "Login")
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT status FROM orders WHERE id=? AND user_id=?", (oid, user['id']))
        o = cur.fetchone()
    return {"order_id": oid, "status": o['status'] if o else "unknown"}

@router.get("/notifications")
def notifs(authorization: str = Header(None)):
    user = auth.get_user_from_token(authorization.replace("Bearer ", "") if authorization else "")
    if not user: raise HTTPException(401, "Login")
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 20", (user['id'],))
        return {"notifications": [dict(n) for n in cur.fetchall()]}
