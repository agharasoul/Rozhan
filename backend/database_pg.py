"""
🗄️ PostgreSQL + Redis Database Layer
پایگاه داده حرفه‌ای برای مقیاس بالا
"""

import os
import json
import redis
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from contextlib import contextmanager

# ===== تنظیمات =====
POSTGRES_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:aseman777@localhost:5432/rozhan')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Parse Redis URL
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Cache TTL (seconds)
CACHE_TTL = {
    'session': 86400 * 30,  # 30 days
    'user': 3600,           # 1 hour
    'chat_history': 300,    # 5 minutes
    'profile': 1800,        # 30 minutes
}


def convert_query(query):
    """تبدیل ? به %s برای PostgreSQL"""
    return query.replace('?', '%s')


class PgCursor:
    """Cursor wrapper برای تبدیل خودکار query"""
    def __init__(self, cursor):
        self._cursor = cursor
    
    def execute(self, query, params=None):
        query = convert_query(query)
        if params:
            return self._cursor.execute(query, params)
        return self._cursor.execute(query)
    
    def fetchone(self):
        return self._cursor.fetchone()
    
    def fetchall(self):
        return self._cursor.fetchall()
    
    def __iter__(self):
        return iter(self._cursor)
    
    @property
    def rowcount(self):
        return self._cursor.rowcount
    
    @property
    def lastrowid(self):
        return self._cursor.lastrowid if hasattr(self._cursor, 'lastrowid') else None


class PgConnection:
    """Wrapper برای سازگاری با SQLite"""
    def __init__(self):
        self.conn = psycopg2.connect(POSTGRES_URL, cursor_factory=RealDictCursor)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()
        return False
    
    def cursor(self):
        return PgCursor(self.conn.cursor())
    
    def commit(self):
        self.conn.commit()
    
    def rollback(self):
        self.conn.rollback()
    
    def close(self):
        self.conn.close()
    
    def execute(self, *args):
        return self.cursor().execute(*args)


def get_connection():
    """اتصال به PostgreSQL (سازگار با SQLite API)"""
    return PgConnection()


@contextmanager
def get_connection_context():
    """اتصال به PostgreSQL با context manager"""
    conn = psycopg2.connect(POSTGRES_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_database():
    """ساخت جداول اولیه"""
    with get_connection_context() as conn:
        cursor = conn.cursor()
        
        # جدول کاربران
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                phone VARCHAR(15) UNIQUE,
                email VARCHAR(255) UNIQUE,
                name VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                preferences JSONB DEFAULT '{}',
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # ایندکس برای جستجوی سریع
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        
        # جدول کدهای تأیید
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verification_codes (
                id SERIAL PRIMARY KEY,
                phone VARCHAR(15),
                email VARCHAR(255),
                code VARCHAR(6),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_used BOOLEAN DEFAULT FALSE
            )
        """)
        
        # جدول سشن‌ها
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                token VARCHAR(64) UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                device_info TEXT
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
        
        # جدول تاریخچه چت
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                role VARCHAR(20),
                content TEXT,
                image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB DEFAULT '{}'
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_history(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_created ON chat_history(created_at DESC)")
        
        # جدول سشن‌های چت (مکالمات)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(255) DEFAULT 'مکالمه جدید',
                summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                message_count INTEGER DEFAULT 0,
                metadata JSONB DEFAULT '{}'
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated ON chat_sessions(updated_at DESC)")
        
        # اضافه کردن session_id به chat_history
        cursor.execute("""
            ALTER TABLE chat_history 
            ADD COLUMN IF NOT EXISTS session_id INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id)")
        
        # جدول پروفایل مشتری
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_profiles (
                id SERIAL PRIMARY KEY,
                user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                favorite_foods JSONB DEFAULT '[]',
                allergies JSONB DEFAULT '[]',
                dietary_preferences JSONB DEFAULT '[]',
                avg_order_value DECIMAL(10,2) DEFAULT 0,
                total_orders INTEGER DEFAULT 0,
                last_order_date TIMESTAMP,
                notes TEXT,
                tags JSONB DEFAULT '[]',
                loyalty_points INTEGER DEFAULT 0,
                loyalty_tier VARCHAR(20) DEFAULT 'bronze',
                spice_level VARCHAR(20),
                extra_data JSONB DEFAULT '{}'
            )
        """)
        
        # اضافه کردن فیلدهای جدید اگر نباشن
        cursor.execute("ALTER TABLE customer_profiles ADD COLUMN IF NOT EXISTS loyalty_tier VARCHAR(20) DEFAULT 'bronze'")
        cursor.execute("ALTER TABLE customer_profiles ADD COLUMN IF NOT EXISTS spice_level VARCHAR(20)")
        cursor.execute("ALTER TABLE customer_profiles ADD COLUMN IF NOT EXISTS extra_data JSONB DEFAULT '{}'")
        
    print("✅ PostgreSQL initialized!")
    
    # تست Redis
    try:
        redis_client.ping()
        print("✅ Redis connected!")
    except:
        print("⚠️ Redis not available - running without cache")


# ===== Redis Cache Helpers =====

def cache_get(key: str) -> Optional[Dict]:
    """خواندن از cache"""
    try:
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except:
        return None


def cache_set(key: str, value: Dict, ttl_type: str = 'user'):
    """نوشتن در cache"""
    try:
        redis_client.setex(key, CACHE_TTL.get(ttl_type, 3600), json.dumps(value, default=str))
    except:
        pass


def cache_delete(key: str):
    """حذف از cache"""
    try:
        redis_client.delete(key)
    except:
        pass


def cache_delete_pattern(pattern: str):
    """حذف با pattern"""
    try:
        for key in redis_client.scan_iter(pattern):
            redis_client.delete(key)
    except:
        pass


# ===== User Functions =====

def create_user(phone: str = None, email: str = None, name: str = None) -> int:
    """ایجاد کاربر جدید"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO users (phone, email, name) 
            VALUES (%s, %s, %s)
            RETURNING id
        """, (phone, email, name))
        
        user_id = cursor.fetchone()['id']
        
        # ساخت پروفایل مشتری
        cursor.execute("""
            INSERT INTO customer_profiles (user_id) VALUES (%s)
        """, (user_id,))
        
    return user_id


def get_user_by_phone(phone: str) -> Optional[Dict]:
    """دریافت کاربر با شماره موبایل"""
    # چک cache
    cached = cache_get(f"user:phone:{phone}")
    if cached:
        return cached
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE phone = %s", (phone,))
        row = cursor.fetchone()
        
    if row:
        user = dict(row)
        cache_set(f"user:phone:{phone}", user)
        cache_set(f"user:id:{user['id']}", user)
        return user
    return None


def get_user_by_email(email: str) -> Optional[Dict]:
    """دریافت کاربر با ایمیل"""
    cached = cache_get(f"user:email:{email}")
    if cached:
        return cached
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        row = cursor.fetchone()
        
    if row:
        user = dict(row)
        cache_set(f"user:email:{email}", user)
        cache_set(f"user:id:{user['id']}", user)
        return user
    return None


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """دریافت کاربر با ID"""
    cached = cache_get(f"user:id:{user_id}")
    if cached:
        return cached
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        
    if row:
        user = dict(row)
        cache_set(f"user:id:{user_id}", user)
        return user
    return None


def update_last_login(user_id: int):
    """آپدیت زمان آخرین لاگین"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET last_login = %s WHERE id = %s
        """, (datetime.now(), user_id))
    
    # پاک کردن cache
    cache_delete(f"user:id:{user_id}")


# ===== Chat History Functions =====

def save_message(user_id: int, role: str, content: str, image_url: str = None, metadata: dict = None):
    """ذخیره پیام در تاریخچه"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chat_history (user_id, role, content, image_url, metadata)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, role, content, image_url, json.dumps(metadata or {})))
    
    # پاک کردن cache تاریخچه
    cache_delete(f"chat:history:{user_id}")
    
    # ذخیره در Redis برای دسترسی سریع (آخرین ۱۰ پیام)
    try:
        redis_client.lpush(f"chat:recent:{user_id}", json.dumps({
            'role': role,
            'content': content,
            'created_at': datetime.now().isoformat()
        }))
        redis_client.ltrim(f"chat:recent:{user_id}", 0, 9)  # فقط ۱۰ تا نگه دار
        redis_client.expire(f"chat:recent:{user_id}", CACHE_TTL['chat_history'])
    except:
        pass


def get_chat_history(user_id: int, limit: int = 50) -> List[Dict]:
    """دریافت تاریخچه چت کاربر"""
    # چک cache
    cached = cache_get(f"chat:history:{user_id}")
    if cached:
        return cached[:limit]
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM chat_history 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s
        """, (user_id, limit))
        rows = cursor.fetchall()
        
    history = [dict(row) for row in reversed(rows)]
    cache_set(f"chat:history:{user_id}", history, 'chat_history')
    return history


def get_recent_context(user_id: int, limit: int = 10) -> str:
    """دریافت context اخیر برای Gemini - از Redis"""
    try:
        # اول از Redis بخون (سریع‌تر)
        recent = redis_client.lrange(f"chat:recent:{user_id}", 0, limit - 1)
        if recent:
            messages = [json.loads(m) for m in recent]
            messages.reverse()
            context_parts = []
            for msg in messages:
                role = "کاربر" if msg['role'] == 'user' else "دستیار"
                context_parts.append(f"{role}: {msg['content']}")
            return "\n".join(context_parts)
    except:
        pass
    
    # Fallback به PostgreSQL
    history = get_chat_history(user_id, limit)
    if not history:
        return ""
    
    context_parts = []
    for msg in history:
        role = "کاربر" if msg['role'] == 'user' else "دستیار"
        context_parts.append(f"{role}: {msg['content']}")
    
    return "\n".join(context_parts)


# ===== Customer Profile Functions =====

def get_customer_profile(user_id: int) -> Optional[Dict]:
    """دریافت پروفایل مشتری"""
    cached = cache_get(f"profile:{user_id}")
    if cached:
        return cached
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cp.*, u.name, u.phone, u.email
            FROM customer_profiles cp
            JOIN users u ON cp.user_id = u.id
            WHERE cp.user_id = %s
        """, (user_id,))
        row = cursor.fetchone()
        
    if row:
        profile = dict(row)
        cache_set(f"profile:{user_id}", profile, 'profile')
        return profile
    return None


def update_customer_profile(user_id: int, **kwargs):
    """آپدیت پروفایل مشتری"""
    allowed_fields = ['favorite_foods', 'allergies', 'dietary_preferences', 
                      'avg_order_value', 'total_orders', 'last_order_date', 
                      'notes', 'tags', 'loyalty_points', 'loyalty_tier', 
                      'spice_level', 'extra_data']
    
    updates = []
    values = []
    
    for key, value in kwargs.items():
        if key in allowed_fields:
            if key in ['favorite_foods', 'allergies', 'dietary_preferences', 'tags', 'extra_data']:
                updates.append(f"{key} = %s::jsonb")
                values.append(json.dumps(value))
            else:
                updates.append(f"{key} = %s")
                values.append(value)
    
    if updates:
        values.append(user_id)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE customer_profiles 
                SET {', '.join(updates)} 
                WHERE user_id = %s
            """, values)
        
        # پاک کردن cache
        cache_delete(f"profile:{user_id}")


def get_customer_context(user_id: int) -> str:
    """ساخت context کامل مشتری برای Gemini"""
    profile = get_customer_profile(user_id)
    if not profile:
        return ""
    
    context_parts = []
    
    if profile.get('name'):
        context_parts.append(f"نام مشتری: {profile['name']}")
    
    if profile.get('favorite_foods'):
        foods = profile['favorite_foods']
        if isinstance(foods, list) and foods:
            context_parts.append(f"غذاهای مورد علاقه: {', '.join(foods)}")
    
    if profile.get('allergies'):
        allergies = profile['allergies']
        if isinstance(allergies, list) and allergies:
            context_parts.append(f"⚠️ آلرژی‌ها: {', '.join(allergies)}")
    
    if profile.get('dietary_preferences'):
        prefs = profile['dietary_preferences']
        if isinstance(prefs, list) and prefs:
            context_parts.append(f"رژیم غذایی: {', '.join(prefs)}")
    
    if profile.get('total_orders', 0) > 0:
        context_parts.append(f"تعداد سفارشات قبلی: {profile['total_orders']}")
    
    if profile.get('loyalty_points', 0) > 0:
        context_parts.append(f"امتیاز وفاداری: {profile['loyalty_points']}")
    
    if profile.get('notes'):
        context_parts.append(f"یادداشت: {profile['notes']}")
    
    return "\n".join(context_parts)


# ===== Session Management (Redis) =====

def store_session_redis(user_id: int, token_hash: str, expires_days: int = 30):
    """ذخیره session در Redis برای دسترسی سریع"""
    try:
        session_data = {
            'user_id': user_id,
            'created_at': datetime.now().isoformat()
        }
        redis_client.setex(
            f"session:{token_hash}", 
            expires_days * 86400, 
            json.dumps(session_data)
        )
    except:
        pass


def get_session_redis(token_hash: str) -> Optional[Dict]:
    """خواندن session از Redis"""
    try:
        data = redis_client.get(f"session:{token_hash}")
        return json.loads(data) if data else None
    except:
        return None


def delete_session_redis(token_hash: str):
    """حذف session از Redis"""
    try:
        redis_client.delete(f"session:{token_hash}")
    except:
        pass


# Initialize on import
try:
    init_database()
except Exception as e:
    print(f"⚠️ Database init error: {e}")
    print("💡 Make sure PostgreSQL and Redis are running!")

