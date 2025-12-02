"""
🤖 AI Provider - لایه انتزاعی برای هوش مصنوعی
به راحتی میتونی بین Gemini, OpenAI, Claude و... سوئیچ کنی

استفاده:
    from ai_provider import AI
    
    result = AI.extract_info("سلام، پیتزا میخوام")
    result = AI.analyze_emotion("خیلی عصبانیم!")
    result = AI.detect_patterns(order_history)
    
تغییر Provider:
    در فایل .env:
    AI_PROVIDER=gemini  یا  AI_PROVIDER=openai
"""

import os
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests

# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 تنظیمات
# ═══════════════════════════════════════════════════════════════════════════════

AI_PROVIDER = os.getenv('AI_PROVIDER', 'gemini')  # gemini, openai, claude


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 Interface اصلی (همه Provider ها باید این رو پیاده کنن)
# ═══════════════════════════════════════════════════════════════════════════════

class AIProviderInterface(ABC):
    """Interface برای همه AI Provider ها"""
    
    @abstractmethod
    def extract_info(self, message: str) -> Dict:
        """استخراج اطلاعات از پیام"""
        pass
    
    @abstractmethod
    def analyze_emotion(self, message: str) -> Dict:
        """تحلیل احساس پیام"""
        pass
    
    @abstractmethod
    def detect_patterns(self, data: List[Dict]) -> Dict:
        """تشخیص الگو از داده‌ها"""
        pass
    
    @abstractmethod
    def predict_churn(self, profile: Dict) -> Dict:
        """پیش‌بینی ترک مشتری"""
        pass
    
    @abstractmethod
    def get_recommendation(self, profile: Dict, context: Dict) -> Dict:
        """پیشنهاد شخصی‌سازی‌شده"""
        pass
    
    @abstractmethod
    def check_health(self, foods: List[str], health_profile: Dict) -> List[Dict]:
        """بررسی سلامت غذاها"""
        pass
    
    @abstractmethod
    def analyze_image(self, image_base64: str) -> Dict:
        """تحلیل تصویر غذا"""
        pass
    
    @abstractmethod
    def chat(self, message: str, context: str = None) -> str:
        """چت عادی"""
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# 🔷 Gemini Provider
# ═══════════════════════════════════════════════════════════════════════════════

class GeminiProvider(AIProviderInterface):
    """پیاده‌سازی با Google Gemini از طریق GapGPT"""
    
    def __init__(self):
        from config import GAPGPT_API_KEY, GEMINI_API_KEYS, switch_to_next_key
        
        self.gapgpt_key = GAPGPT_API_KEY
        self.gapgpt_url = "https://api.gapgpt.app/v1beta/models"
        self.backup_keys = GEMINI_API_KEYS
        self.switch_key = switch_to_next_key
        self.model = "gemini-2.5-pro"  # مدل هوشمند برای یادگیری
        self.use_gapgpt = True
        print("✅ GapGPT AI Provider initialized")
    
    def _call_api(self, prompt: str, max_tokens: int = 2000) -> str:
        """فراخوانی API با مدیریت خطا"""
        # روش ۱: GapGPT API (با requests)
        if self.use_gapgpt:
            try:
                url = f"{self.gapgpt_url}/{self.model}:generateContent"
                headers = {
                    "Authorization": f"Bearer {self.gapgpt_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": max_tokens,
                    }
                }
                
                response = requests.post(url, headers=headers, json=data, timeout=60)
                
                if response.ok:
                    result = response.json()
                    return result['candidates'][0]['content']['parts'][0]['text'].strip()
                    
            except Exception as e:
                print(f"⚠️ GapGPT error: {e}, switching to direct API")
                self.use_gapgpt = False
        
        # روش ۲: Direct API (بکاپ)
        from config import get_current_key
        for attempt in range(len(self.backup_keys)):
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={get_current_key()}"
                data = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": max_tokens,
                    }
                }
                
                response = requests.post(url, json=data, timeout=30)
                
                if response.status_code in [429, 403]:
                    self.switch_key()
                    continue
                
                if response.status_code != 200:
                    return None
                
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text'].strip()
                
            except Exception as e:
                print(f"Direct API error: {e}")
                self.switch_key()
                continue
        
        return None
    
    def _parse_json(self, text: str) -> Dict:
        """پارس امن JSON از خروجی"""
        if not text:
            return {}
        try:
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())
        except:
            return {}
    
    def extract_info(self, message: str) -> Dict:
        """استخراج ۱۲۰+ فیلد از پیام"""
        prompt = f'''از این پیام اطلاعات استخراج کن. فقط JSON برگردون.

پیام: "{message}"

فیلدها:
{{
  "personal": {{"name": null, "age": null, "city": null, "job": null}},
  "food": {{"favorites": [], "dislikes": [], "allergies": [], "dietary": [], "spice_level": null}},
  "health": {{"conditions": [], "diabetes": null, "blood_pressure": null}},
  "emotion": {{"current_mood": null, "intensity": 0, "urgency": null}},
  "financial": {{"budget_level": null}},
  "personality": {{"type": null, "communication_style": null}}
}}

فقط فیلدهای موجود در پیام. بقیه null.'''
        
        result = self._call_api(prompt, 2000)
        return self._parse_json(result)
    
    def analyze_emotion(self, message: str) -> Dict:
        """تحلیل احساس با Gemini"""
        prompt = f'''احساس این پیام رو تحلیل کن:

پیام: "{message}"

JSON:
{{
  "mood": "happy/sad/angry/hungry/hurry/tired/neutral",
  "intensity": 0.0-1.0,
  "urgency": "low/medium/high",
  "sarcasm": false,
  "needs_empathy": false
}}'''
        
        result = self._call_api(prompt, 500)
        return self._parse_json(result)
    
    def detect_patterns(self, data: List[Dict]) -> Dict:
        """تشخیص الگو با Gemini"""
        prompt = f'''از این تاریخچه سفارشات، الگوهای رفتاری رو پیدا کن:

داده‌ها: {json.dumps(data[-20:], ensure_ascii=False)}

JSON:
{{
  "patterns": [
    {{"type": "day_pattern", "day": "Friday", "food": "پیتزا", "confidence": 0.9}},
    {{"type": "time_pattern", "time": "12:00-14:00", "food": "ساندویچ"}}
  ],
  "insights": ["معمولاً جمعه‌ها پیتزا میگیره"]
}}'''
        
        result = self._call_api(prompt, 1000)
        return self._parse_json(result)
    
    def predict_churn(self, profile: Dict) -> Dict:
        """پیش‌بینی ترک با Gemini"""
        prompt = f'''با توجه به پروفایل این مشتری، احتمال ترکش رو بررسی کن:

پروفایل: {json.dumps(profile, ensure_ascii=False)}

JSON:
{{
  "risk_level": "low/medium/high",
  "risk_score": 0-100,
  "factors": ["دلیل ۱", "دلیل ۲"],
  "suggested_action": "پیشنهاد",
  "retention_offer": {{"type": "discount", "value": "20%"}}
}}'''
        
        result = self._call_api(prompt, 800)
        return self._parse_json(result)
    
    def get_recommendation(self, profile: Dict, context: Dict) -> Dict:
        """پیشنهاد شخصی با Gemini"""
        prompt = f'''بر اساس پروفایل و context، غذا پیشنهاد بده:

پروفایل: {json.dumps(profile, ensure_ascii=False)}
Context: {json.dumps(context, ensure_ascii=False)}

JSON:
{{
  "recommendations": [
    {{"food": "نام غذا", "reason": "چرا", "confidence": 0.9}}
  ],
  "personalized_message": "پیام شخصی"
}}'''
        
        result = self._call_api(prompt, 800)
        return self._parse_json(result)
    
    def check_health(self, foods: List[str], health_profile: Dict) -> List[Dict]:
        """بررسی سلامت با Gemini"""
        prompt = f'''این غذاها رو با پروفایل سلامت چک کن:

غذاها: {foods}
پروفایل سلامت: {json.dumps(health_profile, ensure_ascii=False)}

JSON (لیست هشدارها):
[
  {{"food": "نام", "severity": "high/medium/low", "message": "هشدار", "reason": "دلیل"}}
]'''
        
        result = self._call_api(prompt, 800)
        parsed = self._parse_json(result)
        return parsed if isinstance(parsed, list) else []
    
    def analyze_image(self, image_base64: str) -> Dict:
        """تحلیل تصویر غذا"""
        # برای Vision API باید endpoint متفاوت استفاده بشه
        # فعلاً placeholder
        return {"error": "Vision API not implemented yet"}
    
    def chat(self, message: str, context: str = None) -> str:
        """چت عادی"""
        prompt = message
        if context:
            prompt = f"{context}\n\nپیام: {message}"
        return self._call_api(prompt, 1000) or ""


# ═══════════════════════════════════════════════════════════════════════════════
# 🔶 OpenAI Provider (آماده برای آینده)
# ═══════════════════════════════════════════════════════════════════════════════

class OpenAIProvider(AIProviderInterface):
    """پیاده‌سازی با OpenAI GPT"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = "gpt-4o-mini"  # یا gpt-4o
        self.api_url = "https://api.openai.com/v1/chat/completions"
    
    def _call_api(self, prompt: str, max_tokens: int = 2000) -> str:
        """فراخوانی OpenAI API"""
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.1
            }
            
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            
            if response.status_code != 200:
                return None
            
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return None
    
    def _parse_json(self, text: str) -> Dict:
        """پارس JSON"""
        if not text:
            return {}
        try:
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())
        except:
            return {}
    
    # همون متدهای Gemini، فقط prompt ها یکم متفاوت
    def extract_info(self, message: str) -> Dict:
        prompt = f'''Extract information from this Persian message. Return JSON only.

Message: "{message}"

Fields:
{{
  "personal": {{"name": null, "age": null, "city": null, "job": null}},
  "food": {{"favorites": [], "dislikes": [], "allergies": [], "dietary": [], "spice_level": null}},
  "health": {{"conditions": [], "diabetes": null}},
  "emotion": {{"current_mood": null, "intensity": 0, "urgency": null}},
  "financial": {{"budget_level": null}}
}}'''
        
        result = self._call_api(prompt, 2000)
        return self._parse_json(result)
    
    def analyze_emotion(self, message: str) -> Dict:
        prompt = f'''Analyze emotion of this Persian message:

Message: "{message}"

Return JSON:
{{"mood": "happy/sad/angry/neutral", "intensity": 0.0-1.0, "urgency": "low/medium/high"}}'''
        
        result = self._call_api(prompt, 300)
        return self._parse_json(result)
    
    def detect_patterns(self, data: List[Dict]) -> Dict:
        prompt = f'''Find behavioral patterns in this order history:

Data: {json.dumps(data[-20:], ensure_ascii=False)}

Return JSON with patterns array.'''
        
        result = self._call_api(prompt, 1000)
        return self._parse_json(result)
    
    def predict_churn(self, profile: Dict) -> Dict:
        prompt = f'''Predict churn risk for this customer:

Profile: {json.dumps(profile, ensure_ascii=False)}

Return JSON with risk_level, risk_score, factors, suggested_action.'''
        
        result = self._call_api(prompt, 800)
        return self._parse_json(result)
    
    def get_recommendation(self, profile: Dict, context: Dict) -> Dict:
        prompt = f'''Recommend food based on profile and context:

Profile: {json.dumps(profile, ensure_ascii=False)}
Context: {json.dumps(context, ensure_ascii=False)}

Return JSON with recommendations array.'''
        
        result = self._call_api(prompt, 800)
        return self._parse_json(result)
    
    def check_health(self, foods: List[str], health_profile: Dict) -> List[Dict]:
        prompt = f'''Check these foods against health profile:

Foods: {foods}
Health: {json.dumps(health_profile, ensure_ascii=False)}

Return JSON array of warnings.'''
        
        result = self._call_api(prompt, 800)
        parsed = self._parse_json(result)
        return parsed if isinstance(parsed, list) else []
    
    def analyze_image(self, image_base64: str) -> Dict:
        # OpenAI Vision API
        return {"error": "Vision not implemented"}
    
    def chat(self, message: str, context: str = None) -> str:
        prompt = message
        if context:
            prompt = f"{context}\n\n{message}"
        return self._call_api(prompt, 1000) or ""


# ═══════════════════════════════════════════════════════════════════════════════
# 🟣 Claude Provider (آماده برای آینده)
# ═══════════════════════════════════════════════════════════════════════════════

class ClaudeProvider(AIProviderInterface):
    """پیاده‌سازی با Anthropic Claude"""
    
    def __init__(self):
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.model = "claude-3-haiku-20240307"  # یا claude-3-sonnet
        self.api_url = "https://api.anthropic.com/v1/messages"
    
    def _call_api(self, prompt: str, max_tokens: int = 2000) -> str:
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        
        try:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            
            if response.status_code != 200:
                return None
            
            result = response.json()
            return result['content'][0]['text'].strip()
            
        except Exception as e:
            print(f"Claude API error: {e}")
            return None
    
    def _parse_json(self, text: str) -> Dict:
        if not text:
            return {}
        try:
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())
        except:
            return {}
    
    # متدها مشابه OpenAI
    def extract_info(self, message: str) -> Dict:
        return self._parse_json(self._call_api(f"Extract info from: {message}"))
    
    def analyze_emotion(self, message: str) -> Dict:
        return self._parse_json(self._call_api(f"Analyze emotion: {message}"))
    
    def detect_patterns(self, data: List[Dict]) -> Dict:
        return self._parse_json(self._call_api(f"Find patterns: {data}"))
    
    def predict_churn(self, profile: Dict) -> Dict:
        return self._parse_json(self._call_api(f"Predict churn: {profile}"))
    
    def get_recommendation(self, profile: Dict, context: Dict) -> Dict:
        return self._parse_json(self._call_api(f"Recommend: {profile}, {context}"))
    
    def check_health(self, foods: List[str], health_profile: Dict) -> List[Dict]:
        result = self._parse_json(self._call_api(f"Check health: {foods}, {health_profile}"))
        return result if isinstance(result, list) else []
    
    def analyze_image(self, image_base64: str) -> Dict:
        return {"error": "Not implemented"}
    
    def chat(self, message: str, context: str = None) -> str:
        return self._call_api(message) or ""


# ═══════════════════════════════════════════════════════════════════════════════
# 🏭 Factory - انتخاب Provider
# ═══════════════════════════════════════════════════════════════════════════════

def get_ai_provider(provider_name: str = None) -> AIProviderInterface:
    """دریافت AI Provider بر اساس تنظیمات"""
    provider = provider_name or AI_PROVIDER
    
    providers = {
        'gemini': GeminiProvider,
        'openai': OpenAIProvider,
        'claude': ClaudeProvider,
    }
    
    if provider not in providers:
        raise ValueError(f"Unknown AI provider: {provider}. Available: {list(providers.keys())}")
    
    return providers[provider]()


# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 کلاس راحت برای استفاده (Singleton)
# ═══════════════════════════════════════════════════════════════════════════════

class AI:
    """
    دسترسی آسان به AI Provider
    
    استفاده:
        AI.extract_info("پیام")
        AI.analyze_emotion("پیام")
        AI.detect_patterns(data)
        AI.switch_provider("openai")
    """
    _instance: AIProviderInterface = None
    _provider_name: str = AI_PROVIDER
    
    @classmethod
    def _get_instance(cls) -> AIProviderInterface:
        if cls._instance is None:
            cls._instance = get_ai_provider(cls._provider_name)
        return cls._instance
    
    @classmethod
    def switch_provider(cls, provider_name: str):
        """تغییر Provider در runtime"""
        cls._provider_name = provider_name
        cls._instance = get_ai_provider(provider_name)
        print(f"🔄 AI Provider switched to: {provider_name}")
    
    @classmethod
    def get_current_provider(cls) -> str:
        return cls._provider_name
    
    # متدهای استاتیک برای دسترسی آسان
    @classmethod
    def extract_info(cls, message: str) -> Dict:
        return cls._get_instance().extract_info(message)
    
    @classmethod
    def analyze_emotion(cls, message: str) -> Dict:
        return cls._get_instance().analyze_emotion(message)
    
    @classmethod
    def detect_patterns(cls, data: List[Dict]) -> Dict:
        return cls._get_instance().detect_patterns(data)
    
    @classmethod
    def predict_churn(cls, profile: Dict) -> Dict:
        return cls._get_instance().predict_churn(profile)
    
    @classmethod
    def get_recommendation(cls, profile: Dict, context: Dict = None) -> Dict:
        return cls._get_instance().get_recommendation(profile, context or {})
    
    @classmethod
    def check_health(cls, foods: List[str], health_profile: Dict) -> List[Dict]:
        return cls._get_instance().check_health(foods, health_profile)
    
    @classmethod
    def analyze_image(cls, image_base64: str) -> Dict:
        return cls._get_instance().analyze_image(image_base64)
    
    @classmethod
    def chat(cls, message: str, context: str = None) -> str:
        return cls._get_instance().chat(message, context)


# ═══════════════════════════════════════════════════════════════════════════════
# 🧪 تست
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"🤖 Current AI Provider: {AI.get_current_provider()}")
    
    # تست استخراج
    result = AI.extract_info("سلام، اسمم علی هست و پیتزا دوست دارم")
    print(f"📝 Extract: {result}")
    
    # تست احساس
    emotion = AI.analyze_emotion("خیلی عصبانیم، چرا دیر شد؟!")
    print(f"😊 Emotion: {emotion}")
    
    # تغییر provider (اگه API key داشته باشی)
    # AI.switch_provider("openai")
    # result = AI.extract_info("Hello!")
