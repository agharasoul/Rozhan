"""
🔑 تنظیمات روژان
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 🔷 GapGPT API (پروکسی ایرانی برای Gemini) - اولویت اول
# ═══════════════════════════════════════════════════════════════════════════════
GAPGPT_API_KEY = "sk-30IhBBPeXbyktVpCL9WPVWTZvWGxbRyrGYZGREFaw6FE41NN"
GAPGPT_BASE_URL = "https://api.gapgpt.app/"

# ═══════════════════════════════════════════════════════════════════════════════
# 🔶 Gemini API Keys (بکاپ - مستقیم گوگل)
# ═══════════════════════════════════════════════════════════════════════════════
GEMINI_API_KEYS = [
    "AIzaSyD4-5eb9mI0Rf7-iFwCx7YGpF38mDsxJ0E",
    "AIzaSyAv4K7Vquqn7C8A5nrZdQT_6TBCyMpyTkU",
    "AIzaSyBhjbBePfShjj1eqFG_m099qHN_RQN3Ad8",
    "AIzaSyB88bsDTPOnYGd3qRqw3z8LJf-0QqF3s2g",
    "AIzaSyCtHHxGxiMKO-cVWVMNVg6kCcrpBWEe-Es",
    "AIzaSyAf8x1Ze-ozd6ZM2_sXPppfLQqxFmK4tSI",
]

# حالت فعلی: gapgpt یا direct
USE_GAPGPT = True  # از GapGPT استفاده کن

# API Key فعلی (برای حالت direct)
current_key_index = 0

def get_current_key():
    """گرفتن API Key فعلی"""
    if USE_GAPGPT:
        return GAPGPT_API_KEY
    return GEMINI_API_KEYS[current_key_index]

def get_base_url():
    """گرفتن Base URL"""
    if USE_GAPGPT:
        return GAPGPT_BASE_URL
    return "https://generativelanguage.googleapis.com/v1beta/"

def switch_to_next_key():
    """سوئیچ به API Key بعدی (فقط وقتی خطا بخوریم)"""
    global current_key_index, USE_GAPGPT
    
    if USE_GAPGPT:
        # اگه GapGPT خطا داد، سوئیچ به direct
        print("⚠️ GapGPT error, switching to direct Google API")
        USE_GAPGPT = False
        return GEMINI_API_KEYS[0]
    
    current_key_index = (current_key_index + 1) % len(GEMINI_API_KEYS)
    print(f"🔄 سوئیچ به کلید {current_key_index + 1}")
    return GEMINI_API_KEYS[current_key_index]

