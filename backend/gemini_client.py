"""
🤖 روژان - اتصال به Gemini از طریق GapGPT
"""
import requests
import base64
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import get_current_key, switch_to_next_key, GEMINI_API_KEYS, GAPGPT_API_KEY, GAPGPT_BASE_URL

# ═══════════════════════════════════════════════════════════════════════════════
# 🔷 GapGPT Client (اولویت اول)
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from google.genai import types, Client
    gapgpt_client = Client(
        api_key=GAPGPT_API_KEY,
        http_options=types.HttpOptions(base_url=GAPGPT_BASE_URL)
    )
    USE_GAPGPT = True
    print("✅ GapGPT آماده!")
except Exception as e:
    print(f"⚠️ GapGPT init error: {e}")
    gapgpt_client = None
    USE_GAPGPT = False

# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 مدل‌های بهینه روژان (آپدیت شده)
# ═══════════════════════════════════════════════════════════════════════════════
CHAT_MODEL = "gemini-2.5-flash"              # چت اصلی - سریع و هوشمند
VISION_MODEL = "gemini-3-pro-image-preview"  # 🆕 تحلیل تصویر - جدیدتر و دقیق‌تر
AUDIO_MODEL = "gemini-2.5-flash"             # تبدیل صدا به متن
SMART_MODEL = "gemini-2.5-pro"               # یادگیری هوشمند (AI Provider)
TTS_MODEL = "gemini-2.5-flash-preview-tts"   # 🆕 TTS فارسی با Gemini

# GapGPT API
GAPGPT_API_URL = "https://api.gapgpt.app/v1beta/models"

# بکاپ - Direct Google API
MODEL = CHAT_MODEL
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

session = requests.Session()
retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry)
session.mount('https://', adapter)

print(f"✅ Gemini آماده! ({len(GEMINI_API_KEYS)} کلید بکاپ)")

# System Prompt برای روژان
SYSTEM_PROMPT = """تو روژان هستی، دستیار هوشمند رستوران.

قوانین مهم:
1. روند فکر کردنت رو نشون بده
2. اول تحلیل کن، بعد پیشنهاد بده
3. فارسی محاوره‌ای صحبت کن
4. اگه اطلاعاتی نداری، سوال بپرس

وظایفت:
- کمک به انتخاب غذا
- پیشنهاد بر اساس سلیقه مشتری
- پاسخ به سوالات درباره منو
"""


def chat(message: str, image: str = None, show_thinking: bool = False) -> dict:
    """
    چت با Gemini (متن + تصویر)
    اول GapGPT، بعد Direct API
    
    Returns:
        dict: {"response": "پاسخ", "thinking": "روند فکر کردن"} یا فقط str
    """
    global USE_GAPGPT
    
    # ═══════════════════════════════════════════════════════════════
    # روش ۱: GapGPT API (با requests - پایدارتر)
    # ═══════════════════════════════════════════════════════════════
    if USE_GAPGPT:
        try:
            # اگه thinking خواست، از مدل Pro استفاده کن
            if show_thinking:
                model = "gemini-2.5-pro"
            else:
                model = VISION_MODEL if image else CHAT_MODEL
                
            url = f"{GAPGPT_API_URL}/{model}:generateContent"
            headers = {
                "Authorization": f"Bearer {GAPGPT_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # پرامپت با دستور نشان دادن فکر
            if show_thinking:
                thinking_prompt = """قبل از پاسخ دادن، مراحل فکر کردنت رو نشون بده:

<thinking>
[اینجا روند تحلیل و فکر کردنت رو بنویس]
</thinking>

<response>
[اینجا پاسخ نهایی رو بنویس]
</response>

"""
                full_message = thinking_prompt + SYSTEM_PROMPT + "\n\n" + message
            else:
                full_message = SYSTEM_PROMPT + "\n\n" + message
            
            # ساخت parts
            parts = [{"text": full_message}]
            
            # تصویر (اگه داشت)
            if image:
                if "," in image:
                    image = image.split(",")[1]
                parts.append({
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image
                    }
                })
            
            data = {"contents": [{"parts": parts}]}
            response = session.post(url, headers=headers, json=data, timeout=90)
            
            if response.ok:
                result = response.json()
                text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                
                # پارس thinking و response
                if show_thinking:
                    return _parse_thinking_response(text)
                return text
                
        except Exception as e:
            print(f"⚠️ GapGPT error: {e}, switching to direct API")
            USE_GAPGPT = False
    
    # ═══════════════════════════════════════════════════════════════
    # روش ۲: Direct API (بکاپ)
    # ═══════════════════════════════════════════════════════════════
    max_retries = len(GEMINI_API_KEYS)
    
    for attempt in range(max_retries):
        try:
            api_key = get_current_key()
            url = f"{API_URL}?key={api_key}"
            
            parts = []
            if message:
                parts.append({"text": message})
            
            if image:
                if "," in image:
                    image = image.split(",")[1]
                parts.append({
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image
                    }
                })
            
            data = {
                "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "contents": [{"parts": parts}]
            }
            
            response = session.post(url, json=data, timeout=30)
            
            if response.status_code in [429, 403]:
                switch_to_next_key()
                continue
            
            if response.status_code != 200:
                return f"خطا: {response.status_code}"
            
            result = response.json()
            if 'candidates' not in result or not result['candidates']:
                return "متأسفم، نتونستم پردازش کنم."
            return result['candidates'][0]['content']['parts'][0]['text'].strip()
            
        except Exception as e:
            print(f"Direct API error: {e}")
            switch_to_next_key()
            continue
    
    return "❌ همه کلیدها مشکل دارن!"


def transcribe(audio_base64: str, mime_type: str = "audio/webm", detect_emotion: bool = False) -> dict:
    """
    تبدیل صدا به متن + تشخیص احساس با Gemini
    
    Returns:
        dict: {"text": "متن", "emotion": "happy/sad/angry/neutral/..."}
    """
    global USE_GAPGPT
    
    if detect_emotion:
        transcribe_prompt = """این یک فایل صوتی فارسی است. لطفاً:
1. متن گفته‌شده را دقیق بنویس
2. احساس گوینده را از لحن صدا تشخیص بده

خروجی فقط JSON باشه:
{"text": "متن گفته شده", "emotion": "happy/sad/angry/excited/neutral/tired/stressed/calm", "confidence": 0.0-1.0}"""
    else:
        transcribe_prompt = "این یک فایل صوتی فارسی است. لطفاً دقیقاً متن گفته‌شده را بنویس. فقط متن، بدون هیچ توضیح اضافه‌ای."
    
    # ═══════════════════════════════════════════════════════════════
    # روش ۱: GapGPT API (با requests)
    # ═══════════════════════════════════════════════════════════════
    if USE_GAPGPT:
        try:
            url = f"{GAPGPT_API_URL}/{AUDIO_MODEL}:generateContent"
            headers = {
                "Authorization": f"Bearer {GAPGPT_API_KEY}",
                "Content-Type": "application/json"
            }
            
            data = {
                "contents": [{
                    "parts": [
                        {"text": transcribe_prompt},
                        {"inline_data": {"mime_type": mime_type, "data": audio_base64}}
                    ]
                }]
            }
            
            response = session.post(url, headers=headers, json=data, timeout=60)
            
            if response.ok:
                result = response.json()
                text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                return _parse_transcribe_result(text, detect_emotion)
                
        except Exception as e:
            print(f"⚠️ GapGPT transcribe error: {e}")
            USE_GAPGPT = False
    
    # ═══════════════════════════════════════════════════════════════
    # روش ۲: Direct API (بکاپ)
    # ═══════════════════════════════════════════════════════════════
    max_retries = len(GEMINI_API_KEYS)
    
    for attempt in range(max_retries):
        try:
            api_key = get_current_key()
            url = f"{API_URL}?key={api_key}"
            
            data = {
                "contents": [{
                    "parts": [
                        {"text": transcribe_prompt},
                        {"inline_data": {"mime_type": mime_type, "data": audio_base64}}
                    ]
                }]
            }
            
            response = session.post(url, json=data, timeout=60)
            
            if response.status_code in [429, 403]:
                switch_to_next_key()
                continue
            
            if response.status_code != 200:
                return {"text": "", "emotion": None} if detect_emotion else ""
            
            result = response.json()
            text = result['candidates'][0]['content']['parts'][0]['text'].strip()
            return _parse_transcribe_result(text, detect_emotion)
            
        except Exception as e:
            switch_to_next_key()
            continue
    
    return {"text": "", "emotion": None} if detect_emotion else ""


def _parse_transcribe_result(text: str, detect_emotion: bool) -> dict:
    """پارس نتیجه transcribe"""
    import json
    
    if not detect_emotion:
        return text
    
    # تلاش برای پارس JSON
    try:
        # حذف ```json و ``` اگه بود
        clean = text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)
        return {
            "text": data.get("text", ""),
            "emotion": data.get("emotion", "neutral"),
            "confidence": data.get("confidence", 0.5)
        }
    except:
        # اگه JSON نبود، فقط متن برگردون
        return {"text": text, "emotion": "neutral", "confidence": 0.3}


def _parse_thinking_response(text: str) -> dict:
    """پارس thinking و response از پاسخ AI"""
    import re
    
    thinking = ""
    response = text
    
    # استخراج thinking
    thinking_match = re.search(r'<thinking>(.*?)</thinking>', text, re.DOTALL)
    if thinking_match:
        thinking = thinking_match.group(1).strip()
    
    # استخراج response
    response_match = re.search(r'<response>(.*?)</response>', text, re.DOTALL)
    if response_match:
        response = response_match.group(1).strip()
    else:
        # اگه تگ response نبود، بقیه متن بعد از thinking
        if thinking_match:
            response = text[thinking_match.end():].strip()
            # حذف تگ‌های اضافی
            response = re.sub(r'</?response>', '', response).strip()
    
    return {
        "response": response,
        "thinking": thinking
    }


# تست
if __name__ == "__main__":
    print("\n🧪 تست چت با Gemini:")
    response = chat("سلام! خوبی؟")
    print(f"پاسخ: {response}")

