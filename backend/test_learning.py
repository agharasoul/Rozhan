"""
🧪 تست سیستم یادگیری پروفایل
"""

import profile_learner
import db
import json

print('🧪 Testing Profile Learning System...\n')

# ایجاد یک کاربر تست
conn = db.get_connection()
cursor = conn.cursor()

# چک کن کاربر تست هست یا نه
cursor.execute("SELECT id FROM users WHERE email = ?", ('test@example.com',))
user = cursor.fetchone()

if not user:
    cursor.execute("INSERT INTO users (email, name) VALUES (?, ?)", ('test@example.com', 'Test User'))
    conn.commit()
    cursor.execute("SELECT id FROM users WHERE email = ?", ('test@example.com',))
    user = cursor.fetchone()

user_id = user[0]
print(f'✅ Test user ID: {user_id}\n')
conn.close()

# تست یادگیری از چت
test_messages = [
    'سلام، من رضا هستم',
    'پیتزا پپرونی می‌خوام',
    'به بادام آلرژی دارم',
    'غذای تند نمی‌خورم',
    'من گیاهی هستم',
    '۳۲ سالمه',
    'شغلم برنامه‌نویسی هست',
    'اهل تهران هستم زندگی می‌کنم',
    'تولدم ۱۵ مهر هست',
]

print('💬 Testing chat learning:')
for msg in test_messages:
    print(f'  > "{msg}"')
    try:
        result = profile_learner.learn_from_chat(user_id, msg)
        if result:
            print(f'    ✅ Learned something!')
    except Exception as e:
        print(f'    ❌ Error: {e}')

# نمایش نتایج
print('\n' + '='*50)
print('📊 RESULTS:')
print('='*50)

profile = db.get_customer_profile(user_id)
if profile:
    print(f'\n🍕 Favorite foods: {profile.get("favorite_foods", [])}')
    print(f'⚠️  Allergies: {profile.get("allergies", [])}')
    print(f'🥗 Dietary: {profile.get("dietary_preferences", [])}')
    print(f'🌶️  Spice level: {profile.get("spice_level", "not set")}')
    
    extra = profile.get("extra_data", "{}")
    if extra and extra != "{}":
        print(f'\n🆕 Smart Learned (extra_data):')
        try:
            extra_dict = json.loads(extra) if isinstance(extra, str) else extra
            for k, v in extra_dict.items():
                if k != 'last_smart_update':
                    print(f'    {k}: {v}')
        except:
            print(f'    {extra}')
else:
    print('  ❌ No profile found')

print('\n✅ Test complete!')

