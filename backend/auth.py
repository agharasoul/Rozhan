"""
🔐 Authentication System
احراز هویت با موبایل یا ایمیل + کد تأیید
"""

import secrets
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
import db
import os

# تنظیمات ایمیل
EMAIL_SENDER = os.environ.get('EMAIL_SENDER', '')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')

# تنظیمات
CODE_LENGTH = 6
CODE_EXPIRY_MINUTES = 5
SESSION_EXPIRY_DAYS = 30


def generate_code() -> str:
    """تولید کد تأیید 6 رقمی"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(CODE_LENGTH)])


def send_email(to_email: str, code: str) -> bool:
    """ارسال ایمیل با کد تأیید"""
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print(f"⚠️ ایمیل تنظیم نشده! کد تأیید: {code}")
        return True  # در حالت تست، موفق فرض کن
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = '🔐 کد تأیید روژان'
        msg['From'] = EMAIL_SENDER
        msg['To'] = to_email
        
        # متن ساده
        text = f"کد تأیید شما: {code}\n\nاین کد ۵ دقیقه اعتبار دارد."
        
        # HTML زیبا
        html = f"""
        <html dir="rtl">
        <body style="font-family: Tahoma, Arial; background: #f5f5f5; padding: 20px;">
            <div style="max-width: 400px; margin: auto; background: white; border-radius: 16px; padding: 30px; text-align: center;">
                <h2 style="color: #333;">🌟 روژان</h2>
                <p style="color: #666;">کد تأیید شما:</p>
                <div style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #2563eb; margin: 20px 0;">
                    {code}
                </div>
                <p style="color: #999; font-size: 12px;">این کد ۵ دقیقه اعتبار دارد</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(text, 'plain'))
        msg.attach(MIMEText(html, 'html'))
        
        # اتصال به Gmail SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, to_email, msg.as_string())
        
        print(f"✅ ایمیل به {to_email} ارسال شد")
        return True
        
    except Exception as e:
        print(f"❌ خطا در ارسال ایمیل: {e}")
        print(f"📧 کد تأیید (فالبک): {code}")
        return True  # حتی اگر خطا، ادامه بده


def generate_token() -> str:
    """تولید توکن سشن"""
    return secrets.token_hex(32)


def hash_token(token: str) -> str:
    """هش کردن توکن برای ذخیره امن"""
    return hashlib.sha256(token.encode()).hexdigest()


# ===== Verification Code =====

def send_verification_code(phone: str = None, email: str = None) -> Tuple[bool, str]:
    """
    ارسال کد تأیید به موبایل یا ایمیل
    برمی‌گرداند: (success, message)
    """
    if not phone and not email:
        return False, "شماره موبایل یا ایمیل وارد کنید"
    
    code = generate_code()
    expires_at = datetime.now() + timedelta(minutes=CODE_EXPIRY_MINUTES)
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO verification_codes (phone, email, code, expires_at)
        VALUES (?, ?, ?, ?)
    """, (phone, email, code, expires_at.isoformat()))
    
    conn.commit()
    conn.close()
    
    if phone:
        print(f"📱 کد تأیید SMS: {code}")
        return True, f"کد: {code}"  # نمایش در UI (حالت تست)
    else:
        send_email(email, code)
        return True, f"کد: {code}"  # نمایش در UI (حالت تست)


def verify_code(code: str, phone: str = None, email: str = None) -> Tuple[bool, str, Optional[Dict]]:
    """
    تأیید کد و لاگین/ثبت‌نام
    برمی‌گرداند: (success, message, user_data)
    """
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # پیدا کردن کد معتبر
    if phone:
        cursor.execute("""
            SELECT * FROM verification_codes 
            WHERE phone = ? AND code = ? AND is_used = FALSE AND expires_at > ?
            ORDER BY created_at DESC LIMIT 1
        """, (phone, code, datetime.now().isoformat()))
    else:
        cursor.execute("""
            SELECT * FROM verification_codes 
            WHERE email = ? AND code = ? AND is_used = FALSE AND expires_at > ?
            ORDER BY created_at DESC LIMIT 1
        """, (email, code, datetime.now().isoformat()))
    
    verification = cursor.fetchone()
    
    if not verification:
        conn.close()
        return False, "کد نامعتبر یا منقضی شده", None
    
    # علامت‌گذاری کد به عنوان استفاده شده
    cursor.execute("""
        UPDATE verification_codes SET is_used = TRUE WHERE id = ?
    """, (verification['id'],))
    
    conn.commit()
    conn.close()
    
    # پیدا کردن یا ساخت کاربر
    if phone:
        user = db.get_user_by_phone(phone)
        if not user:
            user_id = db.create_user(phone=phone)
            user = db.get_user_by_id(user_id)
    else:
        user = db.get_user_by_email(email)
        if not user:
            user_id = db.create_user(email=email)
            user = db.get_user_by_id(user_id)
    
    # آپدیت آخرین لاگین
    db.update_last_login(user['id'])
    
    # ساخت سشن
    token = generate_token()
    session_data = create_session(user['id'], token)
    
    return True, "ورود موفق", {
        "user": user,
        "token": token,
        "expires_at": session_data['expires_at']
    }


# ===== Session Management =====

def create_session(user_id: int, token: str, device_info: str = None) -> Dict:
    """ساخت سشن جدید"""
    expires_at = datetime.now() + timedelta(days=SESSION_EXPIRY_DAYS)
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO sessions (user_id, token, expires_at, device_info)
        VALUES (?, ?, ?, ?)
    """, (user_id, hash_token(token), expires_at.isoformat(), device_info))
    
    conn.commit()
    conn.close()
    
    return {
        "user_id": user_id,
        "token": token,
        "expires_at": expires_at.isoformat()
    }


def validate_session(token: str) -> Optional[Dict]:
    """اعتبارسنجی توکن و برگرداندن اطلاعات کاربر"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT s.*, u.* FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ? AND s.expires_at > ? AND u.is_active = TRUE
    """, (hash_token(token), datetime.now().isoformat()))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def logout(token: str) -> bool:
    """خروج از سیستم - حذف سشن"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM sessions WHERE token = ?
    """, (hash_token(token),))
    
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    return affected > 0


def get_user_from_token(token: str) -> Optional[Dict]:
    """دریافت کاربر از توکن"""
    session = validate_session(token)
    if session:
        return db.get_user_by_id(session['user_id'])
    return None

