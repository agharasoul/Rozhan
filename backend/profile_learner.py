"""
🧠 Profile Learner
یادگیری خودکار پروفایل مشتری از رفتار و مکالمات

این سیستم به مرور زمان:
- از سفارشات یاد می‌گیره
- از چت‌ها اطلاعات استخراج می‌کنه  
- ترجیحات رو کشف می‌کنه
- پیش‌بینی می‌کنه
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import Counter
import db
import emotion_detector

# ═══════════════════════════════════════════════════════════
# 🍕 لیست غذاها برای تشخیص در چت
# ═══════════════════════════════════════════════════════════

FOOD_KEYWORDS = {
    # پیتزا
    "پیتزا", "pizza", "پپرونی", "مارگاریتا", "سبزیجات",
    # برگر
    "برگر", "burger", "همبرگر", "چیزبرگر", "دبل برگر",
    # ایرانی
    "کباب", "جوجه", "چلو", "برنج", "خورشت", "قورمه", "قیمه",
    "زرشک پلو", "باقالی پلو", "تهچین", "کوبیده", "سلطانی",
    # فست فود
    "ساندویچ", "هات داگ", "سوخاری", "مرغ سوخاری", "کنتاکی",
    # نوشیدنی
    "نوشابه", "دوغ", "آب", "چای", "قهوه", "نسکافه",
    # دسر
    "دسر", "کیک", "بستنی", "شیرینی",
    # سالاد
    "سالاد", "فصل", "سزار",
}

ALLERGY_KEYWORDS = {
    "آلرژی", "حساسیت", "نمی‌تونم بخورم", "نباید بخورم",
    "بادام", "گردو", "لاکتوز", "شیر", "گلوتن", "گندم",
    "تخم مرغ", "سویا", "ماهی", "میگو",
}

DIET_KEYWORDS = {
    "گیاهی": ["گیاهی", "وگان", "گوشت نمی‌خورم", "بدون گوشت"],
    "حلال": ["حلال"],
    "بدون گلوتن": ["بدون گلوتن", "گلوتن فری"],
    "کم کالری": ["رژیمی", "کم کالری", "سبک"],
    "بدون لاکتوز": ["بدون لاکتوز", "شیر نخورم"],
}

SPICE_KEYWORDS = {
    "تند": ["تند", "فلفل", "خیلی تند", "با فلفل"],
    "ملایم": ["ملایم", "کم تند", "بدون فلفل"],
    "معمولی": ["معمولی", "نرمال"],
}


# ═══════════════════════════════════════════════════════════
# 📊 آپدیت آمار از سفارشات
# ═══════════════════════════════════════════════════════════

def update_profile_from_order(user_id: int, order_data: dict):
    """
    بعد از هر سفارش، پروفایل آپدیت میشه
    
    order_data = {
        "total_amount": 250000,
        "items": ["پیتزا پپرونی", "نوشابه"],
        "payment_method": "online",
        "delivery_type": "delivery"
    }
    """
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # گرفتن پروفایل فعلی
    cursor.execute("SELECT * FROM customer_profiles WHERE user_id = ?", (user_id,))
    profile = cursor.fetchone()
    
    if not profile:
        cursor.execute("INSERT INTO customer_profiles (user_id) VALUES (?)", (user_id,))
        conn.commit()
        cursor.execute("SELECT * FROM customer_profiles WHERE user_id = ?", (user_id,))
        profile = cursor.fetchone()
    
    profile = dict(profile)
    
    # آپدیت آمار سفارش
    total_orders = (profile.get('total_orders') or 0) + 1
    total_spent = (profile.get('total_spent') or 0) + order_data.get('total_amount', 0)
    avg_order_value = total_spent / total_orders if total_orders > 0 else 0
    
    # آپدیت غذاهای مورد علاقه
    favorite_foods = json.loads(profile.get('favorite_foods') or '[]')
    for item in order_data.get('items', []):
        if item not in favorite_foods:
            favorite_foods.append(item)
        # فقط ۲۰ تا نگه دار
        favorite_foods = favorite_foods[-20:]
    
    # تشخیص فرکانس سفارش
    first_order = profile.get('first_order_date')
    if not first_order:
        first_order = datetime.now().isoformat()
        order_frequency = 'new'
    else:
        # محاسبه فرکانس
        days_since_first = (datetime.now() - datetime.fromisoformat(first_order)).days
        if days_since_first > 0:
            orders_per_month = (total_orders / days_since_first) * 30
            if orders_per_month >= 15:
                order_frequency = 'daily'
            elif orders_per_month >= 4:
                order_frequency = 'weekly'
            elif orders_per_month >= 1:
                order_frequency = 'monthly'
            else:
                order_frequency = 'rarely'
        else:
            order_frequency = 'new'
    
    # تعیین سگمنت مشتری
    if total_orders == 1:
        segment = 'new'
    elif total_orders >= 20 or total_spent >= 5000000:
        segment = 'vip'
    elif total_orders >= 5:
        segment = 'regular'
    else:
        segment = 'new'
    
    # تعیین سطح وفاداری
    if total_spent >= 10000000:
        tier = 'diamond'
    elif total_spent >= 5000000:
        tier = 'platinum'
    elif total_spent >= 2000000:
        tier = 'gold'
    elif total_spent >= 500000:
        tier = 'silver'
    else:
        tier = 'bronze'
    
    # محاسبه ریسک ترک
    last_order = profile.get('last_order_date')
    if last_order:
        days_inactive = (datetime.now() - datetime.fromisoformat(last_order)).days
        if order_frequency == 'daily' and days_inactive > 7:
            churn_risk = min(days_inactive / 30, 1.0)
        elif order_frequency == 'weekly' and days_inactive > 21:
            churn_risk = min(days_inactive / 60, 1.0)
        else:
            churn_risk = 0.0
    else:
        churn_risk = 0.0
    
    # ذخیره
    cursor.execute("""
        UPDATE customer_profiles SET
            total_orders = ?,
            total_spent = ?,
            avg_order_value = ?,
            favorite_foods = ?,
            first_order_date = COALESCE(first_order_date, ?),
            last_order_date = ?,
            order_frequency = ?,
            customer_segment = ?,
            loyalty_tier = ?,
            churn_risk = ?,
            preferred_payment = COALESCE(preferred_payment, ?),
            preferred_delivery_type = COALESCE(preferred_delivery_type, ?),
            lifetime_value = ?,
            last_profile_update = ?
        WHERE user_id = ?
    """, (
        total_orders,
        total_spent,
        avg_order_value,
        json.dumps(favorite_foods, ensure_ascii=False),
        first_order,
        datetime.now().isoformat(),
        order_frequency,
        segment,
        tier,
        churn_risk,
        order_data.get('payment_method'),
        order_data.get('delivery_type'),
        total_spent,  # lifetime_value = total_spent
        datetime.now().isoformat(),
        user_id
    ))
    
    conn.commit()
    conn.close()
    
    print(f"📊 Profile updated: {segment} customer, {tier} tier, {total_orders} orders")
    return True


# ═══════════════════════════════════════════════════════════
# 💬 یادگیری از چت
# ═══════════════════════════════════════════════════════════

def learn_from_chat(user_id: int, message: str):
    """
    از پیام‌های چت یاد می‌گیره
    
    مثال:
    - "پیتزا دوست دارم" → favorite_foods += پیتزا
    - "به بادام آلرژی دارم" → allergies += بادام
    - "غذای تند نمی‌خورم" → spice_level = none
    """
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # گرفتن پروفایل
    cursor.execute("SELECT * FROM customer_profiles WHERE user_id = ?", (user_id,))
    profile = cursor.fetchone()
    if not profile:
        cursor.execute("INSERT INTO customer_profiles (user_id) VALUES (?)", (user_id,))
        conn.commit()
        cursor.execute("SELECT * FROM customer_profiles WHERE user_id = ?", (user_id,))
        profile = cursor.fetchone()
    
    profile = dict(profile)
    message_lower = message.lower()
    updates = {}
    
    # 1️⃣ تشخیص غذاهای مورد علاقه
    favorite_foods = json.loads(profile.get('favorite_foods') or '[]')
    positive_triggers = [
        "دوست", "می خو", "مي خو", "میخو", "ميخو", "هوس", "میل دارم", "بخورم", "میخورم", "می‌خورم", "بده"
    ]
    negative_triggers = [
        "دوست ندارم", "نمی‌خورم", "نخورم", "بدم میاد", "متنفرم از"
    ]

    for food in FOOD_KEYWORDS:
        if food in message_lower:
            # اگر جمله منفی بود، این غذا رو به عنوان علاقه یاد نگیریم
            if any(neg in message_lower for neg in negative_triggers):
                continue

            # اگر یکی از تریگرهای مثبت دیده شد، به علاقه‌ها اضافه کن
            if any(pos in message_lower for pos in positive_triggers):
                if food not in favorite_foods:
                    favorite_foods.append(food)
                    print(f"  🍕 Learned: loves {food}")
    
    if favorite_foods != json.loads(profile.get('favorite_foods') or '[]'):
        updates['favorite_foods'] = json.dumps(favorite_foods[-20:], ensure_ascii=False)
    
    # 2️⃣ تشخیص آلرژی
    allergies = json.loads(profile.get('allergies') or '[]')
    for keyword in ALLERGY_KEYWORDS:
        if keyword in message_lower:
            # استخراج ماده آلرژی‌زا
            for allergen in ["بادام", "گردو", "لاکتوز", "شیر", "گلوتن", "تخم مرغ", "سویا", "ماهی", "میگو"]:
                if allergen in message_lower and allergen not in allergies:
                    allergies.append(allergen)
                    print(f"  ⚠️ Learned: allergic to {allergen}")
    
    if allergies != json.loads(profile.get('allergies') or '[]'):
        updates['allergies'] = json.dumps(allergies, ensure_ascii=False)
    
    # 3️⃣ تشخیص رژیم غذایی
    dietary = json.loads(profile.get('dietary_preferences') or '[]')
    for diet, keywords in DIET_KEYWORDS.items():
        for kw in keywords:
            if kw in message_lower and diet not in dietary:
                dietary.append(diet)
                print(f"  🥗 Learned: diet = {diet}")
    
    if dietary != json.loads(profile.get('dietary_preferences') or '[]'):
        updates['dietary_preferences'] = json.dumps(dietary, ensure_ascii=False)
    
    # 4️⃣ تشخیص تندی
    for level, keywords in SPICE_KEYWORDS.items():
        for kw in keywords:
            if kw in message_lower:
                if "نمی‌خورم" in message_lower or "نه" in message_lower:
                    if level == "تند":
                        updates['spice_level'] = 'none'
                        print(f"  🌶️ Learned: no spicy")
                else:
                    spice_map = {"تند": "hot", "ملایم": "mild", "معمولی": "medium"}
                    updates['spice_level'] = spice_map.get(level, 'medium')
                    print(f"  🌶️ Learned: spice = {level}")
    
    # 5️⃣ تشخیص نام
    # کلماتی که اسم نیستن
    NOT_NAMES = {"گیاهی", "وگان", "متاهل", "مجرد", "راضی", "ناراضی", "گرسنه", "سیر"}
    
    name_patterns = [
        r"اسم(?:م|ـم)?\s+([^\s]+)",
        r"من\s+([^\s]+)\s+هستم",
    ]
    for pattern in name_patterns:
        match = re.search(pattern, message)
        if match:
            name = match.group(1).strip()
            # چک کن اسم واقعی باشه
            if len(name) > 1 and len(name) < 30 and name not in NOT_NAMES:
                cursor.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
                print(f"  👤 Learned: name = {name}")
    
    # ذخیره آپدیت‌ها
    if updates:
        updates['last_profile_update'] = datetime.now().isoformat()
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [user_id]
        cursor.execute(f"UPDATE customer_profiles SET {set_clause} WHERE user_id = ?", values)
        conn.commit()
    
    conn.close()
    
    # 🤖 یادگیری هوشمند - کشف فیلدهای جدید
    try:
        smart_learn(user_id, message)
    except:
        pass
    
    # 🎭 تشخیص و یادگیری احساسات
    try:
        emotion_detector.learn_emotion(user_id, message)
    except:
        pass
    
    return len(updates) > 0


# ═══════════════════════════════════════════════════════════
# 🎯 دریافت پیشنهادات شخصی
# ═══════════════════════════════════════════════════════════

def get_personalized_suggestions(user_id: int) -> Dict:
    """
    پیشنهادات شخصی بر اساس پروفایل
    """
    profile = db.get_customer_profile(user_id)
    if not profile:
        return {"suggestions": [], "message": "کاربر جدید - بدون پروفایل"}
    
    suggestions = []
    
    # بر اساس غذاهای مورد علاقه
    favorites = profile.get('favorite_foods', [])
    if favorites:
        suggestions.append({
            "type": "favorite",
            "message": f"🍕 بر اساس علاقه شما به {favorites[-1]}",
            "items": favorites[-3:]
        })
    
    # هشدار آلرژی
    allergies = profile.get('allergies', [])
    if allergies:
        suggestions.append({
            "type": "warning", 
            "message": f"⚠️ یادآوری: حساسیت به {', '.join(allergies)}",
            "items": allergies
        })
    
    # پیشنهاد وفاداری
    tier = profile.get('loyalty_tier', 'bronze')
    points = profile.get('loyalty_points', 0)
    if tier in ['gold', 'platinum', 'diamond']:
        suggestions.append({
            "type": "loyalty",
            "message": f"⭐ مشتری {tier} - {points} امتیاز",
            "items": []
        })
    
    return {
        "suggestions": suggestions,
        "profile_summary": {
            "segment": profile.get('customer_segment', 'new'),
            "tier": tier,
            "total_orders": profile.get('total_orders', 0),
            "avg_order": profile.get('avg_order_value', 0),
        }
    }


# ═══════════════════════════════════════════════════════════
# 📈 تحلیل روزانه (برای cron job)
# ═══════════════════════════════════════════════════════════

def daily_profile_analysis():
    """
    تحلیل روزانه همه پروفایل‌ها
    - آپدیت ریسک ترک
    - آپدیت سگمنت
    - ارسال هشدار برای مشتریان at_risk
    """
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM customer_profiles")
    profiles = cursor.fetchall()
    
    at_risk_users = []
    
    for profile in profiles:
        profile = dict(profile)
        user_id = profile['user_id']
        
        # محاسبه ریسک ترک
        last_order = profile.get('last_order_date')
        if last_order:
            days_inactive = (datetime.now() - datetime.fromisoformat(last_order)).days
            freq = profile.get('order_frequency', 'monthly')
            
            if freq == 'daily' and days_inactive > 7:
                churn_risk = min(days_inactive / 14, 1.0)
            elif freq == 'weekly' and days_inactive > 21:
                churn_risk = min(days_inactive / 45, 1.0)
            elif freq == 'monthly' and days_inactive > 60:
                churn_risk = min(days_inactive / 90, 1.0)
            else:
                churn_risk = 0.0
            
            # آپدیت سگمنت
            if churn_risk > 0.7:
                segment = 'churned'
            elif churn_risk > 0.3:
                segment = 'at_risk'
                at_risk_users.append(user_id)
            else:
                total = profile.get('total_orders', 0)
                spent = profile.get('total_spent', 0)
                if total >= 20 or spent >= 5000000:
                    segment = 'vip'
                elif total >= 5:
                    segment = 'regular'
                else:
                    segment = 'new'
            
            cursor.execute("""
                UPDATE customer_profiles 
                SET churn_risk = ?, customer_segment = ?
                WHERE user_id = ?
            """, (churn_risk, segment, user_id))
    
    conn.commit()
    conn.close()
    
    print(f"📈 Daily analysis complete: {len(at_risk_users)} at-risk customers")
    return at_risk_users


# ═══════════════════════════════════════════════════════════
# 🤖 یادگیری هوشمند - ذخیره هر اطلاعات جدید
# ═══════════════════════════════════════════════════════════

# الگوهایی که نشون‌دهنده اطلاعات شخصی هستن
INFO_PATTERNS = [
    # اسم - فقط وقتی واقعاً اسم گفته
    (r"اسم(?:م|ـم)?\s+([^\s]+)", "name"),
    (r"من\s+([^\s]+)\s+هستم(?!\s+زندگی)", "name"),  # نه "من گیاهی هستم"
    
    # شغل
    (r"شغل(?:م|ـم)?\s+(.+?)(?:\s+است|\s+هست|ه$)", "job"),
    (r"کار(?:م|ـم)?\s+(.+?)(?:\s+است|\s+هست|ه$)", "job"),
    
    # سن / تولد
    (r"([۰-۹\d]+)\s*سال(?:م|مه)?", "age"),
    (r"تولد(?:م|ـم)?\s+(\d+\s*(?:فروردین|اردیبهشت|خرداد|تیر|مرداد|شهریور|مهر|آبان|آذر|دی|بهمن|اسفند))", "birthday"),
    
    # شهر
    (r"اهل\s+([^\s]+)", "city"),
    (r"ساکن\s+([^\s]+)", "city"),
    (r"توی?\s+([^\s]+)\s+زندگی", "city"),
    
    # خانواده
    (r"([۰-۹\d]+)\s*(?:تا\s+)?(?:بچه|فرزند)", "kids_count"),
    (r"(متاهل|مجرد)\s+هستم", "marital_status"),
    
    # ترجیحات زمانی
    (r"(?:معمولا|همیشه)\s+(?:ساعت\s+)?([۰-۹\d]+)\s+(?:سفارش|غذا)", "preferred_time"),
    (r"(?:ناهار|شام|صبحانه)\s+(?:ساعت\s+)?([۰-۹\d]+)", "meal_time"),
    
    # بودجه
    (r"بودجه(?:م|ـم)?\s+([۰-۹\d,]+)", "budget"),
    
    # سلیقه خاص
    (r"عاشق\s+(.+?)\s+هستم", "loves"),
    (r"خیلی دوست دارم\s+(.+?)(?:$|\.)", "loves"),
    (r"متنفرم از\s+(.+?)(?:$|\.)", "hates"),
    (r"اصلا دوست ندارم\s+(.+?)(?:$|\.)", "hates"),
]


# کلماتی که اسم نیستن
NOT_NAMES = {"گیاهی", "وگان", "متاهل", "مجرد", "راضی", "ناراضی", "گرسنه", "سیر", 
             "خوب", "بد", "خسته", "شاد", "ناراحت", "عصبانی"}


def smart_learn(user_id: int, message: str) -> Dict[str, any]:
    """
    یادگیری هوشمند - هر اطلاعات جدیدی رو کشف و ذخیره کن
    
    این تابع:
    1. الگوها رو چک می‌کنه
    2. اطلاعات جدید رو پیدا می‌کنه
    3. در extra_data ذخیره می‌کنه
    4. بعداً میشه فیلد رسمی بشه
    """
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # گرفتن extra_data فعلی
    cursor.execute("SELECT extra_data FROM customer_profiles WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row:
        cursor.execute("INSERT INTO customer_profiles (user_id) VALUES (?)", (user_id,))
        conn.commit()
        extra_data = {}
    else:
        extra_data = json.loads(row[0] or '{}')
    
    learned = {}
    
    # چک کردن همه الگوها
    for pattern, field_name in INFO_PATTERNS:
        match = re.search(pattern, message)
        if match:
            value = match.group(1) if match.lastindex else match.group(0)
            value = value.strip()
            
            if value and len(value) > 1 and len(value) < 100:
                # فیلتر کلمات غیر اسم
                if field_name == "name" and value in NOT_NAMES:
                    continue
                    
                # ذخیره در extra_data
                if field_name not in extra_data or extra_data[field_name] != value:
                    extra_data[field_name] = value
                    learned[field_name] = value
                    print(f"  🆕 Smart learned: {field_name} = {value}")
    
    # تشخیص اعداد مهم
    numbers = re.findall(r'(\d+)\s*(نفر|تا|عدد|تومان|ریال)', message)
    for num, unit in numbers:
        key = f"mentioned_{unit}"
        if key not in extra_data:
            extra_data[key] = []
        if num not in extra_data[key]:
            extra_data[key].append(num)
            learned[key] = num
    
    # تشخیص تاریخ‌های مهم
    dates = re.findall(r'(\d{1,2})\s*(فروردین|اردیبهشت|خرداد|تیر|مرداد|شهریور|مهر|آبان|آذر|دی|بهمن|اسفند)', message)
    for day, month in dates:
        key = "mentioned_dates"
        if key not in extra_data:
            extra_data[key] = []
        date_str = f"{day} {month}"
        if date_str not in extra_data[key]:
            extra_data[key].append(date_str)
            learned[key] = date_str
            print(f"  📅 Learned date: {date_str}")
    
    # ذخیره
    if learned:
        extra_data['last_smart_update'] = datetime.now().isoformat()
        cursor.execute(
            "UPDATE customer_profiles SET extra_data = ? WHERE user_id = ?",
            (json.dumps(extra_data, ensure_ascii=False), user_id)
        )
        conn.commit()
    
    conn.close()
    return learned


def get_all_learned_info(user_id: int) -> Dict:
    """
    گرفتن همه اطلاعاتی که یاد گرفتیم
    """
    profile = db.get_customer_profile(user_id)
    if not profile:
        return {}
    
    # فیلدهای رسمی
    info = {
        "official": {
            "name": profile.get('name'),
            "favorite_foods": profile.get('favorite_foods', []),
            "allergies": profile.get('allergies', []),
            "dietary_preferences": profile.get('dietary_preferences', []),
            "spice_level": profile.get('spice_level'),
            "total_orders": profile.get('total_orders', 0),
            "loyalty_tier": profile.get('loyalty_tier'),
        },
        # فیلدهای هوشمند (از extra_data)
        "smart_learned": json.loads(profile.get('extra_data') or '{}'),
    }
    
    return info


def get_table_for_field(field_name: str) -> str:
    """تشخیص جدول مناسب برای فیلد"""
    user_fields = ["name", "job", "age", "city", "birthday"]
    if field_name in user_fields:
        return "users"
    return "customer_profiles"


# ═══════════════════════════════════════════════════════════
# 🔄 Auto-Migration System
# ═══════════════════════════════════════════════════════════

# حداقل تعداد استفاده برای promote شدن
MIN_USAGE_FOR_PROMOTION = 5

# فیلدهایی که نباید promote بشن
SKIP_FIELDS = {"last_smart_update", "mentioned_dates", "mentioned_نفر", "mentioned_تا", "emotion_history"}


def analyze_extra_data_usage() -> Dict[str, int]:
    """
    تحلیل اینکه کدوم فیلدها در extra_data زیاد استفاده شدن
    """
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT extra_data FROM customer_profiles WHERE extra_data IS NOT NULL")
    rows = cursor.fetchall()
    conn.close()
    
    field_counts = {}
    
    for row in rows:
        try:
            if isinstance(row, dict):
                extra_data = row.get('extra_data', {})
            else:
                extra_data = row[0] if row else {}
            
            if isinstance(extra_data, str):
                extra_data = json.loads(extra_data) if extra_data else {}
            
            for field in extra_data.keys():
                if field not in SKIP_FIELDS:
                    field_counts[field] = field_counts.get(field, 0) + 1
        except:
            pass
    
    return field_counts


def get_fields_ready_for_promotion() -> List[str]:
    """
    فیلدهایی که آماده promote شدن هستن
    """
    usage = analyze_extra_data_usage()
    ready = [field for field, count in usage.items() if count >= MIN_USAGE_FOR_PROMOTION]
    return ready


def auto_promote_field(field_name: str) -> bool:
    """
    خودکار یه فیلد رو از extra_data به schema اصلی promote کن
    
    1. فیلد جدید در جدول بساز
    2. اطلاعات رو از extra_data منتقل کن
    3. ثبت در ai_learned_patterns
    """
    import os
    
    if field_name in SKIP_FIELDS:
        print(f"⚠️ Field '{field_name}' is in skip list")
        return False
    
    table = get_table_for_field(field_name)
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # 1️⃣ ساخت فیلد جدید (PostgreSQL)
        if os.environ.get('DB_MODE') == 'postgres':
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {field_name} TEXT")
        else:
            # SQLite
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {field_name} TEXT")
            except:
                pass  # فیلد وجود داره
        
        conn.commit()
        print(f"✅ Created field: {table}.{field_name}")
        
        # 2️⃣ انتقال اطلاعات از extra_data
        cursor.execute("SELECT user_id, extra_data FROM customer_profiles WHERE extra_data IS NOT NULL")
        rows = cursor.fetchall()
        
        migrated = 0
        for row in rows:
            try:
                if isinstance(row, dict):
                    user_id = row['user_id']
                    extra_data = row.get('extra_data', {})
                else:
                    user_id = row[0]
                    extra_data = row[1] if len(row) > 1 else {}
                
                if isinstance(extra_data, str):
                    extra_data = json.loads(extra_data) if extra_data else {}
                
                if field_name in extra_data:
                    value = extra_data[field_name]
                    
                    if table == "users":
                        cursor.execute(f"UPDATE users SET {field_name} = ? WHERE id = ?", (value, user_id))
                    else:
                        cursor.execute(f"UPDATE customer_profiles SET {field_name} = ? WHERE user_id = ?", (value, user_id))
                    
                    migrated += 1
            except Exception as e:
                print(f"⚠️ Error migrating user {user_id}: {e}")
        
        conn.commit()
        print(f"📦 Migrated {migrated} values to {table}.{field_name}")
        
        # 3️⃣ ثبت در ai_learned_patterns
        cursor.execute("""
            INSERT INTO ai_learned_patterns (pattern_type, pattern_key, pattern_value, usage_count, last_used)
            VALUES (?, ?, ?, ?, ?)
        """, ('auto_promoted_field', field_name, table, migrated, datetime.now().isoformat()))
        conn.commit()
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error promoting field: {e}")
        conn.close()
        return False


def auto_promote_all_ready_fields():
    """
    همه فیلدهای آماده رو خودکار promote کن
    """
    ready = get_fields_ready_for_promotion()
    
    if not ready:
        print("📭 No fields ready for promotion")
        return []
    
    print(f"🔄 Found {len(ready)} fields ready for promotion: {ready}")
    
    promoted = []
    for field in ready:
        if auto_promote_field(field):
            promoted.append(field)
    
    return promoted


def promote_to_official_field(field_name: str):
    """
    Promote یه فیلد به schema رسمی (دستی یا خودکار)
    """
    return auto_promote_field(field_name)


# ═══════════════════════════════════════════════════════════
# 🧪 تست
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n🧪 Testing Profile Learner...\n")
    
    # تست یادگیری از چت
    test_messages = [
        "سلام، پیتزا پپرونی می‌خوام",
        "به بادام‌زمینی آلرژی دارم",
        "غذای تند نمی‌خورم",
        "من گیاهی هستم",
    ]
    
    print("💬 Learning from chat:")
    for msg in test_messages:
        print(f"  > {msg}")
        # learn_from_chat(1, msg)  # Uncomment to test with real user
    
    print("\n✅ Profile Learner ready!")

