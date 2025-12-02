"""تست قابلیت‌های جدید روژان"""
import requests

BASE = 'http://localhost:8000'

print('=' * 50)
print('🧪 تست API‌های جدید روژان')
print('=' * 50)

# 1. تست TTS با صدای جدید
print('\n1️⃣ تست TTS با Gemini...')
try:
    r = requests.post(f'{BASE}/tts', json={'text': 'سلام خوبی؟', 'voice': 'Kore', 'emotion': 'happy'}, timeout=60)
    print(f'   Status: {r.status_code}')
    if r.ok:
        d = r.json()
        print(f'   Success: {d.get("success")}')
        print(f'   Has Audio: {bool(d.get("audio"))}')
except Exception as e:
    print(f'   Error: {e}')

# 2. تست لیست صداها
print('\n2️⃣ تست لیست صداها...')
try:
    r = requests.get(f'{BASE}/tts/voices')
    print(f'   Status: {r.status_code}')
    if r.ok:
        d = r.json()
        print(f'   Voices: {len(d.get("voices", {}))} صدا')
        print(f'   Emotions: {d.get("emotions")}')
except Exception as e:
    print(f'   Error: {e}')

# 3. تست پیشنهاد غذا
print('\n3️⃣ تست پیشنهاد غذا...')
try:
    r = requests.get(f'{BASE}/suggest/food')
    print(f'   Status: {r.status_code}')
    if r.ok:
        d = r.json()
        print(f'   Reason: {d.get("reason")}')
except Exception as e:
    print(f'   Error: {e}')

# 4. تست تحلیل تصویر
print('\n4️⃣ تست تحلیل تصویر...')
try:
    # یه تصویر ساده
    test_img = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
    r = requests.post(f'{BASE}/analyze/image', json={'image': test_img, 'mode': 'describe'}, timeout=90)
    print(f'   Status: {r.status_code}')
    if r.ok:
        d = r.json()
        print(f'   Success: {d.get("success")}')
        if d.get("analysis"):
            print(f'   Analysis: {str(d.get("analysis"))[:100]}...')
except Exception as e:
    print(f'   Error: {e}')

# 5. تست Transcribe با تشخیص احساس
print('\n5️⃣ تست Transcribe endpoint...')
try:
    r = requests.get(f'{BASE}/')
    print(f'   Server Status: {r.status_code}')
    if r.ok:
        print(f'   Message: {r.json().get("message")}')
except Exception as e:
    print(f'   Error: {e}')

print('\n' + '=' * 50)
print('✅ تست‌ها تمام شد!')
print('=' * 50)
