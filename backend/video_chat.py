"""
📹 Video Chat - چت ویدیویی Real-time با Gemini
تعامل ویدیویی مداوم با AI که چهره و احساس کاربر رو می‌بینه

ویژگی‌ها:
- استریم ویدیو از دوربین کاربر
- تحلیل real-time چهره و احساس
- پاسخ صوتی/متنی متناسب با حال کاربر
- پیشنهاد غذا بر اساس احساس
- 🧠 یادگیری هوشمند از مکالمات ویدیویی
- 🎤 چت صوتی مداوم
"""

import asyncio
import base64
import json
from datetime import datetime
from typing import Optional, Dict, AsyncGenerator, List
import requests
from config import GAPGPT_API_KEY
import smart_learner  # 🧠 یادگیری هوشمند

# مدل برای تحلیل ویدیو (آپدیت شده)
VIDEO_MODEL = "gemini-live-2.5-flash-preview"  # 🆕 بهتر برای real-time
VISION_MODEL = "gemini-3-pro-image-preview"    # 🆕 تحلیل تصویر دقیق‌تر

# تنظیمات احساس
EMOTION_RESPONSES = {
    "happy": {
        "fa": "خوشحال",
        "response_tone": "پرانرژی و شاد",
        "food_suggestion": "یه غذای جشنی مثل پیتزا یا برگر چطوره؟ 🎉"
    },
    "sad": {
        "fa": "غمگین",
        "response_tone": "همدردانه و مهربان",
        "food_suggestion": "یه سوپ گرم یا شکلات داغ حالتو خوب میکنه 🤗"
    },
    "angry": {
        "fa": "عصبانی", 
        "response_tone": "آرام و صبورانه",
        "food_suggestion": "یه نوشیدنی خنک بزن آروم شی 🧊"
    },
    "surprised": {
        "fa": "متعجب",
        "response_tone": "هیجان‌زده",
        "food_suggestion": "امروز یه چیز جدید امتحان کن! 🌟"
    },
    "fearful": {
        "fa": "نگران",
        "response_tone": "اطمینان‌بخش",
        "food_suggestion": "یه چای گرم با کیک آرومت میکنه ☕"
    },
    "disgusted": {
        "fa": "ناراحت",
        "response_tone": "درک‌کننده",
        "food_suggestion": "یه غذای ساده و سبک چطوره؟"
    },
    "neutral": {
        "fa": "عادی",
        "response_tone": "دوستانه",
        "food_suggestion": "چی میل داری امروز؟ 😊"
    }
}

# System Prompt برای تحلیل ویدیو
VIDEO_ANALYSIS_PROMPT = """تو روژان هستی، دستیار هوشمند رستوران که داره ویدیوی کاربر رو می‌بینه.

وظیفه‌ات:
1. احساس کاربر رو از چهره‌اش تشخیص بده (happy, sad, angry, surprised, fearful, disgusted, neutral)
2. سن تقریبی و جنسیت رو حدس بزن
3. محیط رو توصیف کن (خونه، دفتر، بیرون)
4. اگه غذایی در تصویر هست، توضیح بده

خروجی JSON:
{
    "emotion": "happy/sad/angry/...",
    "emotion_confidence": 0.0-1.0,
    "age_range": "20-30",
    "gender": "male/female",
    "environment": "home/office/outdoor/restaurant",
    "food_visible": true/false,
    "food_description": "توضیح غذا اگه هست",
    "face_count": 1,
    "suggestion": "پیشنهاد غذا بر اساس احساس"
}
"""

CHAT_WITH_VIDEO_PROMPT = """تو روژان هستی، دستیار هوشمند رستوران.
الان داری با کاربر ویدیو چت می‌کنی و چهره‌اش رو می‌بینی.

اطلاعات از تصویر:
- احساس کاربر: {emotion} ({emotion_fa})
- محیط: {environment}

قوانین:
1. متناسب با احساس کاربر جواب بده
2. فارسی محاوره‌ای صحبت کن
3. کوتاه و مفید باش (برای مکالمه ویدیویی)
4. اگه غمگین یا عصبانیه، همدردی کن

پیام کاربر: {message}
"""


class VideoChatSession:
    """
    یک session چت ویدیویی مداوم با یادگیری
    
    قابلیت‌ها:
    - مکالمه مداوم با حفظ context
    - یادگیری هوشمند از چت
    - تحلیل احساس real-time
    - تشخیص تغییر احساس
    """
    
    def __init__(self, user_id: int = None):
        self.user_id = user_id
        self.session_id = None
        self.is_active = False
        self.current_emotion = "neutral"
        self.emotion_history: List[Dict] = []
        self.frame_count = 0
        self.last_analysis = None
        self.api_url = "https://api.gapgpt.app/v1beta/models"
        
        # 🧠 مکالمه مداوم
        self.conversation_history: List[Dict] = []
        self.max_history = 20  # حداکثر تاریخچه
        self.learned_info: List[str] = []  # اطلاعات یاد گرفته شده
        
        # 📊 آمار session
        self.start_time = None
        self.message_count = 0
        self.emotion_changes = 0
        self.last_emotion_change = None
        
    async def start(self):
        """شروع session"""
        self.is_active = True
        self.start_time = datetime.now()
        self.session_id = f"video_{self.user_id or 'guest'}_{self.start_time.strftime('%Y%m%d%H%M%S')}"
        
        # پیام خوش‌آمدگویی بر اساس پروفایل کاربر
        welcome = "سلام! 👋 من روژان هستم و دارم می‌بینمت!"
        
        if self.user_id:
            try:
                profile_summary = smart_learner.get_profile_summary(self.user_id)
                if profile_summary:
                    welcome += f"\n{profile_summary[:100]}..."
            except:
                pass
        
        self.conversation_history.append({
            "role": "assistant",
            "content": welcome,
            "timestamp": datetime.now().isoformat()
        })
        
        print(f"📹 Video chat started: {self.session_id}")
        return {
            "session_id": self.session_id, 
            "status": "started",
            "welcome": welcome
        }
    
    async def stop(self):
        """پایان session با خلاصه یادگیری"""
        self.is_active = False
        duration = (datetime.now() - self.start_time).seconds if self.start_time else 0
        
        print(f"📹 Video chat stopped: {self.session_id}")
        
        # 🧠 یادگیری نهایی از کل مکالمه
        if self.user_id and self.conversation_history:
            try:
                # ترکیب همه پیام‌های کاربر
                user_messages = " ".join([
                    msg["content"] for msg in self.conversation_history 
                    if msg["role"] == "user"
                ])
                if user_messages:
                    learn_result = smart_learner.learn_from_chat(self.user_id, user_messages)
                    if learn_result.get("learned"):
                        self.learned_info.extend(learn_result.get("categories", []))
                        print(f"  🧠 Final learning: {learn_result.get('categories', [])}")
            except Exception as e:
                print(f"  ⚠️ Final learning error: {e}")
        
        # خلاصه احساسات
        emotion_summary = {}
        for e in self.emotion_history:
            emotion = e.get("emotion", "neutral")
            emotion_summary[emotion] = emotion_summary.get(emotion, 0) + 1
        
        dominant = max(emotion_summary, key=emotion_summary.get) if emotion_summary else "neutral"
        
        return {
            "session_id": self.session_id,
            "status": "stopped",
            "duration_seconds": duration,
            "message_count": self.message_count,
            "frames_analyzed": self.frame_count,
            "dominant_emotion": dominant,
            "emotion_changes": self.emotion_changes,
            "emotion_summary": emotion_summary,
            "learned_categories": list(set(self.learned_info))
        }
    
    async def analyze_frame(self, frame_base64: str) -> Dict:
        """
        تحلیل یک فریم از ویدیو
        
        Args:
            frame_base64: تصویر به صورت base64
            
        Returns:
            dict با اطلاعات تحلیل
        """
        if not self.is_active:
            return {"error": "Session not active"}
        
        self.frame_count += 1
        
        try:
            # حذف prefix اگه داره
            if "," in frame_base64:
                frame_base64 = frame_base64.split(",")[1]
            
            # درخواست به Gemini Vision
            url = f"{self.api_url}/{VISION_MODEL}:generateContent"
            headers = {
                "Authorization": f"Bearer {GAPGPT_API_KEY}",
                "Content-Type": "application/json"
            }
            
            data = {
                "contents": [{
                    "parts": [
                        {"text": VIDEO_ANALYSIS_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": frame_base64
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 500
                }
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            if response.ok:
                result = response.json()
                text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                
                # پارس JSON از پاسخ
                try:
                    # پیدا کردن JSON در متن
                    import re
                    json_match = re.search(r'\{.*\}', text, re.DOTALL)
                    if json_match:
                        analysis = json.loads(json_match.group())
                    else:
                        analysis = {"emotion": "neutral", "error": "No JSON found"}
                except json.JSONDecodeError:
                    analysis = {"emotion": "neutral", "raw_response": text}
                
                # ذخیره احساس
                emotion = analysis.get("emotion", "neutral")
                prev_emotion = self.current_emotion
                
                # تشخیص تغییر احساس
                emotion_changed = prev_emotion != emotion
                if emotion_changed:
                    self.emotion_changes += 1
                    self.last_emotion_change = {
                        "from": prev_emotion,
                        "to": emotion,
                        "timestamp": datetime.now().isoformat()
                    }
                    print(f"  😊→😢 Emotion changed: {prev_emotion} → {emotion}")
                
                self.current_emotion = emotion
                self.emotion_history.append({
                    "emotion": emotion,
                    "confidence": analysis.get("emotion_confidence", 0.5),
                    "timestamp": datetime.now().isoformat()
                })
                self.last_analysis = analysis
                
                # 🧠 یادگیری از تصویر (اگه کاربر لاگین باشه)
                if self.user_id and self.frame_count % 5 == 0:  # هر 5 فریم
                    try:
                        img_learn = smart_learner.learn_from_image(self.user_id, frame_base64)
                        if img_learn.get("learned"):
                            self.learned_info.append("image_analysis")
                    except:
                        pass
                
                # اضافه کردن پیشنهاد غذا
                emotion_info = EMOTION_RESPONSES.get(emotion, EMOTION_RESPONSES["neutral"])
                analysis["food_suggestion"] = emotion_info["food_suggestion"]
                analysis["emotion_fa"] = emotion_info["fa"]
                analysis["emotion_changed"] = emotion_changed
                
                # اگه احساس عوض شده، پیام خاص بده
                if emotion_changed:
                    if emotion == "sad":
                        analysis["emotion_message"] = "چی شد؟ ناراحت شدی؟ 😢"
                    elif emotion == "happy":
                        analysis["emotion_message"] = "خوشحالی که خوشحالی! 😊"
                    elif emotion == "angry":
                        analysis["emotion_message"] = "آروم باش، چی شده؟ 🤗"
                
                return analysis
                
            else:
                return {"error": f"API error: {response.status_code}"}
                
        except Exception as e:
            print(f"Frame analysis error: {e}")
            return {"error": str(e), "emotion": "neutral"}
    
    async def chat_with_context(self, message: str, frame_base64: str = None, audio_text: str = None) -> Dict:
        """
        چت مداوم با context ویدیویی و یادگیری
        
        Args:
            message: پیام کاربر (متنی یا از صدا)
            frame_base64: فریم فعلی (اختیاری)
            audio_text: متن تبدیل شده از صدا (اختیاری)
            
        Returns:
            dict با پاسخ، تحلیل، و اطلاعات یادگیری
        """
        self.message_count += 1
        
        # اگه از صدا اومده، اون رو استفاده کن
        user_message = audio_text or message
        
        # اول فریم رو تحلیل کن (اگه داده شده)
        if frame_base64:
            analysis = await self.analyze_frame(frame_base64)
        else:
            analysis = self.last_analysis or {"emotion": "neutral"}
        
        emotion = analysis.get("emotion", "neutral")
        emotion_info = EMOTION_RESPONSES.get(emotion, EMOTION_RESPONSES["neutral"])
        
        # 🧠 یادگیری فوری از پیام
        learned_now = []
        if self.user_id and user_message:
            try:
                learn_result = smart_learner.learn_from_chat(self.user_id, user_message)
                if learn_result.get("learned"):
                    learned_now = learn_result.get("categories", [])
                    self.learned_info.extend(learned_now)
                    print(f"  🧠 Learned from video chat: {learned_now}")
            except Exception as e:
                print(f"  ⚠️ Learning error: {e}")
        
        # ذخیره پیام کاربر در تاریخچه
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
            "emotion": emotion,
            "timestamp": datetime.now().isoformat()
        })
        
        # محدود کردن تاریخچه
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
        
        # ساخت context از تاریخچه
        history_context = "\n".join([
            f"{'کاربر' if msg['role'] == 'user' else 'روژان'}: {msg['content']}"
            for msg in self.conversation_history[-6:]  # آخرین 6 پیام
        ])
        
        # گرفتن پروفایل کاربر
        user_profile = ""
        if self.user_id:
            try:
                profile_summary = smart_learner.get_profile_summary(self.user_id)
                warnings = smart_learner.get_warnings(self.user_id)
                if profile_summary:
                    user_profile = f"\n📋 پروفایل: {profile_summary[:200]}"
                if warnings:
                    user_profile += f"\n⚠️ هشدارها: {', '.join(warnings[:3])}"
            except:
                pass
        
        # ساخت prompt کامل برای مکالمه مداوم
        full_prompt = f"""تو روژان هستی، دستیار هوشمند رستوران که داری با کاربر ویدیو چت می‌کنی.

📹 اطلاعات از تصویر:
- احساس کاربر: {emotion} ({emotion_info["fa"]})
- محیط: {analysis.get("environment", "نامشخص")}
- لحن پاسخ: {emotion_info["response_tone"]}
{user_profile}

💬 تاریخچه مکالمه:
{history_context}

قوانین مهم:
1. این یک مکالمه مداوم است - به تاریخچه توجه کن
2. متناسب با احساس کاربر ({emotion_info["fa"]}) جواب بده
3. فارسی محاوره‌ای و صمیمی صحبت کن
4. جواب‌ها کوتاه باشن (برای مکالمه صوتی)
5. اگه چیز جدیدی یاد گرفتی، تأیید کن
6. اگه غذا پیشنهاد میدی، دلیلش رو بگو

{"🧠 الان یاد گرفتم: " + ", ".join(learned_now) if learned_now else ""}

پیام جدید کاربر: {user_message}
"""
        
        try:
            url = f"{self.api_url}/{VISION_MODEL}:generateContent"
            headers = {
                "Authorization": f"Bearer {GAPGPT_API_KEY}",
                "Content-Type": "application/json"
            }
            
            parts = [{"text": full_prompt}]
            
            # اضافه کردن تصویر اگه داریم
            if frame_base64:
                img_data = frame_base64.split(",")[1] if "," in frame_base64 else frame_base64
                parts.append({
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": img_data
                    }
                })
            
            data = {
                "contents": [{"parts": parts}],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 300  # کوتاه‌تر برای مکالمه صوتی
                }
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.ok:
                result = response.json()
                ai_response = result['candidates'][0]['content']['parts'][0]['text'].strip()
                
                # ذخیره پاسخ در تاریخچه
                self.conversation_history.append({
                    "role": "assistant",
                    "content": ai_response,
                    "timestamp": datetime.now().isoformat()
                })
                
                return {
                    "response": ai_response,
                    "emotion": emotion,
                    "emotion_fa": emotion_info["fa"],
                    "tone": emotion_info["response_tone"],
                    "analysis": analysis,
                    "learned": learned_now,
                    "message_count": self.message_count,
                    "emotion_changed": analysis.get("emotion_changed", False)
                }
            else:
                return {"error": f"API error: {response.status_code}", "response": "متأسفم، مشکلی پیش اومد."}
                
        except Exception as e:
            print(f"Chat error: {e}")
            return {"error": str(e), "response": "خطا در پردازش"}
    
    async def transcribe_and_chat(self, audio_base64: str, frame_base64: str = None, mime_type: str = "audio/webm") -> Dict:
        """
        🎤 دریافت صدا، تبدیل به متن، و چت
        
        Args:
            audio_base64: صدای کاربر
            frame_base64: فریم فعلی
            mime_type: نوع فایل صوتی
            
        Returns:
            dict با متن، پاسخ، و تحلیل
        """
        from gemini_client import transcribe
        
        try:
            # تبدیل صدا به متن با تشخیص احساس
            transcribe_result = transcribe(audio_base64, mime_type, detect_emotion=True)
            
            if isinstance(transcribe_result, dict):
                user_text = transcribe_result.get("text", "")
                audio_emotion = transcribe_result.get("emotion", "neutral")
            else:
                user_text = transcribe_result
                audio_emotion = "neutral"
            
            if not user_text:
                return {"error": "متنی تشخیص داده نشد", "response": "متوجه نشدم، میشه تکرار کنی؟"}
            
            # چت با متن استخراج شده
            chat_result = await self.chat_with_context(user_text, frame_base64, audio_text=user_text)
            
            # اضافه کردن اطلاعات صوتی
            chat_result["transcribed_text"] = user_text
            chat_result["audio_emotion"] = audio_emotion
            
            return chat_result
            
        except Exception as e:
            print(f"Transcribe and chat error: {e}")
            return {"error": str(e), "response": "خطا در پردازش صدا"}


# ذخیره sessions فعال
video_sessions: Dict[str, VideoChatSession] = {}


async def create_video_session(user_id: int) -> VideoChatSession:
    """ساخت session جدید"""
    session = VideoChatSession(user_id)
    await session.start()
    video_sessions[session.session_id] = session
    return session


async def get_video_session(session_id: str) -> Optional[VideoChatSession]:
    """گرفتن session موجود"""
    return video_sessions.get(session_id)


async def close_video_session(session_id: str) -> Dict:
    """بستن session"""
    session = video_sessions.pop(session_id, None)
    if session:
        return await session.stop()
    return {"error": "Session not found"}
