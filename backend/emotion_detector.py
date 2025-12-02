"""
🎭 تشخیص احساسات مشتری از چت
با AI (Gemini) + فال‌بک Rule-Based
"""

import json
import requests
from datetime import datetime
from config import GAPGPT_API_KEY

# مدل سریع برای تشخیص احساس
EMOTION_MODEL = "gemini-2.5-flash-lite"


def detect_emotion(message: str, use_ai: bool = True) -> dict:
    """
    تشخیص احساس از پیام
    فقط با AI (بدون فال‌بک rule-based)
    """
    
    # 🤖 تشخیص با AI
    if use_ai:
        ai_result = detect_emotion_ai(message)
        if ai_result:
            return ai_result
    
    # اگر AI خطا داد، neutral برگردون (بدون rule-based)
    return {
        "emotions": [],
        "primary_emotion": {"emotion": "neutral", "score": 0.5, "intensity": 0.5},
        "satisfaction": "neutral",
        "timestamp": datetime.now().isoformat(),
        "method": "default"
    }


def detect_emotion_ai(message: str) -> dict:
    """
    🤖 تشخیص احساس با Gemini AI
    درک عمیق context، کنایه، لحن
    """
    try:
        prompt = f'''احساس این پیام فارسی رو تحلیل کن.

پیام: "{message}"

خروجی فقط JSON (بدون توضیح):
{{
    "emotion": "happy/sad/angry/hungry/hurry/confused/excited/disappointed/tired/stressed/neutral",
    "score": 0.0-1.0,
    "intensity": 0.0-1.0,
    "satisfaction": "high/medium/low/neutral",
    "is_sarcastic": false,
    "needs_urgent_response": false,
    "secondary_emotions": ["emotion1", "emotion2"]
}}'''

        response = requests.post(
            f"https://api.gapgpt.app/v1beta/models/{EMOTION_MODEL}:generateContent",
            headers={
                "Authorization": f"Bearer {GAPGPT_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 200
                }
            },
            timeout=5  # سریع باشه
        )
        
        if response.ok:
            text = response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            
            # پارس JSON
            if "```" in text:
                text = text.split("```")[1].replace("json", "").strip()
            
            data = json.loads(text)
            
            print(f"  🤖 AI Emotion: {data.get('emotion')} (score: {data.get('score', 0):.2f})")
            
            return {
                "emotions": [
                    {"emotion": data.get("emotion", "neutral"), "score": data.get("score", 0.5), "intensity": data.get("intensity", 0.5)}
                ] + [{"emotion": e, "score": 0.3, "intensity": 0.3} for e in data.get("secondary_emotions", [])[:2]],
                "primary_emotion": {
                    "emotion": data.get("emotion", "neutral"),
                    "score": data.get("score", 0.5),
                    "intensity": data.get("intensity", 0.5)
                },
                "satisfaction": data.get("satisfaction", "neutral"),
                "is_sarcastic": data.get("is_sarcastic", False),
                "needs_urgent_response": data.get("needs_urgent_response", False),
                "timestamp": datetime.now().isoformat(),
                "method": "ai"
            }
            
    except Exception as e:
        print(f"  ⚠️ AI emotion error: {e}, using rules...")
    
    return None


def get_empathy_response(emotion: str) -> str:
    """
    پاسخ همدلانه بر اساس احساس
    """
    responses = {
        "happy": "خوشحالم که راضی هستی! 😊",
        "angry": "متوجه ناراحتیت هستم. چطور می‌تونم کمکت کنم؟",
        "sad": "متأسفم که این حس رو داری. بذار کمکت کنم.",
        "hungry": "گرسنگی بدترین حسه! بذار سریع یه غذای خوب پیشنهاد بدم 🍕",
        "hurry": "متوجهم که عجله داری! سریع‌ترین گزینه‌ها رو بهت میگم ⚡",
        "confused": "نگران نباش، کمکت می‌کنم انتخاب کنی 🤝",
        "excited": "چه هیجانی! منم خوشحالم! 🎉",
        "disappointed": "متأسفم که انتظاراتت برآورده نشده. چطور می‌تونم جبران کنم؟",
        "neutral": ""
    }
    return responses.get(emotion, "")


# ذخیره در پروفایل
def learn_emotion(user_id: int, message: str) -> dict:
    """
    یادگیری احساس و ذخیره در پروفایل
    """
    import db
    
    result = detect_emotion(message)
    
    # گرفتن پروفایل فعلی
    profile = db.get_customer_profile(user_id)
    if profile:
        extra_data = profile.get('extra_data', {})
        if isinstance(extra_data, str):
            import json
            extra_data = json.loads(extra_data) if extra_data else {}
        
        # ذخیره آخرین احساس (حتی اگر neutral باشد)
        extra_data['last_emotion'] = result['primary_emotion']['emotion']
        extra_data['last_emotion_time'] = result['timestamp']
        extra_data['satisfaction_level'] = result['satisfaction']
        
        # تاریخچه احساسات (آخرین 10 تا)
        emotion_history = extra_data.get('emotion_history', [])
        emotion_history.append({
            "emotion": result['primary_emotion']['emotion'],
            "time": result['timestamp']
        })
        extra_data['emotion_history'] = emotion_history[-10:]
        
        # آپدیت پروفایل
        import json
        db.update_customer_profile(user_id, extra_data=json.dumps(extra_data, ensure_ascii=False))
        
        print(f"  🎭 Emotion: {result['primary_emotion']['emotion']} (score: {result['primary_emotion']['score']:.2f})")
    
    return result


# تست
if __name__ == "__main__":
    test_messages = [
        "سلام، خیلی گرسنمه!",
        "غذاتون عالی بود، ممنون 😊",
        "چرا اینقدر دیر رسید؟ عصبانی شدم",
        "نمیدونم چی بگیرم، کمکم کن",
        "عجله دارم، سریع‌ترین غذا چیه؟",
        # تست‌های پیشرفته (نیاز به AI)
        "واقعاً که! چه سرویس عالی‌ای!",  # کنایه
        "دیگه حوصله ندارم از بس منتظر موندم",  # خستگی + ناامیدی
        "باورم نمیشه این همه پول دادم برای این؟!",  # ناراحتی پنهان
    ]
    
    print("🎭 تست تشخیص احساسات با AI:\n")
    for msg in test_messages:
        result = detect_emotion(msg)
        method = result.get('method', 'unknown')
        print(f"📝 '{msg}'")
        print(f"   → [{method}] {result['primary_emotion']['emotion']} (score: {result['primary_emotion']['score']:.2f})")
        print(f"   → رضایت: {result['satisfaction']}")
        if result.get('is_sarcastic'):
            print(f"   → ⚠️ کنایه تشخیص داده شد!")
        if result.get('needs_urgent_response'):
            print(f"   → 🚨 نیاز به پاسخ فوری!")
        empathy = get_empathy_response(result['primary_emotion']['emotion'])
        if empathy:
            print(f"   → پاسخ: {empathy}")
        print()

