"""
🧠 Smart Learner - یادگیری هوشمند ۱۲۰+ فیلد
سیستم یادگیری خودکار پروفایل مشتری از مکالمات

ویژگی‌ها:
- استخراج ۱۲۰+ فیلد از چت
- امتیاز اطمینان (Confidence Score)
- مدیریت تناقضات
- کهنگی اطلاعات (Time Decay)
- یادگیری از سفارشات
- قابل تغییر AI Provider (Gemini/OpenAI/Claude)

نویسنده: روژان AI
تاریخ: 2025
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

# 🤖 AI Provider - قابل تغییر!
from ai_provider import AI

# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 تنظیمات
# ═══════════════════════════════════════════════════════════════════════════════

# تنظیمات کهنگی
DECAY_DAYS = {
    'emotion': 1,           # احساسات: ۱ روز
    'timing': 30,           # زمان‌بندی: ۱ ماه
    'financial': 60,        # مالی: ۲ ماه
    'food.favorites': 180,  # غذای محبوب: ۶ ماه
    'personal': 365,        # شخصی: ۱ سال
    'health': 365,          # سلامت: ۱ سال
    'default': 90           # پیش‌فرض: ۳ ماه
}

# حداقل امتیاز اطمینان برای ذخیره
MIN_CONFIDENCE = 0.3

# ═══════════════════════════════════════════════════════════════════════════════
# 📋 Mega Prompt برای استخراج ۱۲۰+ فیلد
# ═══════════════════════════════════════════════════════════════════════════════

MEGA_EXTRACTION_PROMPT = '''تو یک سیستم هوشمند استخراج اطلاعات هستی.
از پیام کاربر، هر اطلاعاتی که میتونی استخراج کن.

⚠️ قوانین مهم:
1. فقط چیزی که واقعاً در پیام گفته شده رو استخراج کن
2. هرگز حدس نزن یا اطلاعات جعلی نساز
3. اگه مطمئن نیستی، اون فیلد رو ننویس
4. خروجی فقط JSON باشه، بدون توضیح اضافه
5. برای هر فیلد، confidence (0.0-1.0) و signal (positive/negative) رو هم بده:
   - "عاشق پیتزام" → confidence: 1.0, signal: positive
   - "پیتزا بد نیست" → confidence: 0.5, signal: positive  
   - "پیتزا دوست ندارم" → confidence: 0.9, signal: negative
   - "فکر کنم آلرژی دارم" → confidence: 0.4, signal: positive

⚠️ قوانین خاص برای اسم (name):
- فقط اسم خود کاربر رو استخراج کن، نه اسم دوست/همکار/دیگران!
- "من علی هستم" یا "اسمم مریم" → confidence: 1.0 (اسم خود کاربر)
- "برای علی سفارش بده" → confidence: 0.0 (اسم دیگری - استخراج نکن!)
- "دوستم سارا گفت..." → confidence: 0.0 (اسم دیگری - استخراج نکن!)
- اگه مشخص نیست اسم خود کاربره، اصلاً name رو ننویس!

پیام کاربر: "{message}"

خروجی JSON (فقط فیلدهای موجود در پیام):
{{
  "personal": {{
    "name": "اسم کوچک",
    "family_name": "نام خانوادگی",
    "nickname": "لقب/اسم مستعار",
    "age": 0,
    "birth_year": 0,
    "gender": "male/female",
    "city": "شهر",
    "district": "محله",
    "country": "کشور",
    "nationality": "ملیت",
    "job": "شغل",
    "job_title": "عنوان شغلی",
    "company": "شرکت",
    "work_type": "remote/office/hybrid",
    "education": "تحصیلات",
    "university": "دانشگاه",
    "field_of_study": "رشته",
    "languages": ["زبان‌ها"],
    "marital_status": "single/married/divorced",
    "spouse_name": "اسم همسر",
    "family_size": 0,
    "children_count": 0,
    "children_ages": [],
    "children_names": [],
    "parents_alive": true,
    "lives_with": "alone/family/roommate",
    "pet_type": "نوع حیوان",
    "pet_name": "اسم حیوان",
    "birthday_day": 0,
    "birthday_month": "ماه",
    "zodiac": "برج",
    "blood_type": "گروه خونی",
    "height": 0,
    "dominant_hand": "right/left"
  }},

  "food": {{
    "favorites": ["غذاهای محبوب"],
    "super_favorites": ["غذای خیلی محبوب"],
    "dislikes": ["غذاهای نامحبوب"],
    "hates": ["غذاهایی که متنفره"],
    "never_tried": ["غذاهایی که نخورده"],
    "want_to_try": ["غذاهایی که میخواد امتحان کنه"],
    "childhood_favorites": ["غذای دوران کودکی"],
    "comfort_food": ["غذای آرامش‌بخش"],
    "cuisines_liked": ["آشپزی محبوب: ایرانی/ایتالیایی/چینی/..."],
    "cuisines_disliked": ["آشپزی نامحبوب"],
    "allergies": ["آلرژی‌های غذایی"],
    "intolerances": ["عدم تحمل: لاکتوز/گلوتن/..."],
    "dietary": ["رژیم: گیاهی/وگان/حلال/کوشر/کتو/..."],
    "diet_reason": "دلیل رژیم: سلامتی/اعتقادی/...",
    "spice_level": "none/mild/medium/hot/extra_hot",
    "spice_preference": "تند دوست داره یا نه",
    "salt_level": "low/normal/high",
    "sugar_level": "low/normal/high",
    "fat_level": "low/normal/high",
    "sour_preference": "ترش دوست داره؟",
    "bitter_preference": "تلخ دوست داره؟",
    "sweet_preference": "شیرین دوست داره؟",
    "umami_preference": "اومامی دوست داره؟",
    "portion_size": "small/medium/large/extra_large",
    "eating_speed": "slow/normal/fast",
    "temperature_preference": "hot/warm/room/cold",
    "texture_preferences": ["نرم/ترد/چسبناک/..."],
    "cooking_method_preference": ["کبابی/سرخ‌شده/بخارپز/..."],
    "favorite_ingredients": ["مواد اولیه محبوب"],
    "disliked_ingredients": ["مواد اولیه نامحبوب"],
    "favorite_drink": "نوشیدنی محبوب",
    "favorite_hot_drink": "نوشیدنی گرم محبوب",
    "favorite_cold_drink": "نوشیدنی سرد محبوب",
    "coffee_preference": "نوع قهوه",
    "tea_preference": "نوع چای",
    "favorite_dessert": "دسر محبوب",
    "favorite_snack": "میان‌وعده محبوب",
    "favorite_fruit": "میوه محبوب",
    "favorite_vegetable": "سبزی محبوب",
    "favorite_sauce": "سس محبوب",
    "favorite_bread": "نان محبوب",
    "favorite_rice": "نوع برنج",
    "favorite_meat": "گوشت محبوب",
    "favorite_seafood": "غذای دریایی محبوب",
    "breakfast_preference": "صبحانه ترجیحی",
    "lunch_preference": "ناهار ترجیحی",
    "dinner_preference": "شام ترجیحی",
    "midnight_snack": "میان‌وعده شبانه",
    "guilty_pleasure_food": "غذای گناه‌آلود!",
    "food_memories": ["خاطرات غذایی"],
    "cooking_skill": "none/beginner/intermediate/advanced/chef",
    "cooks_at_home": true,
    "favorite_restaurant": "رستوران محبوب",
    "favorite_fast_food": "فست‌فود محبوب"
  }},

  "health": {{
    "general_health": "excellent/good/fair/poor",
    "chronic_conditions": ["بیماری‌های مزمن"],
    "diabetes": "none/type1/type2/prediabetic",
    "blood_pressure": "low/normal/high",
    "cholesterol": "low/normal/high",
    "heart_condition": "بیماری قلبی",
    "kidney_condition": "بیماری کلیوی",
    "liver_condition": "بیماری کبدی",
    "digestive_issues": ["مشکلات گوارشی"],
    "ibs": true,
    "acid_reflux": true,
    "ulcer": true,
    "food_sensitivities": ["حساسیت‌های غذایی"],
    "skin_conditions": ["مشکلات پوستی مرتبط با غذا"],
    "migraine_triggers": ["محرک‌های میگرن"],
    "traditional_temperament": "گرم/سرد/خشک/تر",
    "ayurvedic_dosha": "vata/pitta/kapha",
    "weight_status": "underweight/normal/overweight/obese",
    "weight_goal": "lose/maintain/gain",
    "on_diet": true,
    "diet_type": "نوع رژیم لاغری",
    "calorie_counting": true,
    "daily_calorie_target": 0,
    "macro_tracking": true,
    "fitness_level": "sedentary/light/moderate/active/athlete",
    "exercise_type": ["نوع ورزش"],
    "exercise_frequency": "روزانه/هفتگی",
    "gym_member": true,
    "athlete_type": "نوع ورزشکار",
    "pregnant": true,
    "pregnancy_trimester": 0,
    "breastfeeding": true,
    "menstrual_affects_appetite": true,
    "medications": ["داروها"],
    "supplements": ["مکمل‌ها"],
    "vitamins_needed": ["ویتامین‌های مورد نیاز"],
    "water_intake": "low/normal/high",
    "sleep_quality": "poor/fair/good/excellent",
    "sleep_hours": 0,
    "stress_level": "low/medium/high/extreme",
    "anxiety": true,
    "depression": true,
    "eating_disorder_history": true,
    "smoking": "never/former/current",
    "alcohol": "never/rarely/moderate/heavy",
    "caffeine_sensitivity": true,
    "energy_level": "low/medium/high",
    "appetite_level": "low/normal/high",
    "recent_illness": "بیماری اخیر",
    "recovery_diet": true,
    "surgery_recent": "جراحی اخیر",
    "dental_issues": "مشکلات دندان"
  }},

  "emotion": {{
    "current_mood": "happy/sad/angry/anxious/stressed/tired/excited/neutral",
    "mood_intensity": 0.0,
    "is_sarcastic": true,
    "is_joking": true,
    "urgency_level": "none/low/medium/high/critical",
    "patience_level": "none/low/medium/high",
    "frustration_level": "none/low/medium/high",
    "satisfaction_level": "very_unhappy/unhappy/neutral/happy/very_happy",
    "hunger_level": "not_hungry/slightly/moderate/very/starving",
    "energy_mood": "exhausted/tired/normal/energetic/hyper",
    "social_mood": "antisocial/quiet/normal/social/party",
    "needs_comfort": true,
    "needs_empathy": true,
    "needs_speed": true,
    "needs_value": true,
    "needs_quality": true,
    "celebration_mode": true,
    "celebration_type": "نوع جشن",
    "comfort_eating": true,
    "stress_eating": true,
    "emotional_trigger": "محرک احساسی",
    "mood_food_connection": "ارتباط غذا با حالش"
  }},

  "personality": {{
    "mbti_type": "INTJ/ENFP/...",
    "personality_type": "analyst/doer/social/perfectionist/creative",
    "communication_style": "direct/detailed/emotional/formal/casual",
    "decision_making": "impulsive/quick/thoughtful/slow/indecisive",
    "risk_tolerance": "very_low/low/medium/high/very_high",
    "food_adventurous": true,
    "tries_new_things": true,
    "brand_loyal": true,
    "restaurant_loyal": true,
    "routine_oriented": true,
    "spontaneous": true,
    "detail_oriented": true,
    "big_picture": true,
    "organized": true,
    "perfectionist": true,
    "patient": true,
    "impatient": true,
    "introvert_extrovert": "introvert/ambivert/extrovert",
    "social_energy": "draining/neutral/energizing",
    "leadership": true,
    "follower": true,
    "independent": true,
    "team_player": true,
    "competitive": true,
    "cooperative": true,
    "optimist_pessimist": "optimist/realist/pessimist",
    "morning_evening_person": "morning/neither/evening",
    "planner_spontaneous": "planner/mixed/spontaneous",
    "logical_emotional": "logical/balanced/emotional",
    "traditional_modern": "traditional/mixed/modern",
    "minimalist_maximalist": "minimalist/balanced/maximalist",
    "quality_quantity": "quality/balanced/quantity",
    "health_conscious": true,
    "environmentally_conscious": true,
    "price_conscious": true,
    "time_conscious": true,
    "appearance_conscious": true,
    "socially_conscious": true,
    "tech_savvy": true,
    "early_adopter": true
  }},

  "financial": {{
    "income_level": "low/medium/high/very_high",
    "budget_level": "tight/moderate/comfortable/unlimited",
    "budget_for_food": "low/medium/high",
    "average_order_value": 0,
    "max_willing_to_pay": 0,
    "price_sensitivity": "very_sensitive/sensitive/moderate/insensitive",
    "value_seeker": true,
    "discount_hunter": true,
    "coupon_user": true,
    "loyalty_program_member": true,
    "premium_buyer": true,
    "bulk_buyer": true,
    "payment_preference": "cash/card/online/crypto",
    "tip_behavior": "never/sometimes/always",
    "tip_percentage": 0,
    "expense_tracking": true,
    "end_of_month_tight": true,
    "payday": 0,
    "financial_stress": true,
    "treats_self": true,
    "treats_others": true,
    "generous_with_food": true,
    "splits_bill": true,
    "pays_for_group": true
  }},

  "timing": {{
    "chronotype": "early_bird/normal/night_owl",
    "wake_up_time": "HH:MM",
    "sleep_time": "HH:MM",
    "breakfast_time": "HH:MM",
    "lunch_time": "HH:MM",
    "dinner_time": "HH:MM",
    "snack_times": ["HH:MM"],
    "work_start": "HH:MM",
    "work_end": "HH:MM",
    "lunch_break_duration": 0,
    "busy_days": ["روزهای شلوغ"],
    "free_days": ["روزهای آزاد"],
    "work_from_home_days": ["روزهای دورکاری"],
    "gym_days": ["روزهای ورزش"],
    "order_frequency": "daily/few_times_week/weekly/biweekly/monthly",
    "preferred_order_time": "HH:MM",
    "preferred_order_day": "روز ترجیحی",
    "weekend_routine": "روتین آخر هفته",
    "weekday_routine": "روتین روز کاری",
    "seasonal_preferences": {{
      "spring": "بهار",
      "summer": "تابستان",
      "fall": "پاییز",
      "winter": "زمستان"
    }},
    "ramadan_fasting": true,
    "intermittent_fasting": true,
    "fasting_schedule": "برنامه روزه",
    "meal_prep_day": "روز آماده‌سازی",
    "grocery_day": "روز خرید"
  }},

  "location": {{
    "home_address_area": "منطقه خانه",
    "home_city": "شهر",
    "work_address_area": "منطقه کار",
    "work_city": "شهر کار",
    "commute_method": "car/public/bike/walk",
    "commute_duration": 0,
    "delivery_preference": "door/lobby/office/pickup",
    "home_floor": 0,
    "has_elevator": true,
    "doorbell_works": true,
    "parking_available": true,
    "landmark_near_home": "نقطه عطف",
    "special_delivery_instructions": "دستورالعمل تحویل",
    "multiple_addresses": true,
    "frequently_travels": true,
    "travel_frequency": "monthly/quarterly/yearly",
    "current_location_type": "home/work/travel/other",
    "neighborhood_type": "residential/commercial/mixed"
  }},

  "social": {{
    "eating_alone_preference": true,
    "usual_eating_company": "alone/partner/family/friends/colleagues",
    "group_size_usual": 0,
    "is_decision_maker": true,
    "orders_for_others": true,
    "orders_for_kids": true,
    "orders_for_elderly": true,
    "hosts_gatherings": true,
    "gathering_frequency": "often/sometimes/rarely/never",
    "foodie_friends": true,
    "shares_food_photos": true,
    "writes_reviews": true,
    "social_media_foodie": true,
    "influencer": true,
    "follower_count": 0,
    "recommends_to_others": true,
    "recommendation_influence": "low/medium/high",
    "part_of_food_groups": true,
    "cultural_background": "فرهنگ",
    "religious_dietary_rules": true,
    "family_traditions": ["سنت‌های خانوادگی غذایی"],
    "office_lunch_culture": "نوع ناهار اداری"
  }},

  "delivery": {{
    "preferred_delivery_time": "asap/scheduled",
    "scheduled_time_preference": "HH:MM",
    "delivery_patience": "low/medium/high",
    "tracks_delivery": true,
    "contactless_preference": true,
    "call_before_arrival": true,
    "meet_at_door": true,
    "special_ring_instructions": "دستور زنگ",
    "safe_place_delivery": true,
    "tips_delivery_person": true,
    "delivery_complaints_history": ["شکایات قبلی"],
    "preferred_delivery_service": "سرویس ترجیحی",
    "has_delivery_subscription": true
  }},

  "occasions": {{
    "birthday": "MM-DD",
    "spouse_birthday": "MM-DD",
    "children_birthdays": ["MM-DD"],
    "anniversary": "MM-DD",
    "special_occasions": ["مناسبت‌های خاص"],
    "holidays_celebrated": ["تعطیلات"],
    "favorite_team": "تیم ورزشی",
    "game_day_food": "غذای روز بازی",
    "movie_night_food": "غذای شب فیلم",
    "date_night_food": "غذای شب دونفره",
    "party_food_preference": "غذای مهمانی",
    "work_celebration_food": "غذای جشن کاری",
    "comfort_occasions": ["مواقع نیاز به آرامش"],
    "reward_occasions": ["مواقع پاداش دادن به خود"]
  }},

  "interests": {{
    "hobbies": ["سرگرمی‌ها"],
    "music_while_eating": "نوع موسیقی",
    "watches_while_eating": "چی میبینه موقع غذا",
    "favorite_shows": ["برنامه‌های محبوب"],
    "gamer": true,
    "gaming_snacks": "تنقلات گیمینگ",
    "reader": true,
    "reading_with_coffee": true,
    "podcast_listener": true,
    "works_while_eating": true,
    "meditation_yoga": true,
    "mindful_eating": true,
    "food_photography": true,
    "cooking_shows_fan": true,
    "food_blogger_follower": true,
    "recipe_collector": true,
    "kitchen_gadget_lover": true,
    "sustainable_eating": true,
    "local_food_supporter": true,
    "organic_preference": true,
    "farm_to_table": true
  }},

  "loyalty": {{
    "membership_tier": "bronze/silver/gold/platinum/diamond",
    "total_orders": 0,
    "total_spent": 0,
    "points_balance": 0,
    "favorite_rewards": ["پاداش‌های محبوب"],
    "referral_count": 0,
    "streak_days": 0,
    "badges_earned": ["نشان‌ها"],
    "challenges_completed": ["چالش‌های تکمیل‌شده"],
    "vip_status": true,
    "early_access": true,
    "beta_tester": true,
    "feedback_giver": true,
    "complaint_history": ["تاریخچه شکایات"],
    "compliment_history": ["تاریخچه تعریف‌ها"]
  }},

  "tech": {{
    "device_type": "iphone/android/web",
    "app_version": "نسخه اپ",
    "notification_preference": "all/important/none",
    "email_preference": true,
    "sms_preference": true,
    "push_preference": true,
    "uses_voice_order": true,
    "uses_image_search": true,
    "tech_comfort": "low/medium/high",
    "needs_assistance": true,
    "accessibility_needs": ["نیازهای دسترسی‌پذیری"],
    "language_preference": "زبان ترجیحی",
    "font_size_preference": "small/normal/large"
  }},

  "special_requests": ["درخواست‌های خاص"],
  
  "notes": ["یادداشت‌های مهم"],
  
  "warnings": ["هشدارها: آلرژی شدید و..."],
  
  "preferences_confidence": {{
    "food": 0.0,
    "health": 0.0,
    "personality": 0.0,
    "overall": 0.0
  }}
}}

⚠️ فقط فیلدهایی که از پیام استخراج کردی رو برگردون. بقیه رو ننویس.
اگه هیچ اطلاعاتی نیست، فقط {{}} برگردون.
'''

# ═══════════════════════════════════════════════════════════════════════════════
# 🧠 توابع اصلی - همه با AI Provider
# ═══════════════════════════════════════════════════════════════════════════════

def extract_from_message(message: str) -> dict:
    """
    استخراج همه اطلاعات ممکن از یک پیام
    🤖 از AI Provider استفاده میکنه (Gemini/OpenAI/Claude)
    """
    if not message or len(message.strip()) < 3:
        return {}
    
    try:
        # استفاده از AI Provider
        extracted = AI.extract_info(message)
        return clean_empty_fields(extracted) if extracted else {}
    except Exception as e:
        print(f"  ⚠️ Extraction error: {e}")
        return {}


def analyze_emotion_ai(message: str) -> dict:
    """
    تحلیل احساس با AI
    🤖 از AI Provider استفاده میکنه
    """
    try:
        return AI.analyze_emotion(message)
    except Exception as e:
        print(f"  ⚠️ Emotion analysis error: {e}")
        return {"mood": "neutral", "intensity": 0.5}


def clean_empty_fields(data: dict) -> dict:
    """
    حذف فیلدهای خالی از دیکشنری
    """
    if not isinstance(data, dict):
        return data
    
    cleaned = {}
    for key, value in data.items():
        if value is None:
            continue
        elif isinstance(value, dict):
            nested = clean_empty_fields(value)
            if nested:
                cleaned[key] = nested
        elif isinstance(value, list):
            if value and any(v for v in value if v):
                cleaned[key] = [v for v in value if v]
        elif isinstance(value, str):
            if value.strip():
                cleaned[key] = value
        elif isinstance(value, (int, float)):
            if value != 0:
                cleaned[key] = value
        elif isinstance(value, bool):
            cleaned[key] = value
    
    return cleaned


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 تعریف انواع فیلدها
# ═══════════════════════════════════════════════════════════════════════════════

# فیلدهای دائمی - جایگزین میشن
PERMANENT_FIELDS = {
    'personal': ['name', 'family_name', 'age', 'birth_year', 'gender', 'city', 
                 'district', 'job', 'education', 'marital_status', 'blood_type'],
    'food': ['allergies', 'intolerances', 'dietary', 'spice_level', 'portion_size'],
    'health': ['chronic_conditions', 'diabetes', 'blood_pressure', 'traditional_temperament'],
}

# فیلدهای نیمه‌دائمی - ادغام میشن
SEMI_PERMANENT_FIELDS = {
    'food': ['favorites', 'dislikes', 'cuisines_liked', 'favorite_drink', 'favorite_dessert'],
    'personality': ['personality_type', 'communication_style', 'decision_making'],
    'financial': ['budget_level', 'price_sensitive'],
    'timing': ['usual_order_time', 'order_frequency'],
}

# فیلدهای موقت - فقط آخرین مقدار + تاریخچه
TEMPORARY_FIELDS = {
    'emotion': ['current_mood', 'mood_intensity', 'urgency_level', 'hunger_level', 
                'patience_level', 'frustration_level', 'satisfaction_level',
                'needs_comfort', 'needs_empathy', 'needs_speed', 'celebration_mode',
                'comfort_eating', 'stress_eating'],
}

# فیلدهای تاریخچه‌ای - همیشه اضافه میشن
HISTORICAL_FIELDS = ['special_requests', 'notes', 'warnings']


def smart_merge(existing: dict, new: dict, parent_key: str = "") -> dict:
    """
    ادغام هوشمند با در نظر گرفتن نوع فیلد:
    - دائمی: جایگزین
    - نیمه‌دائمی: ادغام لیست‌ها
    - موقت: ذخیره در current + اضافه به history
    - تاریخچه‌ای: همیشه append
    """
    if not existing:
        return new
    if not new:
        return existing
    
    result = existing.copy()
    
    for key, value in new.items():
        if value is None:
            continue
        
        full_key = f"{parent_key}.{key}" if parent_key else key
        
        # تشخیص نوع فیلد
        is_temporary = key in TEMPORARY_FIELDS or parent_key in TEMPORARY_FIELDS
        is_historical = key in HISTORICAL_FIELDS
        
        if key not in result:
            result[key] = value
            
        elif isinstance(value, dict) and isinstance(result.get(key), dict):
            # ادغام recursive دیکشنری‌ها
            result[key] = smart_merge(result[key], value, key)
            
        elif isinstance(value, list) and isinstance(result.get(key), list):
            if is_historical:
                # تاریخچه‌ای: همیشه اضافه کن با timestamp
                for v in value:
                    if v not in result[key]:
                        if isinstance(v, str):
                            result[key].append({"value": v, "time": datetime.now().isoformat()})
                        else:
                            result[key].append(v)
                result[key] = result[key][-50:]  # حداکثر 50 آیتم
            else:
                # نیمه‌دائمی: ادغام بدون تکرار
                combined = result[key] + [v for v in value if v not in result[key]]
                result[key] = combined[-30:]  # حداکثر 30 آیتم
                
        elif is_temporary:
            # موقت: ذخیره فعلی + اضافه به تاریخچه
            history_key = f"{key}_history"
            if history_key not in result:
                result[history_key] = []
            
            # اضافه کردن مقدار قبلی به تاریخچه
            if result.get(key):
                result[history_key].append({
                    "value": result[key],
                    "time": datetime.now().isoformat()
                })
                result[history_key] = result[history_key][-20:]  # آخرین 20 تا
            
            # جایگزینی با مقدار جدید
            result[key] = value
            
        else:
            # دائمی و نیمه‌دائمی: جایگزین
            result[key] = value
    
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# ⏰ کهنگی اطلاعات (Time Decay)
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_decay(field_category: str, last_updated: str) -> float:
    """
    محاسبه ضریب کهنگی یک فیلد
    برمی‌گرداند: 0.0 (کاملاً کهنه) تا 1.0 (تازه)
    """
    if not last_updated:
        return 0.5  # پیش‌فرض
    
    try:
        last_dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
        days_old = (datetime.now() - last_dt.replace(tzinfo=None)).days
        
        # پیدا کردن حداکثر روز برای این دسته
        max_days = DECAY_DAYS.get(field_category, DECAY_DAYS['default'])
        
        # محاسبه decay (خطی)
        decay = max(0.0, 1.0 - (days_old / max_days))
        return decay
        
    except:
        return 0.5


def apply_time_decay(profile_data: dict) -> dict:
    """
    اعمال کهنگی روی تمام فیلدها
    فیلدهای خیلی کهنه حذف میشن
    """
    if not profile_data:
        return {}
    
    result = {}
    
    for category, data in profile_data.items():
        if category.startswith('_'):
            result[category] = data
            continue
        
        if isinstance(data, dict):
            # چک کردن timestamp
            last_updated = data.get('_updated') or profile_data.get('_meta', {}).get('last_learned')
            decay = calculate_decay(category, last_updated)
            
            if decay > 0.1:  # فقط اگه بیشتر از ۱۰٪ تازگی داره
                result[category] = data
                result[category]['_decay'] = round(decay, 2)
        else:
            result[category] = data
    
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# ⚖️ مدیریت تناقضات
# ═══════════════════════════════════════════════════════════════════════════════

def handle_contradiction(
    existing_value: Any, 
    new_value: Any, 
    existing_confidence: float,
    new_confidence: float,
    new_signal: str  # 'positive' or 'negative'
) -> Tuple[Any, float, str]:
    """
    مدیریت تناقض بین مقدار قدیم و جدید
    برمی‌گرداند: (مقدار نهایی، امتیاز اطمینان، وضعیت)
    """
    # اگه مقدار جدید منفی باشه (مثلاً "دوست ندارم")
    if new_signal == 'negative':
        if new_confidence > existing_confidence:
            return None, 0.0, 'removed'  # حذف شد
        else:
            return existing_value, existing_confidence * 0.7, 'weakened'  # ضعیف شد
    
    # اگه هر دو مثبت باشن
    if new_confidence > existing_confidence:
        return new_value, new_confidence, 'replaced'  # جایگزین شد
    elif new_confidence == existing_confidence:
        return new_value, new_confidence, 'updated'  # آپدیت شد
    else:
        # مقدار قدیم قوی‌تره
        return existing_value, existing_confidence, 'kept'  # نگه داشته شد


def process_with_confidence(existing_data: dict, new_data: dict) -> dict:
    """
    پردازش داده جدید با در نظر گرفتن امتیاز اطمینان و تناقضات
    """
    result = existing_data.copy()
    changes_log = []
    
    for category, new_values in new_data.items():
        if category.startswith('_'):
            continue
            
        if not isinstance(new_values, dict):
            continue
        
        if category not in result:
            result[category] = {}
        
        for field, new_val in new_values.items():
            if new_val is None:
                continue
            
            # استخراج confidence و signal
            confidence = 0.8  # پیش‌فرض
            signal = 'positive'
            
            if isinstance(new_val, dict) and 'value' in new_val:
                confidence = new_val.get('confidence', 0.8)
                signal = new_val.get('signal', 'positive')
                new_val = new_val['value']
            
            # چک حداقل اطمینان
            if confidence < MIN_CONFIDENCE:
                continue
            
            # گرفتن مقدار قبلی
            existing_val = result[category].get(field)
            existing_conf = result[category].get(f'{field}_confidence', 0.5)
            
            # مدیریت تناقض
            final_val, final_conf, status = handle_contradiction(
                existing_val, new_val, existing_conf, confidence, signal
            )
            
            # ذخیره نتیجه
            if final_val is not None:
                result[category][field] = final_val
                result[category][f'{field}_confidence'] = final_conf
                result[category][f'{field}_updated'] = datetime.now().isoformat()
            elif status == 'removed' and field in result[category]:
                # انتقال به لیست منفی
                if 'dislikes' not in result[category]:
                    result[category]['dislikes'] = []
                if existing_val and existing_val not in result[category]['dislikes']:
                    result[category]['dislikes'].append(existing_val)
                del result[category][field]
            
            if status != 'kept':
                changes_log.append({
                    'category': category,
                    'field': field,
                    'status': status,
                    'confidence': final_conf
                })
    
    result['_changes_log'] = changes_log
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 🛒 یادگیری از سفارشات
# ═══════════════════════════════════════════════════════════════════════════════

def learn_from_order(user_id: int, order_data: dict) -> dict:
    """
    یادگیری از سفارش واقعی مشتری
    این قوی‌تر از چت هست چون عمل واقعی انجام شده
    """
    import database_pg as db
    
    learned = {
        'food': {},
        'timing': {},
        'financial': {},
        'delivery': {}
    }
    
    # غذاهای سفارش داده شده (confidence بالا چون واقعاً سفارش داده)
    if order_data.get('items'):
        ordered_foods = [item.get('name') for item in order_data['items'] if item.get('name')]
        if ordered_foods:
            learned['food']['actually_ordered'] = ordered_foods
            learned['food']['actually_ordered_confidence'] = 0.95  # خیلی مطمئن
            
            # اضافه به favorites با confidence بالا
            profile = db.get_customer_profile(user_id)
            if profile:
                current_favs = json.loads(profile.get('favorite_foods') or '[]')
                for food in ordered_foods:
                    if food not in current_favs:
                        current_favs.append(food)
                
                db.update_customer_profile(
                    user_id, 
                    favorite_foods=json.dumps(current_favs[-30:], ensure_ascii=False)
                )
    
    # ساعت سفارش
    if order_data.get('created_at'):
        try:
            order_time = datetime.fromisoformat(order_data['created_at'])
            learned['timing']['last_order_time'] = order_time.strftime('%H:%M')
            learned['timing']['last_order_day'] = order_time.strftime('%A')
        except:
            pass
    
    # مبلغ سفارش
    if order_data.get('total_amount'):
        learned['financial']['last_order_amount'] = order_data['total_amount']
    
    # آدرس تحویل
    if order_data.get('delivery_address'):
        learned['delivery']['last_address'] = order_data['delivery_address']
    
    # نوع تحویل
    if order_data.get('delivery_type'):
        learned['delivery']['preference'] = order_data['delivery_type']
    
    # یادداشت سفارش (ممکنه اطلاعات مهم داشته باشه)
    if order_data.get('note'):
        note = order_data['note']
        # استخراج اطلاعات از یادداشت
        note_extracted = extract_from_message(note)
        if note_extracted:
            learned = smart_merge(learned, note_extracted)
    
    # ذخیره در پروفایل
    profile = db.get_customer_profile(user_id)
    if profile:
        extra_data = profile.get('extra_data', {})
        if isinstance(extra_data, str):
            try:
                extra_data = json.loads(extra_data) if extra_data else {}
            except:
                extra_data = {}
        
        # آپدیت آمار سفارش
        extra_data['_order_stats'] = extra_data.get('_order_stats', {})
        extra_data['_order_stats']['total_orders'] = extra_data['_order_stats'].get('total_orders', 0) + 1
        extra_data['_order_stats']['last_order'] = datetime.now().isoformat()
        
        # ذخیره تاریخچه سفارشات (آخرین ۲۰ تا)
        extra_data['_order_history'] = extra_data.get('_order_history', [])
        extra_data['_order_history'].append({
            'items': order_data.get('items', []),
            'total': order_data.get('total_amount'),
            'time': datetime.now().isoformat()
        })
        extra_data['_order_history'] = extra_data['_order_history'][-20:]
        
        # ادغام یادگیری‌های جدید
        merged = smart_merge(extra_data, learned)
        
        db.update_customer_profile(
            user_id,
            extra_data=json.dumps(merged, ensure_ascii=False)
        )
    
    print(f"  🛒 Learned from order: {list(learned.keys())}")
    
    return {
        "learned": True,
        "from": "order",
        "categories": list(learned.keys())
    }


def get_order_insights(user_id: int) -> dict:
    """
    تحلیل الگوی سفارشات کاربر
    """
    import database_pg as db
    
    profile = db.get_customer_profile(user_id)
    if not profile:
        return {}
    
    extra_data = profile.get('extra_data', {})
    if isinstance(extra_data, str):
        try:
            extra_data = json.loads(extra_data) if extra_data else {}
        except:
            extra_data = {}
    
    order_history = extra_data.get('_order_history', [])
    if not order_history:
        return {}
    
    # تحلیل
    insights = {
        'total_orders': len(order_history),
        'favorite_items': {},
        'average_spend': 0,
        'usual_time': None,
        'order_frequency': None
    }
    
    # شمارش غذاهای سفارش داده شده
    item_counts = {}
    total_spend = 0
    order_times = []
    
    for order in order_history:
        for item in order.get('items', []):
            name = item.get('name')
            if name:
                item_counts[name] = item_counts.get(name, 0) + 1
        
        if order.get('total'):
            total_spend += order['total']
        
        if order.get('time'):
            try:
                dt = datetime.fromisoformat(order['time'])
                order_times.append(dt.hour)
            except:
                pass
    
    # پرتکرارترین غذاها
    insights['favorite_items'] = dict(sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5])
    
    # میانگین هزینه
    if order_history:
        insights['average_spend'] = total_spend // len(order_history)
    
    # ساعت معمول
    if order_times:
        avg_hour = sum(order_times) // len(order_times)
        insights['usual_time'] = f"{avg_hour}:00"
    
    return insights


# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 پیشنهاد پیشگیرانه - با AI
# ═══════════════════════════════════════════════════════════════════════════════

def get_proactive_suggestion(user_id: int, context: dict = None) -> dict:
    """
    پیشنهاد غذا قبل از پرسیدن کاربر
    🤖 از AI Provider استفاده میکنه
    """
    profile = get_full_profile(user_id)
    if not profile:
        return {"suggestions": []}
    
    # ساخت context
    now = datetime.now()
    full_context = {
        "hour": now.hour,
        "day_of_week": now.strftime('%A'),
        "is_weekend": now.weekday() >= 4,
        **(context or {})
    }
    
    try:
        # استفاده از AI برای پیشنهاد
        result = AI.get_recommendation(profile, full_context)
        return result if result else {"suggestions": []}
    except Exception as e:
        print(f"  ⚠️ Recommendation error: {e}")
        return {"suggestions": []}


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 تشخیص الگو - با AI
# ═══════════════════════════════════════════════════════════════════════════════

def detect_patterns(user_id: int) -> dict:
    """
    تشخیص الگوهای رفتاری: هر جمعه پیتزا
    🤖 از AI Provider استفاده میکنه
    """
    profile = get_full_profile(user_id)
    if not profile:
        return {"patterns": []}
    
    order_history = profile.get('_order_history', [])
    if len(order_history) < 3:
        return {"patterns": [], "reason": "not_enough_data"}
    
    try:
        # استفاده از AI برای تشخیص الگو
        result = AI.detect_patterns(order_history)
        return result if result else {"patterns": []}
    except Exception as e:
        print(f"  ⚠️ Pattern detection error: {e}")
        return {"patterns": []}


# ═══════════════════════════════════════════════════════════════════════════════
# ⚠️ هشدار سلامت - با AI
# ═══════════════════════════════════════════════════════════════════════════════

def check_health_warnings(user_id: int, food_items: List[str]) -> List[dict]:
    """
    چک سلامت غذا با پروفایل کاربر
    🤖 از AI Provider استفاده میکنه
    """
    profile = get_full_profile(user_id)
    if not profile:
        return []
    
    # استخراج اطلاعات سلامت
    health_profile = {
        "allergies": profile.get('allergies', []),
        "health_conditions": profile.get('health', {}),
        "dietary": profile.get('dietary_preferences', [])
    }
    
    # اگه اطلاعات سلامتی نداریم
    if not any(health_profile.values()):
        return []
    
    try:
        # استفاده از AI برای بررسی
        warnings = AI.check_health(food_items, health_profile)
        return warnings if isinstance(warnings, list) else []
    except Exception as e:
        print(f"  ⚠️ Health check error: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# 📉 پیش‌بینی ترک مشتری - با AI
# ═══════════════════════════════════════════════════════════════════════════════

def predict_churn(user_id: int) -> dict:
    """
    پیش‌بینی احتمال ترک مشتری
    🤖 از AI Provider استفاده میکنه
    """
    profile = get_full_profile(user_id)
    if not profile:
        return {"risk_level": "unknown", "risk_score": 0}
    
    try:
        # استفاده از AI برای پیش‌بینی
        result = AI.predict_churn(profile)
        return result if result else {"risk_level": "low", "risk_score": 0}
    except Exception as e:
        print(f"  ⚠️ Churn prediction error: {e}")
        return {"risk_level": "unknown", "risk_score": 0}


# ═══════════════════════════════════════════════════════════════════════════════
# 👥 یادگیری گروهی
# ═══════════════════════════════════════════════════════════════════════════════

def learn_from_group_order(user_id: int, order: dict) -> dict:
    """یادگیری از سفارش گروهی (خانواده/دوستان)"""
    import database_pg as db
    
    items = order.get('items', [])
    note = order.get('note', '').lower()
    total = order.get('total_amount', 0)
    
    # تشخیص نوع گروه
    if any(w in note for w in ['خانواده', 'بچه', 'همسر']):
        group_type = "family"
    elif any(w in note for w in ['دوست', 'جمع']):
        group_type = "friends"
    elif any(w in note for w in ['شرکت', 'اداره', 'جلسه']):
        group_type = "work"
    elif len(items) >= 4:
        group_type = "family"
    else:
        group_type = "unknown"
    
    # ذخیره
    profile = db.get_customer_profile(user_id)
    if profile:
        extra_data = profile.get('extra_data', {})
        if isinstance(extra_data, str):
            extra_data = json.loads(extra_data) if extra_data else {}
        
        extra_data['_group_orders'] = extra_data.get('_group_orders', [])
        extra_data['_group_orders'].append({
            "type": group_type,
            "size": len(items),
            "total": total,
            "time": datetime.now().isoformat()
        })
        extra_data['_group_orders'] = extra_data['_group_orders'][-10:]
        
        # تشخیص الگو
        if group_type != "unknown":
            extra_data['social'] = extra_data.get('social', {})
            extra_data['social']['usual_group_type'] = group_type
            extra_data['social']['usual_group_size'] = len(items)
        
        db.update_customer_profile(user_id, extra_data=json.dumps(extra_data, ensure_ascii=False))
    
    return {"learned": True, "group_type": group_type}


# ═══════════════════════════════════════════════════════════════════════════════
# 💾 یادگیری و ذخیره در دیتابیس
# ═══════════════════════════════════════════════════════════════════════════════

def learn_from_chat(user_id: int, message: str, audio_emotion: str = None) -> dict:
    """
    یادگیری از پیام چت و ذخیره در دیتابیس
    """
    import database_pg as db
    
    # استخراج اطلاعات
    extracted = extract_from_message(message)
    
    if not extracted:
        return {"learned": False, "reason": "nothing_extracted"}
    
    # گرفتن پروفایل فعلی
    profile = db.get_customer_profile(user_id)
    
    if not profile:
        # ساخت پروفایل جدید
        db.create_customer_profile(user_id)
        profile = db.get_customer_profile(user_id)
    
    # گرفتن extra_data فعلی
    extra_data = profile.get('extra_data', {})
    if isinstance(extra_data, str):
        try:
            extra_data = json.loads(extra_data) if extra_data else {}
        except:
            extra_data = {}
    
    # ادغام هوشمند
    merged_data = smart_merge(extra_data, extracted)
    
    # ═══════════════════════════════════════════════════════════════
    # آپدیت فیلدهای اصلی (برای Query سریع)
    # ═══════════════════════════════════════════════════════════════
    
    updates = {}
    
    # غذاهای محبوب
    if extracted.get('food', {}).get('favorites'):
        current = json.loads(profile.get('favorite_foods') or '[]')
        new = list(set(current + extracted['food']['favorites']))
        updates['favorite_foods'] = json.dumps(new[-30:], ensure_ascii=False)
        print(f"  🍕 Learned favorites: {extracted['food']['favorites']}")
    
    # آلرژی‌ها (مهم!)
    if extracted.get('food', {}).get('allergies'):
        current = json.loads(profile.get('allergies') or '[]')
        new = list(set(current + extracted['food']['allergies']))
        updates['allergies'] = json.dumps(new, ensure_ascii=False)
        print(f"  ⚠️ Learned allergies: {extracted['food']['allergies']}")
    
    # رژیم غذایی
    if extracted.get('food', {}).get('dietary'):
        current = json.loads(profile.get('dietary_preferences') or '[]')
        new = list(set(current + extracted['food']['dietary']))
        updates['dietary_preferences'] = json.dumps(new, ensure_ascii=False)
        print(f"  🥗 Learned dietary: {extracted['food']['dietary']}")
    
    # تندی
    if extracted.get('food', {}).get('spice_level'):
        updates['spice_level'] = extracted['food']['spice_level']
        print(f"  🌶️ Learned spice: {extracted['food']['spice_level']}")
    
    # ═══════════════════════════════════════════════════════════════
    # متادیتای یادگیری
    # ═══════════════════════════════════════════════════════════════
    
    merged_data['_meta'] = merged_data.get('_meta', {})
    merged_data['_meta']['last_learned'] = datetime.now().isoformat()
    merged_data['_meta']['total_messages'] = merged_data['_meta'].get('total_messages', 0) + 1
    merged_data['_meta']['last_message'] = message[:200]
    
    if audio_emotion:
        merged_data['_meta']['last_voice_emotion'] = audio_emotion
    
    if extracted.get('emotion', {}).get('current_mood'):
        merged_data['_meta']['last_mood'] = extracted['emotion']['current_mood']
    
    # ذخیره نهایی
    updates['extra_data'] = json.dumps(merged_data, ensure_ascii=False)
    
    # آپدیت دیتابیس
    db.update_customer_profile(user_id, **updates)
    
    # آپدیت اسم کاربر - فقط اگه اسم نداره یا خودش گفته "من [اسم] هستم"
    if extracted.get('personal', {}).get('name'):
        extracted_name = extracted['personal']['name']
        # گرفتن اسم فعلی کاربر
        current_user = db.get_user_by_id(user_id)
        current_name = current_user.get('name') if current_user else None
        
        # فقط اگه اسم نداره یا confidence بالاست (مستقیم گفته)
        name_confidence = extracted.get('personal', {}).get('name_confidence', 0.5)
        
        if not current_name:
            # کاربر اسم نداره، ست کن
            db.update_user(user_id, name=extracted_name)
            print(f"  👤 Learned name: {extracted_name}")
        elif name_confidence >= 0.9:
            # confidence خیلی بالا - مستقیم گفته "من X هستم"
            db.update_user(user_id, name=extracted_name)
            print(f"  👤 Updated name: {extracted_name} (high confidence)")
        else:
            print(f"  👤 Skipped name '{extracted_name}' - user already has name: {current_name}")
    
    # لاگ
    categories_learned = [k for k, v in extracted.items() if v and k != '_meta']
    print(f"  🧠 Learned {len(categories_learned)} categories: {categories_learned}")
    
    return {
        "learned": True,
        "categories": categories_learned,
        "extracted": extracted
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 گرفتن پروفایل
# ═══════════════════════════════════════════════════════════════════════════════

def get_full_profile(user_id: int) -> dict:
    """
    برگرداندن پروفایل کامل کاربر
    """
    import database_pg as db
    
    profile = db.get_customer_profile(user_id)
    if not profile:
        return {}
    
    extra_data = profile.get('extra_data', {})
    if isinstance(extra_data, str):
        try:
            extra_data = json.loads(extra_data) if extra_data else {}
        except:
            extra_data = {}
    
    # پارس امن JSON
    def safe_json_parse(val, default=[]):
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except:
                return default
        return default
    
    return {
        'user_id': user_id,
        'favorite_foods': safe_json_parse(profile.get('favorite_foods')),
        'allergies': safe_json_parse(profile.get('allergies')),
        'dietary_preferences': safe_json_parse(profile.get('dietary_preferences')),
        'spice_level': profile.get('spice_level'),
        **extra_data
    }


def get_profile_summary(user_id: int) -> str:
    """
    خلاصه پروفایل برای System Prompt
    """
    profile = get_full_profile(user_id)
    if not profile:
        return "کاربر جدید، اطلاعاتی موجود نیست."
    
    parts = []
    
    # اطلاعات شخصی
    if profile.get('personal'):
        p = profile['personal']
        personal_parts = []
        if p.get('name'): personal_parts.append(f"اسم: {p['name']}")
        if p.get('age'): personal_parts.append(f"سن: {p['age']}")
        if p.get('city'): personal_parts.append(f"شهر: {p['city']}")
        if p.get('job'): personal_parts.append(f"شغل: {p['job']}")
        if p.get('family_size'): personal_parts.append(f"خانواده: {p['family_size']} نفر")
        if personal_parts:
            parts.append("👤 " + "، ".join(personal_parts))
    
    # غذا
    food_parts = []
    if profile.get('favorite_foods'):
        food_parts.append(f"علاقه: {', '.join(profile['favorite_foods'][:5])}")
    if profile.get('allergies'):
        food_parts.append(f"⚠️آلرژی: {', '.join(profile['allergies'])}")
    if profile.get('dietary_preferences'):
        food_parts.append(f"رژیم: {', '.join(profile['dietary_preferences'])}")
    if profile.get('spice_level'):
        food_parts.append(f"تندی: {profile['spice_level']}")
    if profile.get('food', {}).get('portion_size'):
        food_parts.append(f"پرس: {profile['food']['portion_size']}")
    if food_parts:
        parts.append("🍕 " + "، ".join(food_parts))
    
    # سلامت
    if profile.get('health'):
        h = profile['health']
        health_parts = []
        if h.get('chronic_conditions'):
            health_parts.append(f"بیماری: {', '.join(h['chronic_conditions'])}")
        if h.get('diabetes') and h['diabetes'] != 'none':
            health_parts.append(f"دیابت: {h['diabetes']}")
        if h.get('on_diet'):
            health_parts.append("در رژیم")
        if health_parts:
            parts.append("🏥 " + "، ".join(health_parts))
    
    # مالی
    if profile.get('financial', {}).get('budget_level'):
        parts.append(f"💰 بودجه: {profile['financial']['budget_level']}")
    
    # شخصیت
    if profile.get('personality', {}).get('personality_type'):
        parts.append(f"🎭 شخصیت: {profile['personality']['personality_type']}")
    
    # آخرین وضعیت
    if profile.get('_meta'):
        m = profile['_meta']
        if m.get('last_mood'):
            parts.append(f"😊 آخرین حال: {m['last_mood']}")
        if m.get('total_messages'):
            parts.append(f"📊 تعداد پیام: {m['total_messages']}")
    
    return "\n".join(parts) if parts else "اطلاعات کمی موجود است."


def get_warnings(user_id: int) -> List[str]:
    """
    هشدارهای مهم (آلرژی، بیماری)
    """
    profile = get_full_profile(user_id)
    warnings = []
    
    if profile.get('allergies'):
        warnings.append(f"⚠️ آلرژی: {', '.join(profile['allergies'])}")
    
    if profile.get('health', {}).get('chronic_conditions'):
        warnings.append(f"🏥 بیماری: {', '.join(profile['health']['chronic_conditions'])}")
    
    if profile.get('food', {}).get('intolerances'):
        warnings.append(f"⚠️ عدم تحمل: {', '.join(profile['food']['intolerances'])}")
    
    return warnings


# ═══════════════════════════════════════════════════════════════════════════════
# 🖼️ یادگیری از تصویر (چهره، احساس، غذا)
# ═══════════════════════════════════════════════════════════════════════════════

IMAGE_ANALYSIS_PROMPT = '''این تصویر رو کامل تحلیل کن و همه اطلاعات ممکن استخراج کن.

خروجی JSON:
{
    "face_detected": true/false,
    "face_analysis": {
        "emotion": "happy/sad/tired/angry/stressed/neutral/excited",
        "energy_level": "high/medium/low",
        "apparent_age_range": "20-30",
        "gender_guess": "male/female/unknown",
        "wearing_glasses": true/false,
        "has_beard": true/false,
        "hair_color": "black/brown/blonde/gray/red",
        "hair_style": "short/long/bald",
        "skin_tone": "light/medium/dark",
        "confidence": 0.0-1.0
    },
    "style_analysis": {
        "clothing_style": "casual/formal/sporty/traditional",
        "clothing_colors": ["رنگ‌ها"],
        "visible_brands": ["برندها"],
        "accessories": ["عینک/ساعت/جواهر"],
        "estimated_budget": "low/medium/high/luxury"
    },
    "environment": {
        "location_type": "home/office/restaurant/outdoor/car/gym/cafe",
        "home_style": "modern/traditional/minimal/luxurious",
        "cleanliness": "clean/messy/average",
        "time_of_day_guess": "morning/afternoon/evening/night",
        "weather_guess": "sunny/cloudy/rainy",
        "alone_or_group": "alone/with_others",
        "group_size": 0
    },
    "people_detected": {
        "count": 0,
        "children_visible": true/false,
        "children_ages_estimate": [],
        "elderly_visible": true/false,
        "seems_family": true/false
    },
    "pets_detected": {
        "has_pet": true/false,
        "pet_type": "dog/cat/bird/fish/other",
        "pet_breed_guess": "نژاد",
        "pet_size": "small/medium/large"
    },
    "vehicle_detected": {
        "has_vehicle": true/false,
        "vehicle_type": "car/motorcycle/bicycle",
        "vehicle_brand": "برند",
        "vehicle_class": "economy/mid/luxury/sport"
    },
    "food_detected": true/false,
    "food_analysis": {
        "food_name": "نام غذا",
        "food_type": "fast_food/traditional/healthy/dessert/homemade",
        "cuisine_type": "iranian/italian/chinese/american",
        "ingredients": ["مواد"],
        "is_homemade": true/false,
        "portion_size": "small/medium/large",
        "healthiness": "healthy/moderate/unhealthy"
    },
    "activity_detected": {
        "current_activity": "eating/working/relaxing/exercising/traveling",
        "fitness_indicators": "fit/average/overweight",
        "lifestyle_guess": "active/sedentary/balanced"
    },
    "suggestions": {
        "food_recommendation": "پیشنهاد غذا",
        "reason": "دلیل"
    }
}

فقط JSON برگردون. فیلدهایی که تشخیص ندادی رو ننویس.'''


def learn_from_image(user_id: int, image_base64: str) -> dict:
    """
    🖼️ یادگیری از تصویر کاربر
    - تشخیص چهره و احساس
    - پیشنهاد غذا بر اساس حال
    - ذخیره در پروفایل
    """
    import database_pg as db
    import requests
    from config import GAPGPT_API_KEY
    
    try:
        # تحلیل تصویر با Gemini 3
        url = "https://api.gapgpt.app/v1beta/models/gemini-3-pro-image-preview:generateContent"
        headers = {"Authorization": f"Bearer {GAPGPT_API_KEY}"}
        
        # حذف prefix base64
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        
        data = {
            "contents": [{
                "parts": [
                    {"text": IMAGE_ANALYSIS_PROMPT},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_base64}}
                ]
            }]
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=90)
        
        if not response.ok:
            return {"learned": False, "error": f"API error: {response.status_code}"}
        
        result_text = response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        
        # پارس JSON
        try:
            clean = result_text.replace("```json", "").replace("```", "").strip()
            analysis = json.loads(clean)
        except:
            return {"learned": False, "error": "JSON parse error", "raw": result_text}
        
        # ═══════════════════════════════════════════════════════════════
        # ذخیره در پروفایل کاربر
        # ═══════════════════════════════════════════════════════════════
        
        profile = db.get_customer_profile(user_id)
        if not profile:
            db.create_customer_profile(user_id)
            profile = db.get_customer_profile(user_id)
        
        extra_data = profile.get('extra_data', {})
        if isinstance(extra_data, str):
            try:
                extra_data = json.loads(extra_data) if extra_data else {}
            except:
                extra_data = {}
        
        extra_data['_meta'] = extra_data.get('_meta', {})
        extra_data['personal'] = extra_data.get('personal', {})
        extra_data['lifestyle'] = extra_data.get('lifestyle', {})
        extra_data['financial'] = extra_data.get('financial', {})
        extra_data['preferences'] = extra_data.get('preferences', {})
        
        # ═══════════════════════════════════════════════════════════════
        # 👤 تحلیل چهره
        # ═══════════════════════════════════════════════════════════════
        if analysis.get('face_detected'):
            face = analysis.get('face_analysis', {})
            
            # تاریخچه احساسات
            if 'emotion_history' not in extra_data:
                extra_data['emotion_history'] = []
            
            extra_data['emotion_history'].append({
                'emotion': face.get('emotion', 'neutral'),
                'energy': face.get('energy_level', 'medium'),
                'timestamp': datetime.now().isoformat(),
                'source': 'face'
            })
            extra_data['emotion_history'] = extra_data['emotion_history'][-50:]
            
            # متا
            extra_data['_meta']['last_face_emotion'] = face.get('emotion')
            extra_data['_meta']['last_energy_level'] = face.get('energy_level')
            extra_data['_meta']['last_image_analysis'] = datetime.now().isoformat()
            
            # ویژگی‌های شخصی
            if face.get('apparent_age_range') and not extra_data['personal'].get('age'):
                extra_data['personal']['apparent_age_range'] = face.get('apparent_age_range')
            if face.get('gender_guess') and face.get('gender_guess') != 'unknown':
                if not extra_data['personal'].get('gender'):
                    extra_data['personal']['gender'] = face.get('gender_guess')
            if face.get('wearing_glasses'):
                extra_data['personal']['wearing_glasses'] = True
            if face.get('has_beard'):
                extra_data['personal']['has_beard'] = True
            if face.get('hair_color'):
                extra_data['personal']['hair_color'] = face.get('hair_color')
            if face.get('hair_style'):
                extra_data['personal']['hair_style'] = face.get('hair_style')
        
        # ═══════════════════════════════════════════════════════════════
        # 👔 تحلیل استایل و لباس
        # ═══════════════════════════════════════════════════════════════
        if analysis.get('style_analysis'):
            style = analysis.get('style_analysis', {})
            
            if style.get('clothing_style'):
                extra_data['lifestyle']['clothing_style'] = style.get('clothing_style')
            if style.get('clothing_colors'):
                if 'favorite_colors' not in extra_data['preferences']:
                    extra_data['preferences']['favorite_colors'] = []
                extra_data['preferences']['favorite_colors'].extend(style.get('clothing_colors', []))
                extra_data['preferences']['favorite_colors'] = list(set(extra_data['preferences']['favorite_colors']))[-10:]
            if style.get('visible_brands'):
                if 'favorite_brands' not in extra_data['preferences']:
                    extra_data['preferences']['favorite_brands'] = []
                extra_data['preferences']['favorite_brands'].extend(style.get('visible_brands', []))
                extra_data['preferences']['favorite_brands'] = list(set(extra_data['preferences']['favorite_brands']))[-20:]
            if style.get('accessories'):
                extra_data['lifestyle']['accessories'] = style.get('accessories')
            if style.get('estimated_budget'):
                extra_data['financial']['estimated_budget'] = style.get('estimated_budget')
        
        # ═══════════════════════════════════════════════════════════════
        # 🏠 محیط
        # ═══════════════════════════════════════════════════════════════
        if analysis.get('environment'):
            env = analysis.get('environment', {})
            extra_data['_meta']['last_location_type'] = env.get('location_type')
            extra_data['_meta']['last_time_of_day'] = env.get('time_of_day_guess')
            
            if env.get('home_style'):
                extra_data['lifestyle']['home_style'] = env.get('home_style')
            if env.get('alone_or_group'):
                extra_data['_meta']['social_context'] = env.get('alone_or_group')
        
        # ═══════════════════════════════════════════════════════════════
        # 👨‍👩‍👧‍👦 افراد در تصویر
        # ═══════════════════════════════════════════════════════════════
        if analysis.get('people_detected'):
            people = analysis.get('people_detected', {})
            
            if people.get('children_visible') and people.get('children_ages_estimate'):
                extra_data['personal']['has_children'] = True
                extra_data['personal']['children_ages_estimate'] = people.get('children_ages_estimate')
            if people.get('seems_family'):
                extra_data['personal']['family_oriented'] = True
                if people.get('count'):
                    extra_data['personal']['family_size_estimate'] = people.get('count')
        
        # ═══════════════════════════════════════════════════════════════
        # 🐕 حیوان خانگی
        # ═══════════════════════════════════════════════════════════════
        if analysis.get('pets_detected', {}).get('has_pet'):
            pet = analysis.get('pets_detected', {})
            extra_data['personal']['has_pet'] = True
            extra_data['personal']['pet_type'] = pet.get('pet_type')
            if pet.get('pet_breed_guess'):
                extra_data['personal']['pet_breed'] = pet.get('pet_breed_guess')
        
        # ═══════════════════════════════════════════════════════════════
        # 🚗 وسیله نقلیه
        # ═══════════════════════════════════════════════════════════════
        if analysis.get('vehicle_detected', {}).get('has_vehicle'):
            vehicle = analysis.get('vehicle_detected', {})
            extra_data['lifestyle']['vehicle_type'] = vehicle.get('vehicle_type')
            if vehicle.get('vehicle_brand'):
                extra_data['lifestyle']['vehicle_brand'] = vehicle.get('vehicle_brand')
            if vehicle.get('vehicle_class'):
                extra_data['financial']['vehicle_class'] = vehicle.get('vehicle_class')
        
        # ═══════════════════════════════════════════════════════════════
        # 🍕 غذا
        # ═══════════════════════════════════════════════════════════════
        if analysis.get('food_detected'):
            food = analysis.get('food_analysis', {})
            
            if 'seen_foods' not in extra_data:
                extra_data['seen_foods'] = []
            
            extra_data['seen_foods'].append({
                'food': food.get('food_name'),
                'type': food.get('food_type'),
                'cuisine': food.get('cuisine_type'),
                'healthy': food.get('healthiness'),
                'timestamp': datetime.now().isoformat()
            })
            extra_data['seen_foods'] = extra_data['seen_foods'][-30:]
            
            # ترجیحات غذایی
            if food.get('cuisine_type'):
                if 'favorite_cuisines' not in extra_data['preferences']:
                    extra_data['preferences']['favorite_cuisines'] = []
                if food.get('cuisine_type') not in extra_data['preferences']['favorite_cuisines']:
                    extra_data['preferences']['favorite_cuisines'].append(food.get('cuisine_type'))
            
            if food.get('portion_size'):
                extra_data['preferences']['portion_preference'] = food.get('portion_size')
        
        # ═══════════════════════════════════════════════════════════════
        # 🏃 فعالیت و سبک زندگی
        # ═══════════════════════════════════════════════════════════════
        if analysis.get('activity_detected'):
            activity = analysis.get('activity_detected', {})
            
            if activity.get('current_activity'):
                extra_data['_meta']['last_activity'] = activity.get('current_activity')
            if activity.get('fitness_indicators'):
                extra_data['lifestyle']['fitness_level'] = activity.get('fitness_indicators')
            if activity.get('lifestyle_guess'):
                extra_data['lifestyle']['activity_level'] = activity.get('lifestyle_guess')
        
        # ذخیره نهایی
        db.update_customer_profile(user_id, extra_data=json.dumps(extra_data, ensure_ascii=False))
        
        print(f"  🖼️ Image learned: emotion={analysis.get('face_analysis', {}).get('emotion')}")
        
        return {
            "learned": True,
            "analysis": analysis,
            "suggestion": analysis.get('suggestions', {})
        }
        
    except Exception as e:
        print(f"❌ Image learning error: {e}")
        return {"learned": False, "error": str(e)}


def get_food_suggestion_by_mood(user_id: int) -> dict:
    """
    🍕 پیشنهاد غذا بر اساس حال کاربر
    """
    import database_pg as db
    
    profile = db.get_customer_profile(user_id)
    if not profile:
        return {"suggestion": "یه غذای خوشمزه!", "reason": "پروفایل پیدا نشد"}
    
    extra_data = profile.get('extra_data', {})
    if isinstance(extra_data, str):
        try:
            extra_data = json.loads(extra_data) if extra_data else {}
        except:
            extra_data = {}
    
    meta = extra_data.get('_meta', {})
    emotion = meta.get('last_face_emotion') or meta.get('last_mood', 'neutral')
    energy = meta.get('last_energy_level', 'medium')
    
    # پیشنهادات بر اساس احساس
    suggestions = {
        'happy': {
            'foods': ['پیتزا', 'برگر', 'پاستا', 'سوشی'],
            'reason': 'حالت خوبه! یه غذای خوشمزه بخور 🎉'
        },
        'sad': {
            'foods': ['سوپ گرم', 'شکلات', 'بستنی', 'کیک'],
            'reason': 'یه چیز گرم و دلچسب حالتو بهتر میکنه 🤗'
        },
        'tired': {
            'foods': ['قهوه', 'انرژی‌زا', 'میوه', 'آش'],
            'reason': 'خسته به نظر میرسی! یه چیز انرژی‌بخش بخور ☕'
        },
        'stressed': {
            'foods': ['چای', 'شکلات تلخ', 'ماست', 'سالاد'],
            'reason': 'استرس داری! یه چیز آرامش‌بخش بخور 🍵'
        },
        'angry': {
            'foods': ['نوشیدنی سرد', 'بستنی', 'اسموتی'],
            'reason': 'یه چیز خنک آرومت میکنه 🧊'
        },
        'excited': {
            'foods': ['پیتزا پارتی', 'فینگرفود', 'ناچو'],
            'reason': 'هیجان‌زده‌ای! بزن بریم پارتی 🎊'
        },
        'neutral': {
            'foods': ['غذای روز', 'چلوکباب', 'ساندویچ'],
            'reason': 'یه غذای معمولی و خوشمزه!'
        }
    }
    
    mood_data = suggestions.get(emotion, suggestions['neutral'])
    
    # اگه انرژی کمه، غذای سبک‌تر
    if energy == 'low':
        mood_data['foods'] = ['سوپ', 'سالاد', 'میوه', 'آبمیوه']
        mood_data['reason'] += ' (انرژیت کمه، سبک بخور)'
    
    return {
        'emotion': emotion,
        'energy': energy,
        'suggested_foods': mood_data['foods'],
        'reason': mood_data['reason']
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 🎤 یادگیری از صدا
# ═══════════════════════════════════════════════════════════════════════════════

AUDIO_ANALYSIS_PROMPT = '''این فایل صوتی فارسی رو تحلیل کن:

1. متن گفته شده رو دقیق بنویس
2. از لحن و صدا اطلاعات استخراج کن

خروجی JSON:
{
    "text": "متن گفته شده",
    "voice_analysis": {
        "emotion": "happy/sad/angry/tired/stressed/excited/neutral",
        "energy_level": "high/medium/low",
        "speaking_speed": "fast/normal/slow",
        "voice_pitch": "high/medium/low",
        "confidence_in_speech": "confident/hesitant/nervous",
        "formality": "formal/informal/friendly",
        "age_estimate": "young/middle/elderly"
    },
    "background_analysis": {
        "has_background_noise": true/false,
        "noise_type": "traffic/children/music/office/home/outdoor",
        "seems_alone": true/false
    },
    "accent_analysis": {
        "has_accent": true/false,
        "accent_type": "tehrani/isfahani/shirazi/mashhadi/tabriz/other",
        "dialect_guess": "محلی تخمینی"
    },
    "personality_hints": {
        "personality_type": "extrovert/introvert/ambivert",
        "communication_style": "direct/indirect/friendly/professional",
        "mood_pattern": "stable/variable"
    }
}

فقط JSON برگردون.'''


def learn_from_audio(user_id: int, audio_base64: str, mime_type: str = "audio/webm") -> dict:
    """
    🎤 یادگیری از صدای کاربر
    - تشخیص احساس از لحن
    - تخمین شخصیت
    - تشخیص لهجه
    """
    import database_pg as db
    import requests
    from config import GAPGPT_API_KEY
    
    try:
        url = "https://api.gapgpt.app/v1beta/models/gemini-2.5-flash:generateContent"
        headers = {"Authorization": f"Bearer {GAPGPT_API_KEY}"}
        
        data = {
            "contents": [{
                "parts": [
                    {"text": AUDIO_ANALYSIS_PROMPT},
                    {"inline_data": {"mime_type": mime_type, "data": audio_base64}}
                ]
            }]
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=90)
        
        if not response.ok:
            return {"learned": False, "error": f"API error: {response.status_code}"}
        
        result_text = response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        
        # پارس JSON
        try:
            clean = result_text.replace("```json", "").replace("```", "").strip()
            analysis = json.loads(clean)
        except:
            return {"learned": False, "error": "JSON parse error", "text": result_text}
        
        # ═══════════════════════════════════════════════════════════════
        # ذخیره در پروفایل
        # ═══════════════════════════════════════════════════════════════
        
        profile = db.get_customer_profile(user_id)
        if not profile:
            db.create_customer_profile(user_id)
            profile = db.get_customer_profile(user_id)
        
        extra_data = profile.get('extra_data', {})
        if isinstance(extra_data, str):
            try:
                extra_data = json.loads(extra_data) if extra_data else {}
            except:
                extra_data = {}
        
        extra_data['_meta'] = extra_data.get('_meta', {})
        extra_data['personal'] = extra_data.get('personal', {})
        extra_data['personality'] = extra_data.get('personality', {})
        extra_data['lifestyle'] = extra_data.get('lifestyle', {})
        
        # تحلیل صدا
        if analysis.get('voice_analysis'):
            voice = analysis.get('voice_analysis', {})
            
            # تاریخچه احساس صوتی
            if 'voice_emotion_history' not in extra_data:
                extra_data['voice_emotion_history'] = []
            
            extra_data['voice_emotion_history'].append({
                'emotion': voice.get('emotion', 'neutral'),
                'energy': voice.get('energy_level', 'medium'),
                'speed': voice.get('speaking_speed', 'normal'),
                'timestamp': datetime.now().isoformat()
            })
            extra_data['voice_emotion_history'] = extra_data['voice_emotion_history'][-50:]
            
            extra_data['_meta']['last_voice_emotion'] = voice.get('emotion')
            extra_data['_meta']['last_voice_energy'] = voice.get('energy_level')
            extra_data['_meta']['last_audio_analysis'] = datetime.now().isoformat()
            
            # شخصیت
            if voice.get('confidence_in_speech'):
                extra_data['personality']['speech_confidence'] = voice.get('confidence_in_speech')
            if voice.get('formality'):
                extra_data['personality']['formality'] = voice.get('formality')
            if voice.get('age_estimate'):
                if not extra_data['personal'].get('age_estimate'):
                    extra_data['personal']['age_estimate_voice'] = voice.get('age_estimate')
        
        # پس‌زمینه
        if analysis.get('background_analysis'):
            bg = analysis.get('background_analysis', {})
            
            if bg.get('noise_type'):
                extra_data['_meta']['last_background'] = bg.get('noise_type')
                
                # تخمین محل
                if bg.get('noise_type') == 'office':
                    extra_data['lifestyle']['work_type_guess'] = 'office'
                elif bg.get('noise_type') == 'children':
                    extra_data['personal']['has_children'] = True
                elif bg.get('noise_type') == 'traffic':
                    extra_data['_meta']['calling_from'] = 'outdoor/car'
        
        # لهجه
        if analysis.get('accent_analysis', {}).get('has_accent'):
            accent = analysis.get('accent_analysis', {})
            
            if accent.get('accent_type') and accent.get('accent_type') != 'tehrani':
                extra_data['personal']['accent'] = accent.get('accent_type')
                
                # تخمین شهر از لهجه
                accent_to_city = {
                    'isfahani': 'اصفهان',
                    'shirazi': 'شیراز',
                    'mashhadi': 'مشهد',
                    'tabriz': 'تبریز',
                }
                if accent.get('accent_type') in accent_to_city:
                    if not extra_data['personal'].get('city'):
                        extra_data['personal']['city_guess'] = accent_to_city[accent.get('accent_type')]
        
        # شخصیت
        if analysis.get('personality_hints'):
            pers = analysis.get('personality_hints', {})
            
            if pers.get('personality_type'):
                extra_data['personality']['type'] = pers.get('personality_type')
            if pers.get('communication_style'):
                extra_data['personality']['communication_style'] = pers.get('communication_style')
        
        # ذخیره
        db.update_customer_profile(user_id, extra_data=json.dumps(extra_data, ensure_ascii=False))
        
        print(f"  🎤 Audio learned: emotion={analysis.get('voice_analysis', {}).get('emotion')}")
        
        return {
            "learned": True,
            "text": analysis.get('text', ''),
            "analysis": analysis
        }
        
    except Exception as e:
        print(f"❌ Audio learning error: {e}")
        return {"learned": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# 🧪 تست
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🧪 تست Smart Learner\n")
    
    test_messages = [
        "سلام، اسمم علی محمدی هست، ۲۸ سالمه و تهران سعادت‌آباد زندگی میکنم. مهندس نرم‌افزارم.",
        "من پیتزا و پاستا خیلی دوست دارم ولی به گلوتن و لاکتوز حساسیت دارم",
        "گیاهی هستم و غذای تند نمیخورم، پرس کوچیک میخوام",
        "دیابت نوع ۲ دارم و فشار خونم بالاست، باید کم‌نمک و کم‌قند بخورم",
        "خیلی گرسنمه و عجله دارم، یه چیز سریع میخوام!",
        "بودجم زیاد نیست، یه چیز ارزون و خوشمزه پیشنهاد بده",
        "امشب تولد همسرمه، میخوام یه شام رمانتیک سفارش بدم",
        "۲ تا بچه دارم، ۵ و ۸ ساله، برای اونا هم غذا میخوام",
        "شیر و ماست بهم نمیسازه، لطفاً بدون لبنیات باشه",
        "من جمعه‌ها معمولاً ناهار خانوادگی داریم، ۶ نفریم",
    ]
    
    for i, msg in enumerate(test_messages, 1):
        print(f"\n{'='*60}")
        print(f"📝 تست {i}: {msg[:50]}...")
        print('='*60)
        
        result = extract_from_message(msg)
        
        if result:
            print(f"\n✅ استخراج شد:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"\n❌ چیزی استخراج نشد")
    
    print("\n\n" + "="*60)
    print("🎯 تست کامل شد!")
