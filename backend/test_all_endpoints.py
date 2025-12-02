"""تست همه API های روژان"""
import requests

BASE = 'http://localhost:8000'

print('=' * 60)
print('🧪 تست کامل API روژان')
print('=' * 60)

tests = [
    ('GET', '/', 'سرور'),
    ('GET', '/tts/voices', 'لیست صداها'),
    ('GET', '/suggest/food', 'پیشنهاد غذا'),
    ('POST', '/tts', 'TTS', {'text': 'سلام', 'voice': 'Kore'}),
]

for t in tests:
    method, endpoint, name = t[0], t[1], t[2]
    data = t[3] if len(t) > 3 else None
    
    try:
        if method == 'GET':
            r = requests.get(f'{BASE}{endpoint}', timeout=30)
        else:
            r = requests.post(f'{BASE}{endpoint}', json=data, timeout=60)
        
        status = '✅' if r.ok else '❌'
        print(f'{status} {name}: {r.status_code}')
    except Exception as e:
        print(f'❌ {name}: {str(e)[:50]}')

# تست چت
print('\n📝 تست چت...')
try:
    r = requests.post(f'{BASE}/chat', json={'message': 'سلام'}, timeout=60)
    if r.ok:
        data = r.json()
        print(f'✅ چت: {data.get("response", "")[:50]}...')
    else:
        print(f'❌ چت: {r.status_code}')
except Exception as e:
    print(f'❌ چت: {e}')

print('\n' + '=' * 60)
print('✅ تست تمام!')
