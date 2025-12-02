"""
🎤🔊 چت صوتی سریع با GapGPT
STT (Whisper) → Chat (Gemini Lite) → TTS (OpenAI)
بهینه‌شده برای سرعت
"""

import asyncio
import base64
import json
import httpx
from typing import Optional, AsyncGenerator
from config import GAPGPT_API_KEY, GAPGPT_BASE_URL

# مدل‌های سریع
STT_MODEL = "whisper-1"
CHAT_MODEL = "gemini-2.5-flash-lite"  # سریع‌ترین مدل چت
TTS_MODEL = "tts-1"  # سریع‌ترین TTS
TTS_VOICE = "nova"  # صدای زن، طبیعی

# تنظیمات TTS بر اساس احساس
EMOTION_TTS_CONFIG = {
    "happy": {"rate": "+10%", "pitch": "+5Hz", "fa": "خوشحال", "tone": "شاد و پرانرژی"},
    "sad": {"rate": "-15%", "pitch": "-5Hz", "fa": "غمگین", "tone": "همدردانه و آرام"},
    "angry": {"rate": "-10%", "pitch": "-3Hz", "fa": "عصبانی", "tone": "آرامش‌بخش و صبورانه"},
    "anxious": {"rate": "-5%", "pitch": "+0Hz", "fa": "مضطرب", "tone": "اطمینان‌بخش"},
    "tired": {"rate": "-20%", "pitch": "-5Hz", "fa": "خسته", "tone": "ملایم و کوتاه"},
    "excited": {"rate": "+15%", "pitch": "+8Hz", "fa": "هیجان‌زده", "tone": "پرانرژی"},
    "hurry": {"rate": "+20%", "pitch": "+0Hz", "fa": "عجله", "tone": "مختصر و سریع"},
    "neutral": {"rate": "+0%", "pitch": "+0Hz", "fa": "خنثی", "tone": "عادی"},
}

# System Prompt با قابلیت تشخیص احساس
SYSTEM_PROMPT = """تو روژان هستی، دستیار صوتی هوشمند رستوران.

قوانین مهم:
1. فارسی محاوره‌ای و صمیمی صحبت کن
2. جواب‌هات کوتاه و مفید باشن (برای مکالمه صوتی)
3. از لحن صدای کاربر احساسش رو درک کن و متناسب جواب بده:
   - اگه عصبانی بود: آروم و صبورانه جواب بده
   - اگه خسته بود: کوتاه و سریع جواب بده
   - اگه خوشحال بود: پرانرژی جواب بده
   - اگه عجله داشت: مستقیم و بدون حاشیه جواب بده
4. اول احساس کاربر رو در یک کلمه بگو، بعد جواب اصلی رو بده

وظایفت:
- کمک به انتخاب غذا
- پیشنهاد بر اساس سلیقه
- پاسخ به سوالات درباره منو
"""


class VoiceChatSession:
    """چت صوتی سریع: STT → Chat → TTS"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or GAPGPT_API_KEY
        self.client = httpx.AsyncClient(timeout=30.0, verify=False)
        self.is_connected = False
        self.detected_emotion = "neutral"
        self.chat_history = []
        
    async def connect(self):
        """آماده‌سازی session"""
        self.is_connected = True
        self.chat_history = []
        print("✅ Voice chat session ready (Fast Mode)")
        return True
    
    async def transcribe(self, audio_data: bytes, mime_type: str = "audio/webm") -> str:
        """STT با Whisper - سریع"""
        try:
            import tempfile, os
            ext = "webm" if "webm" in mime_type else "mp3"
            
            with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
                tmp.write(audio_data)
                tmp_path = tmp.name
            
            try:
                url = f"{GAPGPT_BASE_URL}v1/audio/transcriptions"
                with open(tmp_path, "rb") as f:
                    files = {"file": (f"audio.{ext}", f, mime_type)}
                    data = {"model": STT_MODEL, "language": "fa"}
                    headers = {"Authorization": f"Bearer {self.api_key}"}
                    
                    response = await self.client.post(url, files=files, data=data, headers=headers)
                    
                    if response.status_code == 200:
                        return response.json().get("text", "")
                    print(f"STT error: {response.status_code}")
                    return ""
            finally:
                os.unlink(tmp_path)
                
        except Exception as e:
            print(f"Transcribe error: {e}")
            return ""
    
    async def chat(self, text: str) -> str:
        """Chat با Gemini Lite - سریع"""
        try:
            url = f"{GAPGPT_BASE_URL}v1beta/models/{CHAT_MODEL}:generateContent"
            
            self.chat_history.append({"role": "user", "parts": [{"text": text}]})
            
            # فقط آخرین 6 پیام برای سرعت
            recent_history = self.chat_history[-6:]
            
            payload = {
                "contents": recent_history,
                "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 200  # پاسخ کوتاه = سریع‌تر
                }
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = await self.client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                if "candidates" in result and result["candidates"]:
                    reply = result["candidates"][0]["content"]["parts"][0]["text"]
                    
                    # تشخیص احساس
                    for emotion in EMOTION_TTS_CONFIG.keys():
                        if EMOTION_TTS_CONFIG[emotion]["fa"] in reply[:50]:
                            self.detected_emotion = emotion
                            break
                    
                    self.chat_history.append({"role": "model", "parts": [{"text": reply}]})
                    return reply
            
            print(f"Chat error: {response.status_code} - {response.text[:200]}")
            return "متأسفم، مشکلی پیش اومد."
            
        except Exception as e:
            print(f"Chat error: {e}")
            return "خطا در ارتباط"
    
    async def text_to_speech(self, text: str) -> bytes:
        """TTS با OpenAI - سریع‌ترین"""
        try:
            url = f"{GAPGPT_BASE_URL}v1/audio/speech"
            
            payload = {
                "model": TTS_MODEL,
                "input": text,
                "voice": TTS_VOICE,
                "speed": 1.1  # کمی سریع‌تر
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = await self.client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                return response.content
            
            print(f"TTS error: {response.status_code}")
            return b""
            
        except Exception as e:
            print(f"TTS error: {e}")
            return b""
    
    async def process_audio(self, audio_data: bytes, mime_type: str = "audio/webm") -> AsyncGenerator:
        """پردازش کامل: صدا → متن → پاسخ → صدا"""
        if not self.is_connected:
            yield {"type": "error", "message": "Not connected"}
            return
        
        try:
            # 1. STT
            user_text = await self.transcribe(audio_data, mime_type)
            if not user_text:
                yield {"type": "error", "message": "نتونستم صداتو بفهمم"}
                return
            
            yield {"type": "user_text", "data": user_text}
            
            # 2. Chat
            reply = await self.chat(user_text)
            yield {
                "type": "text",
                "data": reply,
                "emotion": self.detected_emotion
            }
            
            # 3. TTS
            audio = await self.text_to_speech(reply)
            if audio:
                yield {
                    "type": "audio",
                    "data": base64.b64encode(audio).decode(),
                    "mime_type": "audio/mp3",
                    "emotion": self.detected_emotion
                }
            
            yield {"type": "turn_complete", "emotion": self.detected_emotion}
            
        except Exception as e:
            print(f"Process audio error: {e}")
            yield {"type": "error", "message": str(e)}
    
    async def close(self):
        """بستن session"""
        await self.client.aclose()
        self.is_connected = False
        self.chat_history = []
        print("🔴 Session closed")


# مدیریت sessions
active_sessions = {}

async def create_session(session_id: str, api_key: str = None) -> VoiceChatSession:
    """ساخت یک session جدید"""
    session = VoiceChatSession(api_key)
    if await session.connect():
        active_sessions[session_id] = session
        return session
    return None

async def get_session(session_id: str) -> Optional[VoiceChatSession]:
    """گرفتن session موجود"""
    return active_sessions.get(session_id)

async def close_session(session_id: str):
    """بستن و حذف session"""
    if session_id in active_sessions:
        await active_sessions[session_id].close()
        del active_sessions[session_id]


# تست
if __name__ == "__main__":
    async def test():
        session = VoiceChatSession()
        if await session.connect():
            await session.send_text("سلام، حالت چطوره؟")
            async for response in session.receive():
                print(response)
            await session.close()
    
    asyncio.run(test())
