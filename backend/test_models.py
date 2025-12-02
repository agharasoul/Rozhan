"""تست TTS با مدل‌های مختلف"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_KEY = "sk-iqYVdnQVcPvdh4I8E09etdcliolmgZmk2RwRtDs6uVZBC0mC"
headers = {"Authorization": f"Bearer {API_KEY}"}

# Session با retry
session = requests.Session()
retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount('https://', HTTPAdapter(max_retries=retry))

def test_tts(model):
    url = f"https://api.gapgpt.app/v1beta/models/{model}:generateContent"
    data = {
        "contents": [{"parts": [{"text": "سلام خوبی؟"}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": "Kore"}
                }
            }
        }
    }
    try:
        r = session.post(url, headers=headers, json=data, timeout=90)
        if r.ok:
            result = r.json()
            has_audio = bool(result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('inlineData'))
            return "✅ Audio!" if has_audio else "⚠️ No audio"
        return f"❌ {r.status_code}"
    except Exception as e:
        return f"❌ {str(e)[:50]}"

print("🔊 تست TTS:\n")
models = [
    "gemini-2.5-flash-preview-tts",
    "gemini-3-pro-image-preview",
]
for m in models:
    print(f"  {m}: {test_tts(m)}")
