"""
🚀 روژان - FastAPI Server
با سیستم احراز هویت و تاریخچه چت
"""
import os
import hashlib
import base64
import json
import uuid
import traceback
import requests as http_client
import httpx

from dotenv import load_dotenv
load_dotenv()  # Load .env file first

from fastapi import FastAPI, HTTPException, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# 🔧 Local imports
from config import GAPGPT_API_KEY
from gemini_client import chat, transcribe
from ai_provider import AI
import db
import auth
import smart_learner
import emotion_detector
from restaurant_api import router as restaurant_router
from payment_api import router as payment_router
from delivery_api import router as delivery_router
from extras_api import router as extras_router

app = FastAPI(
    title="روژان API",
    description="چت هوشمند با Gemini + احراز هویت",
    version="2.0.0"
)

# CORS برای Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🏪 اضافه کردن روترها
app.include_router(restaurant_router)
app.include_router(payment_router)
app.include_router(delivery_router)
app.include_router(extras_router)


# ===== Auth Models =====

class SendCodeRequest(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None


class VerifyCodeRequest(BaseModel):
    code: str
    phone: Optional[str] = None
    email: Optional[str] = None


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    favorite_foods: Optional[list] = None
    allergies: Optional[list] = None
    dietary_preferences: Optional[list] = None


# ===== Chat Models =====

class ChatRequest(BaseModel):
    message: str = ""
    image: Optional[str] = None
    session_id: Optional[int] = None
    show_thinking: bool = False  # نمایش روند فکر کردن AI


class ChatResponse(BaseModel):
    response: str
    user_id: Optional[int] = None
    session_id: Optional[int] = None
    emotion: Optional[str] = None
    thinking: Optional[str] = None  # روند فکر کردن AI


class TranscribeRequest(BaseModel):
    audio: str
    mime_type: str = "audio/webm"


class TranscribeResponse(BaseModel):
    text: str


@app.get("/")
def root():
    return {"status": "ok", "message": "🌟 روژان API v2.0 - با احراز هویت!"}


# ===== Auth Endpoints =====

@app.post("/auth/send-code")
def send_code(request: SendCodeRequest):
    """ارسال کد تأیید به موبایل یا ایمیل"""
    success, message = auth.send_verification_code(request.phone, request.email)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"success": True, "message": message}


@app.post("/auth/verify")
def verify_code(request: VerifyCodeRequest):
    """تأیید کد و دریافت توکن"""
    success, message, data = auth.verify_code(request.code, request.phone, request.email)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {
        "success": True,
        "message": message,
        "token": data['token'],
        "user": {
            "id": data['user']['id'],
            "phone": data['user']['phone'],
            "email": data['user']['email'],
            "name": data['user']['name']
        },
        "expires_at": data['expires_at']
    }


@app.get("/auth/me")
def get_current_user(authorization: str = Header(None)):
    """دریافت اطلاعات کاربر فعلی"""
    if not authorization:
        raise HTTPException(status_code=401, detail="توکن وارد نشده")
    
    token = authorization.replace("Bearer ", "")
    user = auth.get_user_from_token(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")
    
    profile = db.get_customer_profile(user['id'])
    return {
        "user": user,
        "profile": profile
    }


@app.post("/auth/logout")
def logout(authorization: str = Header(None)):
    """خروج از سیستم"""
    if authorization:
        token = authorization.replace("Bearer ", "")
        auth.logout(token)
    return {"success": True, "message": "خروج موفق"}


class LinkAccountRequest(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    code: str

@app.post("/auth/link")
def link_account(request: LinkAccountRequest, authorization: str = Header(None)):
    """اتصال موبایل یا ایمیل به اکانت موجود"""
    if not authorization:
        raise HTTPException(status_code=401, detail="توکن وارد نشده")
    
    token = authorization.replace("Bearer ", "")
    user = auth.get_user_from_token(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")
    
    # تأیید کد
    conn = db.get_connection()
    cursor = conn.cursor()
    
    if request.phone:
        cursor.execute("""
            SELECT * FROM verification_codes 
            WHERE phone = %s AND code = %s AND is_used = FALSE AND expires_at > %s
            ORDER BY created_at DESC LIMIT 1
        """, (request.phone, request.code, datetime.now().isoformat()))
    else:
        cursor.execute("""
            SELECT * FROM verification_codes 
            WHERE email = %s AND code = %s AND is_used = FALSE AND expires_at > %s
            ORDER BY created_at DESC LIMIT 1
        """, (request.email, request.code, datetime.now().isoformat()))
    
    verification = cursor.fetchone()
    if not verification:
        conn.close()
        raise HTTPException(status_code=400, detail="کد نامعتبر یا منقضی شده")
    
    # علامت‌گذاری کد
    cursor.execute("UPDATE verification_codes SET is_used = 1 WHERE id = %s", (verification['id'],))
    
    # آپدیت کاربر
    if request.phone:
        cursor.execute("UPDATE users SET phone = %s WHERE id = %s", (request.phone, user['id']))
    else:
        cursor.execute("UPDATE users SET email = %s WHERE id = %s", (request.email, user['id']))
    
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "اکانت متصل شد"}


@app.post("/auth/merge")
def merge_accounts(authorization: str = Header(None)):
    """ادغام اکانت‌های یک کاربر (با ایمیل و موبایل یکسان)"""
    if not authorization:
        raise HTTPException(status_code=401, detail="توکن وارد نشده")
    
    token = authorization.replace("Bearer ", "")
    user = auth.get_user_from_token(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # پیدا کردن اکانت‌های مرتبط
    other_user = None
    if user['email']:
        cursor.execute("SELECT * FROM users WHERE email = %s AND id != %s", (user['email'], user['id']))
        other_user = cursor.fetchone()
    if not other_user and user['phone']:
        cursor.execute("SELECT * FROM users WHERE phone = %s AND id != %s", (user['phone'], user['id']))
        other_user = cursor.fetchone()
    
    if not other_user:
        conn.close()
        return {"success": False, "message": "اکانت دیگری پیدا نشد"}
    
    # انتقال پروفایل
    cursor.execute("""
        UPDATE customer_profiles SET user_id = %s WHERE user_id = %s
    """, (user['id'], other_user['id']))
    
    # انتقال چت‌ها
    cursor.execute("""
        UPDATE chat_history SET user_id = %s WHERE user_id = %s
    """, (user['id'], other_user['id']))
    
    # انتقال سفارشات
    cursor.execute("""
        UPDATE orders SET user_id = %s WHERE user_id = %s
    """, (user['id'], other_user['id']))
    
    # حذف اکانت قدیمی
    cursor.execute("DELETE FROM users WHERE id = %s", (other_user['id'],))
    
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "اکانت‌ها ادغام شدند"}


@app.put("/auth/profile")
def update_profile(request: UpdateProfileRequest, authorization: str = Header(None)):
    """آپدیت پروفایل کاربر"""
    if not authorization:
        raise HTTPException(status_code=401, detail="توکن وارد نشده")
    
    token = authorization.replace("Bearer ", "")
    user = auth.get_user_from_token(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")
    
    # آپدیت نام در جدول users
    if request.name:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET name = %s WHERE id = %s", (request.name, user['id']))
        conn.commit()
        conn.close()
        
        # پاک کردن cache کاربر
        try:
            db.cache_delete(f"user:id:{user['id']}")
            if user.get('phone'):
                db.cache_delete(f"user:phone:{user['phone']}")
            if user.get('email'):
                db.cache_delete(f"user:email:{user['email']}")
        except:
            pass
    
    # آپدیت پروفایل مشتری
    update_data = {}
    if request.favorite_foods is not None:
        update_data['favorite_foods'] = request.favorite_foods
    if request.allergies is not None:
        update_data['allergies'] = request.allergies
    if request.dietary_preferences is not None:
        update_data['dietary_preferences'] = request.dietary_preferences
    
    if update_data:
        db.update_customer_profile(user['id'], **update_data)
    
    # پاک کردن cache پروفایل
    try:
        db.cache_delete(f"profile:{user['id']}")
    except:
        pass
    
    # دریافت اطلاعات جدید کاربر
    updated_user = db.get_user_by_id(user['id'])
    updated_profile = db.get_customer_profile(user['id'])
    
    return {
        "success": True, 
        "message": "پروفایل آپدیت شد",
        "user": {
            "id": updated_user['id'],
            "name": updated_user.get('name'),
            "phone": updated_user.get('phone'),
            "email": updated_user.get('email')
        },
        "profile": updated_profile
    }


# ===== Smart Profile Endpoint =====

@app.get("/auth/smart-profile")
def get_smart_profile(authorization: str = Header(None)):
    """
    🧠 دریافت پروفایل هوشمند کامل (۱۲۰+ فیلد)
    همه چیزی که سیستم از کاربر یاد گرفته
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="توکن ارسال نشده")
    
    token = authorization.replace("Bearer ", "")
    user = auth.get_user_from_token(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")
    
    # گرفتن پروفایل کامل
    full_profile = smart_learner.get_full_profile(user['id'])
    
    # خلاصه متنی
    summary = smart_learner.get_profile_summary(user['id'])
    
    # هشدارها
    warnings = smart_learner.get_warnings(user['id'])
    
    return {
        "user_id": user['id'],
        "profile": full_profile,
        "summary": summary,
        "warnings": warnings,
        "total_fields": count_fields(full_profile)
    }


def count_fields(data: dict, prefix: str = "") -> int:
    """شمارش تعداد فیلدهای پر شده"""
    count = 0
    for key, value in data.items():
        if key.startswith('_'):
            continue
        if isinstance(value, dict):
            count += count_fields(value, f"{prefix}{key}.")
        elif isinstance(value, list):
            if value:
                count += 1
        elif value is not None:
            count += 1
    return count


# ===== Smart AI Endpoints =====

class AIProviderRequest(BaseModel):
    provider: str  # gemini, openai, claude


@app.get("/api/smart/provider")
def get_ai_provider():
    """🤖 دریافت AI Provider فعلی"""
    return {
        "current": AI.get_current_provider(),
        "available": ["gemini", "openai", "claude"]
    }


@app.post("/api/smart/provider")
def set_ai_provider(request: AIProviderRequest, authorization: str = Header(None)):
    """🔄 تغییر AI Provider"""
    if not authorization:
        raise HTTPException(status_code=401, detail="توکن ارسال نشده")
    
    try:
        AI.switch_provider(request.provider)
        return {"success": True, "provider": request.provider}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/smart/suggestions")
def get_suggestions(authorization: str = Header(None)):
    """🎯 پیشنهاد هوشمند غذا با AI"""
    if not authorization:
        raise HTTPException(status_code=401, detail="توکن ارسال نشده")
    
    user = auth.get_user_from_token(authorization.replace("Bearer ", ""))
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")
    
    result = smart_learner.get_proactive_suggestion(user['id'])
    return {"success": True, "data": result}


@app.get("/api/smart/patterns")
def get_patterns(authorization: str = Header(None)):
    """📊 تشخیص الگوهای رفتاری با AI"""
    if not authorization:
        raise HTTPException(status_code=401, detail="توکن ارسال نشده")
    
    user = auth.get_user_from_token(authorization.replace("Bearer ", ""))
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")
    
    result = smart_learner.detect_patterns(user['id'])
    return {"success": True, "data": result}


class HealthCheckRequest(BaseModel):
    foods: list


@app.post("/api/smart/health-check")
def check_health(request: HealthCheckRequest, authorization: str = Header(None)):
    """⚠️ بررسی سلامت غذا با AI"""
    if not authorization:
        raise HTTPException(status_code=401, detail="توکن ارسال نشده")
    
    user = auth.get_user_from_token(authorization.replace("Bearer ", ""))
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")
    
    warnings = smart_learner.check_health_warnings(user['id'], request.foods)
    return {"success": True, "warnings": warnings}


@app.get("/api/smart/churn")
def get_churn_prediction(authorization: str = Header(None)):
    """📉 پیش‌بینی ترک مشتری با AI"""
    if not authorization:
        raise HTTPException(status_code=401, detail="توکن ارسال نشده")
    
    user = auth.get_user_from_token(authorization.replace("Bearer ", ""))
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")
    
    result = smart_learner.predict_churn(user['id'])
    return {"success": True, "data": result}


@app.get("/api/smart/insights")
def get_insights(authorization: str = Header(None)):
    """📊 تحلیل سفارشات"""
    if not authorization:
        raise HTTPException(status_code=401, detail="توکن ارسال نشده")
    
    user = auth.get_user_from_token(authorization.replace("Bearer ", ""))
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")
    
    result = smart_learner.get_order_insights(user['id'])
    return {"success": True, "data": result}


# ===== Chat Endpoint با Context =====

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, authorization: str = Header(None)):
    """
    چت با روژان (متن + تصویر)
    اگر لاگین باشد، تاریخچه و پروفایل مشتری هم ارسال می‌شود
    """
    try:
        user_id = None
        context = ""
        primary_emotion: Optional[str] = None
        
        # اگر توکن داره، context کاربر رو بگیر
        if authorization:
            token = authorization.replace("Bearer ", "")
            user = auth.get_user_from_token(token)
            if user:
                user_id = user['id']
                
                # 🧠 context پروفایل هوشمند (۱۲۰+ فیلد)
                smart_profile = smart_learner.get_profile_summary(user_id)
                
                # هشدارهای مهم (آلرژی، بیماری)
                warnings = smart_learner.get_warnings(user_id)
                
                # context تاریخچه چت اخیر
                recent_chat = db.get_recent_context(user_id, limit=5)
                
                if smart_profile or recent_chat or warnings:
                    context = "🧠 اطلاعات مشتری:\n"
                    if warnings:
                        context += "\n".join(warnings) + "\n\n"
                    if smart_profile:
                        context += smart_profile + "\n\n"
                    if recent_chat:
                        context += "📝 مکالمات اخیر:\n" + recent_chat + "\n\n"
                    context += "---\nپیام جدید:\n"
        
        # ذخیره پیام کاربر قبل از گرفتن جواب (برای اینکه اگه abort شد، پیام از دست نره)
        session_id = request.session_id
        if user_id:
            try:
                # اگر session_id نداریم، یکی بساز
                if not session_id:
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    # عنوان session از اول پیام
                    title = request.message[:50] + "..." if len(request.message) > 50 else request.message
                    cursor.execute("""
                        INSERT INTO chat_sessions (user_id, title, message_count, created_at, updated_at)
                        VALUES (%s, %s, 0, NOW(), NOW())
                        RETURNING id
                    """, (user_id, title or 'مکالمه جدید'))
                    row = cursor.fetchone()
                    session_id = row['id'] if isinstance(row, dict) else row[0]
                    conn.commit()
                    conn.close()
                
                # ذخیره پیام کاربر فوری
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO chat_history (user_id, session_id, role, content, image_url, created_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                """, (user_id, session_id, 'user', request.message, request.image))
                cursor.execute("""
                    UPDATE chat_sessions SET message_count = message_count + 1, updated_at = NOW()
                    WHERE id = %s
                """, (session_id,))
                conn.commit()
                conn.close()
            except Exception as save_err:
                print(f"Warning: Could not save user message: {save_err}")
        
        # ارسال به Gemini با context
        full_message = context + request.message if context else request.message
        chat_result = chat(full_message, request.image, show_thinking=request.show_thinking)
        
        # پارس نتیجه (ممکنه dict یا str باشه)
        thinking = None
        if isinstance(chat_result, dict):
            response = chat_result.get("response", "")
            thinking = chat_result.get("thinking", None)
            if thinking:
                print(f"🧠 Thinking: {thinking[:100]}...")
        else:
            response = chat_result

        # تشخیص احساس اصلی کاربر بر اساس پیام متنی
        try:
            emo_result = emotion_detector.detect_emotion(request.message)
            primary_emotion = emo_result.get("primary_emotion", {}).get("emotion", "neutral")
        except Exception as emo_err:
            print(f"Emotion detection error: {emo_err}")
        
        # ذخیره جواب (اگر لاگین باشد)
        if user_id and session_id:
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO chat_history (user_id, session_id, role, content, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (user_id, session_id, 'assistant', response))
                cursor.execute("""
                    UPDATE chat_sessions SET message_count = message_count + 1, updated_at = NOW()
                    WHERE id = %s
                """, (session_id,))
                conn.commit()
                conn.close()
            except Exception as save_err:
                print(f"Warning: Could not save assistant message: {save_err}")
            
            # 🧠 یادگیری هوشمند از چت (۱۲۰+ فیلد)
            try:
                learn_result = smart_learner.learn_from_chat(user_id, request.message)
                if learn_result.get('learned'):
                    print(f"  🧠 Smart learned: {learn_result.get('categories', [])}")
            except Exception as learn_err:
                print(f"  ⚠️ Smart learning error: {learn_err}")
            
            # 🖼️ یادگیری از تصویر (اگه داشت)
            if request.image:
                try:
                    img_learn = smart_learner.learn_from_image(user_id, request.image)
                    if img_learn.get('learned'):
                        print(f"  🖼️ Image learned: {img_learn.get('analysis', {}).get('face_analysis', {}).get('emotion')}")
                except Exception as img_err:
                    print(f"  ⚠️ Image learning error: {img_err}")
        
        return ChatResponse(response=response, user_id=user_id, session_id=session_id, emotion=primary_emotion, thinking=thinking)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/transcribe")
def transcribe_endpoint(request: TranscribeRequest):
    """
    🎤 تبدیل صدا به متن + تشخیص احساس از صدا
    """
    try:
        print(f"🎤 Transcribe request: audio length={len(request.audio)}, mime={request.mime_type}")
        
        # تشخیص احساس از صدا
        result = transcribe(request.audio, request.mime_type, detect_emotion=True)
        
        if isinstance(result, dict):
            text = result.get("text", "")
            emotion = result.get("emotion", "neutral")
            confidence = result.get("confidence", 0.5)
            print(f"✅ Transcribed: {text[:50]}... | Emotion: {emotion} ({confidence:.0%})")
            return {
                "text": text,
                "emotion": emotion,
                "emotion_confidence": confidence
            }
        else:
            # فال‌بک - فقط متن
            return {"text": result, "emotion": "neutral", "emotion_confidence": 0.3}
            
    except Exception as e:
        print(f"❌ Transcribe error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class TTSRequest(BaseModel):
    text: str
    voice: str = "Kore"  # صدای پیش‌فرض Gemini
    emotion: str = None  # happy, sad, excited, calm, angry

# 🎙️ صداهای Gemini TTS
GEMINI_VOICES = {
    # زنانه
    "Kore": "👩 زن - طبیعی و گرم",
    "Aoede": "👩 زن - ملایم و آرام", 
    "Leda": "👩 زن - شاد و پرانرژی",
    "Zephyr": "👩 زن - حرفه‌ای",
    
    # مردانه
    "Puck": "👨 مرد - طبیعی و صمیمی",
    "Charon": "👨 مرد - جدی و رسمی",
    "Fenrir": "👨 مرد - قوی و محکم",
    "Orus": "👨 مرد - آرام و مطمئن",
    
    # خاص
    "Enceladus": "🧒 جوان - پرانرژی",
    "Iapetus": "👴 مسن - باتجربه",
}

@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    """
    🔊 تبدیل متن به صدا - فقط Gemini TTS
    مدل: gemini-2.5-flash-preview-tts (فارسی عالی)
    """
    try:
        text = request.text[:1500].strip()
        if not text:
            return {"success": False, "error": "Empty text"}
        
        # کش Redis
        cache_key = f"tts:{hashlib.md5(text.encode()).hexdigest()}"
        cached = db.cache_get(cache_key)
        if cached and cached.get('audio'):
            return {"audio": cached['audio'], "success": True, "cached": True}
        
        # نرمال‌سازی متن
        text = " ".join(text.split())
        
        # 🎤 Gemini TTS (فارسی عالی)
        gemini_voice = request.voice if request.voice in GEMINI_VOICES else "Kore"
        print(f"🔊 TTS: Gemini {gemini_voice}")
        
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.post(
                "https://api.gapgpt.app/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {GAPGPT_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gemini-2.5-flash-preview-tts",
                    "input": text,
                    "voice": gemini_voice,
                }
            )
            
            if response.status_code == 200:
                audio_data = response.content
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                audio_url = f"data:audio/mpeg;base64,{audio_base64}"
                
                # ذخیره در کش
                db.cache_set(cache_key, {"audio": audio_url}, 'menu')
                
                print(f"✅ Gemini TTS success: {len(audio_data)} bytes")
                return {"audio": audio_url, "success": True, "provider": "gemini"}
            else:
                print(f"❌ Gemini TTS failed: {response.status_code}")
                return {"success": False, "error": f"TTS error: {response.status_code}"}
            
    except Exception as e:
        print(f"TTS Error: {e}")
        return {"success": False, "error": str(e)}

@app.get("/tts/voices")
def get_tts_voices():
    """🎙️ لیست صداهای موجود برای TTS"""
    return {
        "voices": GEMINI_VOICES,
        "default": "Kore",
        "emotions": ["happy", "sad", "excited", "angry", "calm", "tired", "neutral"]
    }


# 🖼️ تحلیل تصویر
class ImageAnalysisRequest(BaseModel):
    image: str
    mode: str = "general"  # general, food, text, describe

@app.post("/analyze/image")
def analyze_image(request: ImageAnalysisRequest):
    """تحلیل تصویر با Gemini 3"""
    prompts = {
        "general": "این تصویر رو تحلیل کن.",
        "food": "غذای این تصویر چیه؟ کالری و مواد اولیه رو بگو. JSON بده.",
        "text": "متن این تصویر رو استخراج کن.",
        "describe": "این تصویر رو کامل توضیح بده."
    }
    
    try:
        image_data = request.image.split(",")[1] if "," in request.image else request.image
        
        r = http_client.post(
            "https://api.gapgpt.app/v1beta/models/gemini-3-pro-image-preview:generateContent",
            headers={"Authorization": f"Bearer {GAPGPT_API_KEY}"},
            json={"contents": [{"parts": [
                {"text": prompts.get(request.mode, prompts["general"])},
                {"inline_data": {"mime_type": "image/jpeg", "data": image_data}}
            ]}]},
            timeout=90
        )
        
        if r.ok:
            text = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            return {"success": True, "analysis": text, "mode": request.mode}
        return {"success": False, "error": r.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}


# 🎬 تحلیل ویدیو (چند فریم)
class VideoAnalysisRequest(BaseModel):
    frames: list  # لیست فریم‌ها base64
    question: str = "این ویدیو درباره چیه؟"

@app.post("/analyze/video")
def analyze_video(request: VideoAnalysisRequest):
    """تحلیل ویدیو با Gemini 3 - فریم‌ها رو تحلیل میکنه"""
    if not request.frames:
        return {"success": False, "error": "No frames"}
    
    try:
        # حداکثر 10 فریم
        frames = request.frames[:10]
        
        parts = [{"text": f"این {len(frames)} فریم از یک ویدیو هست. {request.question}"}]
        
        for i, frame in enumerate(frames):
            img = frame.split(",")[1] if "," in frame else frame
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img}})
        
        r = http_client.post(
            "https://api.gapgpt.app/v1beta/models/gemini-3-pro-image-preview:generateContent",
            headers={"Authorization": f"Bearer {GAPGPT_API_KEY}"},
            json={"contents": [{"parts": parts}]},
            timeout=120
        )
        
        if r.ok:
            text = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            return {"success": True, "analysis": text, "frames_analyzed": len(frames)}
        return {"success": False, "error": r.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}


# 🧠 یادگیری از تصویر کاربر
class ImageLearnRequest(BaseModel):
    image: str  # base64

@app.post("/learn/image")
def learn_from_image_endpoint(request: ImageLearnRequest, authorization: str = Header(None)):
    """
    🖼️ یادگیری از تصویر کاربر
    - تشخیص چهره و احساس
    - پیشنهاد غذا بر اساس حال
    """
    if not authorization:
        return {"success": False, "error": "نیاز به لاگین"}
    
    token = authorization.replace("Bearer ", "")
    user = auth.get_user_from_token(token)
    if not user:
        return {"success": False, "error": "توکن نامعتبر"}
    
    result = smart_learner.learn_from_image(user['id'], request.image)
    return result


@app.get("/suggest/food")
def get_food_suggestion(authorization: str = Header(None)):
    """
    🍕 پیشنهاد غذا بر اساس حال کاربر
    """
    if not authorization:
        return {"suggestion": "یه غذای خوشمزه امتحان کن!", "reason": "لاگین کن تا شخصی‌تر پیشنهاد بدم"}
    
    token = authorization.replace("Bearer ", "")
    user = auth.get_user_from_token(token)
    if not user:
        return {"suggestion": "یه غذای خوشمزه!", "reason": "توکن نامعتبر"}
    
    return smart_learner.get_food_suggestion_by_mood(user['id'])


# 🎤 یادگیری از صدای کاربر
class AudioLearnRequest(BaseModel):
    audio: str  # base64
    mime_type: str = "audio/webm"

@app.post("/learn/audio")
def learn_from_audio_endpoint(request: AudioLearnRequest, authorization: str = Header(None)):
    """
    🎤 یادگیری از صدای کاربر
    - تشخیص احساس از لحن
    - تشخیص لهجه → شهر
    - تخمین شخصیت
    - تشخیص محیط (بچه، دفتر، خیابان)
    """
    if not authorization:
        return {"success": False, "error": "نیاز به لاگین"}
    
    token = authorization.replace("Bearer ", "")
    user = auth.get_user_from_token(token)
    if not user:
        return {"success": False, "error": "توکن نامعتبر"}
    
    result = smart_learner.learn_from_audio(user['id'], request.audio, request.mime_type)
    return result


@app.get("/chat/history")
def get_chat_history(authorization: str = Header(None), limit: int = 50):
    """دریافت تاریخچه چت کاربر"""
    if not authorization:
        raise HTTPException(status_code=401, detail="توکن وارد نشده")
    
    token = authorization.replace("Bearer ", "")
    user = auth.get_user_from_token(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")
    
    history = db.get_chat_history(user['id'], limit)
    return {"history": history}


# ===== Chat Sessions (تاریخچه مکالمات) =====

@app.get("/chat/sessions")
def get_chat_sessions(authorization: str = Header(None), q: str = None):
    """لیست همه مکالمات کاربر - با قابلیت جستجو در عنوان و محتوای پیام‌ها"""
    if not authorization:
        raise HTTPException(status_code=401, detail="توکن وارد نشده")
    
    token = authorization.replace("Bearer ", "")
    user = auth.get_user_from_token(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    if q and q.strip():
        # جستجو در عنوان session و محتوای پیام‌ها
        search_term = f"%{q.strip()}%"
        cursor.execute("""
            SELECT DISTINCT s.id, s.title, s.created_at, s.updated_at, s.message_count
            FROM chat_sessions s
            LEFT JOIN chat_history h ON s.id = h.session_id
            WHERE s.user_id = %s AND (
                s.title ILIKE %s OR 
                h.content ILIKE %s
            )
            ORDER BY s.updated_at DESC
        """, (user['id'], search_term, search_term))
    else:
        cursor.execute("""
            SELECT id, title, created_at, updated_at, message_count
            FROM chat_sessions
            WHERE user_id = %s
            ORDER BY updated_at DESC
        """, (user['id'],))
    
    sessions = [dict(row) if hasattr(row, 'keys') else {
        'id': row[0], 'title': row[1], 'created_at': row[2], 
        'updated_at': row[3], 'message_count': row[4]
    } for row in cursor.fetchall()]
    
    conn.close()
    return {"sessions": sessions}


@app.post("/chat/sessions")
def create_chat_session(authorization: str = Header(None)):
    """ایجاد مکالمه جدید"""
    if not authorization:
        raise HTTPException(status_code=401, detail="توکن وارد نشده")
    
    token = authorization.replace("Bearer ", "")
    user = auth.get_user_from_token(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO chat_sessions (user_id, title, created_at, updated_at)
        VALUES (%s, %s, %s, %s)
    """, (user['id'], 'مکالمه جدید', datetime.now().isoformat(), datetime.now().isoformat()))
    
    conn.commit()
    
    # Get the new session ID
    cursor.execute("SELECT id FROM chat_sessions WHERE user_id = %s ORDER BY id DESC LIMIT 1", (user['id'],))
    row = cursor.fetchone()
    session_id = row[0] if row else row['id'] if hasattr(row, 'keys') else None
    
    conn.close()
    return {"session_id": session_id, "message": "مکالمه جدید ایجاد شد"}


@app.get("/chat/sessions/{session_id}")
def get_session_messages(session_id: int, authorization: str = Header(None)):
    """پیام‌های یک مکالمه خاص"""
    if not authorization:
        raise HTTPException(status_code=401, detail="توکن وارد نشده")
    
    token = authorization.replace("Bearer ", "")
    user = auth.get_user_from_token(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Check ownership
    cursor.execute("SELECT user_id FROM chat_sessions WHERE id = %s", (session_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="مکالمه پیدا نشد")
    
    owner_id = row[0] if isinstance(row, tuple) else row.get('user_id')
    if owner_id != user['id']:
        conn.close()
        raise HTTPException(status_code=403, detail="دسترسی ندارید")
    
    # Get messages
    cursor.execute("""
        SELECT id, role, content, image_url, created_at
        FROM chat_history
        WHERE session_id = %s
        ORDER BY created_at ASC
    """, (session_id,))
    
    messages = [dict(row) if hasattr(row, 'keys') else {
        'id': row[0], 'role': row[1], 'content': row[2],
        'image_url': row[3], 'created_at': row[4]
    } for row in cursor.fetchall()]
    
    conn.close()
    return {"messages": messages}


@app.delete("/chat/sessions/{session_id}")
def delete_chat_session(session_id: int, authorization: str = Header(None)):
    """حذف یک مکالمه"""
    if not authorization:
        raise HTTPException(status_code=401, detail="توکن وارد نشده")
    
    token = authorization.replace("Bearer ", "")
    user = auth.get_user_from_token(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM chat_sessions WHERE id = %s AND user_id = %s", (session_id, user['id']))
    conn.commit()
    conn.close()
    
    return {"message": "مکالمه حذف شد"}


# ===== Menu & Restaurant Endpoints =====
# 📌 نکته: endpoint های /api/restaurants در restaurant_api.py هستن


@app.get("/health")
def health():
    return {"status": "healthy", "version": "2.0.0"}


# ===== 🎤 Real-time Voice Chat با Gemini Live API =====

# ذخیره sessions فعال
voice_sessions = {}

@app.websocket("/ws/voice-chat")
async def voice_chat_websocket(websocket: WebSocket):
    """
    🎤🔊 چت صوتی با GapGPT (STT → Chat → TTS)
    
    پروتکل:
    - Client → Server: {"type": "audio", "data": "base64_audio", "mime_type": "audio/webm"}
    - Client → Server: {"type": "text", "data": "متن پیام"}
    - Client → Server: {"type": "end"} برای پایان
    - Server → Client: {"type": "user_text", "data": "متن شناسایی شده"}
    - Server → Client: {"type": "text", "data": "متن پاسخ", "emotion": "happy"}
    - Server → Client: {"type": "audio", "data": "base64_audio", "emotion": "happy"}
    - Server → Client: {"type": "turn_complete"}
    """
    await websocket.accept()
    session_id = str(uuid.uuid4())
    
    print(f"🎤 Voice chat connected: {session_id}")
    
    try:
        # Import here to avoid circular imports
        from voice_chat import VoiceChatSession
        
        # ساخت session جدید
        session = VoiceChatSession()
        connected = await session.connect()
        
        if not connected:
            await websocket.send_json({
                "type": "error",
                "message": "خطا در آماده‌سازی چت صوتی"
            })
            await websocket.close()
            return
        
        voice_sessions[session_id] = session
        
        # ارسال تایید اتصال
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id
        })
        
        # پردازش پیام‌های client
        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type")
                
                if msg_type == "audio":
                    # دریافت صدای کامل و پردازش
                    audio_b64 = data.get("data", "")
                    mime_type = data.get("mime_type", "audio/webm")
                    audio_bytes = base64.b64decode(audio_b64)
                    
                    # پردازش: STT → Chat → TTS
                    async for response in session.process_audio(audio_bytes, mime_type):
                        await websocket.send_json(response)
                    
                elif msg_type == "text":
                    # دریافت متن مستقیم
                    text = data.get("data", "")
                    if text:
                        # Chat → TTS
                        reply = await session.chat(text)
                        await websocket.send_json({
                            "type": "text",
                            "data": reply,
                            "emotion": session.detected_emotion
                        })
                        
                        # تبدیل به صدا
                        audio = await session.text_to_speech(reply)
                        if audio:
                            await websocket.send_json({
                                "type": "audio",
                                "data": base64.b64encode(audio).decode(),
                                "mime_type": "audio/mp3",
                                "emotion": session.detected_emotion
                            })
                        
                        await websocket.send_json({
                            "type": "turn_complete",
                            "emotion": session.detected_emotion
                        })
                        
                elif msg_type == "end":
                    # پایان مکالمه
                    break
                    
        except WebSocketDisconnect:
            print(f"🔴 Voice chat disconnected: {session_id}")
            
    except Exception as e:
        print(f"Voice chat error: {e}")
        traceback.print_exc()
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        # پاکسازی session
        if session_id in voice_sessions:
            await voice_sessions[session_id].close()
            del voice_sessions[session_id]
        try:
            await websocket.close()
        except:
            pass


# Endpoint برای چک کردن وضعیت voice chat
@app.get("/voice-chat/status")
def voice_chat_status():
    """وضعیت سیستم چت صوتی"""
    return {
        "available": True,
        "active_sessions": len(voice_sessions),
        "model": "gemini-2.0-flash-live-001"
    }


# ===== 📹 Video Chat - چت ویدیویی Real-time =====

from video_chat import VideoChatSession, video_sessions, EMOTION_RESPONSES

# ذخیره video sessions
video_chat_sessions = {}


class VideoFrameRequest(BaseModel):
    frame: str  # base64 image
    session_id: Optional[str] = None


class VideoChatRequest(BaseModel):
    message: str
    frame: Optional[str] = None  # base64 image
    session_id: Optional[str] = None


@app.post("/video-chat/start")
async def start_video_chat(authorization: str = Header(None)):
    """
    📹 شروع چت ویدیویی
    یک session جدید ایجاد میکنه
    """
    user_id = None
    if authorization:
        token = authorization.replace("Bearer ", "")
        user = auth.get_user_from_token(token)
        if user:
            user_id = user['id']
    
    session = VideoChatSession(user_id)
    result = await session.start()
    video_chat_sessions[result['session_id']] = session
    
    return {
        "success": True,
        "session_id": result['session_id'],
        "message": "چت ویدیویی شروع شد! 📹"
    }


@app.post("/video-chat/stop/{session_id}")
async def stop_video_chat(session_id: str):
    """📹 پایان چت ویدیویی"""
    session = video_chat_sessions.pop(session_id, None)
    if session:
        result = await session.stop()
        return {"success": True, **result}
    return {"success": False, "error": "Session not found"}


@app.post("/video-chat/analyze")
async def analyze_video_frame(request: VideoFrameRequest):
    """
    📹 تحلیل یک فریم از ویدیو
    - تشخیص چهره و احساس
    - تشخیص محیط
    - پیشنهاد غذا
    """
    session = video_chat_sessions.get(request.session_id)
    
    if not session:
        # ساخت session موقت
        session = VideoChatSession()
        await session.start()
    
    analysis = await session.analyze_frame(request.frame)
    
    return {
        "success": True,
        "analysis": analysis,
        "frame_count": session.frame_count
    }


@app.post("/video-chat/chat")
async def video_chat_message(request: VideoChatRequest, authorization: str = Header(None)):
    """
    📹 چت با context ویدیویی
    - پیام کاربر + فریم فعلی
    - پاسخ متناسب با احساس
    """
    session = video_chat_sessions.get(request.session_id)
    
    if not session:
        # ساخت session جدید
        user_id = None
        if authorization:
            token = authorization.replace("Bearer ", "")
            user = auth.get_user_from_token(token)
            if user:
                user_id = user['id']
        
        session = VideoChatSession(user_id)
        await session.start()
        video_chat_sessions[session.session_id] = session
    
    result = await session.chat_with_context(request.message, request.frame)
    
    return {
        "success": True,
        "session_id": session.session_id,
        **result
    }


@app.websocket("/ws/video-chat")
async def video_chat_websocket(websocket: WebSocket):
    """
    📹🔊 چت ویدیویی Real-time با WebSocket
    
    پروتکل:
    - Client → Server: {"type": "frame", "data": "base64_image"}
    - Client → Server: {"type": "message", "data": "متن پیام", "frame": "base64_image"}
    - Client → Server: {"type": "end"}
    - Server → Client: {"type": "analysis", "data": {...}}
    - Server → Client: {"type": "response", "data": "پاسخ", "emotion": "happy"}
    - Server → Client: {"type": "suggestion", "data": "پیشنهاد غذا"}
    """
    await websocket.accept()
    session_id = str(uuid.uuid4())
    
    print(f"📹 Video chat connected: {session_id}")
    
    try:
        # ساخت session
        session = VideoChatSession()
        await session.start()
        video_chat_sessions[session.session_id] = session
        
        # ارسال تایید اتصال
        await websocket.send_json({
            "type": "connected",
            "session_id": session.session_id,
            "message": "چت ویدیویی آماده است! 📹"
        })
        
        # پردازش پیام‌ها
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "frame":
                # تحلیل فریم
                frame = data.get("data", "")
                if frame:
                    analysis = await session.analyze_frame(frame)
                    await websocket.send_json({
                        "type": "analysis",
                        "data": analysis
                    })
                    
                    # ارسال پیشنهاد غذا
                    if analysis.get("food_suggestion"):
                        await websocket.send_json({
                            "type": "suggestion",
                            "emotion": analysis.get("emotion", "neutral"),
                            "emotion_fa": analysis.get("emotion_fa", "عادی"),
                            "data": analysis.get("food_suggestion")
                        })
                    
                    # 📢 اگه احساس عوض شده، پیام خاص بفرست
                    if analysis.get("emotion_changed") and analysis.get("emotion_message"):
                        await websocket.send_json({
                            "type": "emotion_change",
                            "message": analysis.get("emotion_message"),
                            "from_emotion": session.last_emotion_change.get("from") if session.last_emotion_change else None,
                            "to_emotion": analysis.get("emotion")
                        })
            
            elif msg_type == "message":
                # چت متنی با context
                message = data.get("data", "")
                frame = data.get("frame")
                
                if message:
                    result = await session.chat_with_context(message, frame)
                    await websocket.send_json({
                        "type": "response",
                        "data": result.get("response", ""),
                        "emotion": result.get("emotion", "neutral"),
                        "emotion_fa": result.get("emotion_fa", "عادی"),
                        "tone": result.get("tone", ""),
                        "learned": result.get("learned", []),
                        "message_count": result.get("message_count", 0)
                    })
            
            elif msg_type == "audio":
                # 🎤 چت صوتی - دریافت صدا، تبدیل به متن، و پاسخ
                audio = data.get("data", "")
                frame = data.get("frame")
                mime_type = data.get("mime_type", "audio/webm")
                
                if audio:
                    result = await session.transcribe_and_chat(audio, frame, mime_type)
                    
                    # ارسال متن تشخیص داده شده
                    if result.get("transcribed_text"):
                        await websocket.send_json({
                            "type": "transcription",
                            "data": result.get("transcribed_text"),
                            "audio_emotion": result.get("audio_emotion", "neutral")
                        })
                    
                    # ارسال پاسخ
                    await websocket.send_json({
                        "type": "response",
                        "data": result.get("response", ""),
                        "emotion": result.get("emotion", "neutral"),
                        "emotion_fa": result.get("emotion_fa", "عادی"),
                        "tone": result.get("tone", ""),
                        "learned": result.get("learned", []),
                        "message_count": result.get("message_count", 0)
                    })
            
            elif msg_type == "end":
                # ارسال خلاصه session قبل از بستن
                summary = await session.stop()
                await websocket.send_json({
                    "type": "session_summary",
                    "data": summary
                })
                break
                
    except WebSocketDisconnect:
        print(f"📹 Video chat disconnected: {session_id}")
    except Exception as e:
        print(f"📹 Video chat error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        # پاکسازی
        if session_id in video_chat_sessions:
            await video_chat_sessions[session_id].stop()
            del video_chat_sessions[session_id]
        try:
            await websocket.close()
        except:
            pass


@app.get("/video-chat/status")
def video_chat_status():
    """📹 وضعیت سیستم چت ویدیویی"""
    return {
        "available": True,
        "active_sessions": len(video_chat_sessions),
        "emotions": list(EMOTION_RESPONSES.keys()),
        "model": "gemini-2.5-flash"
    }


if __name__ == "__main__":
    import uvicorn
    import socket
    
    # پیدا کردن IP واقعی
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "localhost"
    
    local_ip = get_local_ip()
    
    # بررسی وجود SSL certificates
    ssl_keyfile = "key.pem" if os.path.exists("key.pem") else None
    ssl_certfile = "cert.pem" if os.path.exists("cert.pem") else None
    use_ssl = ssl_keyfile and ssl_certfile
    protocol = "https" if use_ssl else "http"
    
    print("\n" + "="*50)
    print("   🌟 روژان API Server")
    print("="*50)
    print(f"\n💻 Local: {protocol}://localhost:9999")
    print(f"📱 Network: {protocol}://{local_ip}:9999")
    if use_ssl:
        print("🔒 SSL: Enabled")
    print("\n" + "="*50 + "\n")
    
    if use_ssl:
        uvicorn.run(app, host="0.0.0.0", port=9999, log_level="warning",
                    ssl_keyfile=ssl_keyfile, ssl_certfile=ssl_certfile)
    else:
        uvicorn.run(app, host="0.0.0.0", port=9999, log_level="warning")

