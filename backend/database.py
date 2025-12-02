"""
🗄️ Database Layer
ذخیره اطلاعات کاربران و تاریخچه چت
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
import json
import os

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "rozhan.db")


def get_connection():
    """اتصال به دیتابیس"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """ساخت جداول اولیه"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # ═══════════════════════════════════════════════════════════
    # 👤 کاربران و احراز هویت
    # ═══════════════════════════════════════════════════════════
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone VARCHAR(15) UNIQUE,
            email VARCHAR(255) UNIQUE,
            name VARCHAR(100),
            avatar_url TEXT,
            birthday DATE,
            gender VARCHAR(10),
            language VARCHAR(5) DEFAULT 'fa',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            last_activity TIMESTAMP,
            preferences TEXT DEFAULT '{}',
            is_active BOOLEAN DEFAULT 1,
            is_verified BOOLEAN DEFAULT 0,
            role VARCHAR(20) DEFAULT 'customer',
            referral_code VARCHAR(20) UNIQUE,
            referred_by INTEGER,
            FOREIGN KEY (referred_by) REFERENCES users(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verification_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone VARCHAR(15),
            email VARCHAR(255),
            code VARCHAR(6),
            type VARCHAR(20) DEFAULT 'login',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            is_used BOOLEAN DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            token VARCHAR(64) UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            device_info TEXT,
            ip_address VARCHAR(45),
            user_agent TEXT,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # ═══════════════════════════════════════════════════════════
    # 📍 آدرس‌ها
    # ═══════════════════════════════════════════════════════════
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS addresses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title VARCHAR(50),
            full_address TEXT,
            city VARCHAR(100),
            district VARCHAR(100),
            postal_code VARCHAR(20),
            latitude REAL,
            longitude REAL,
            floor VARCHAR(10),
            unit VARCHAR(10),
            receiver_name VARCHAR(100),
            receiver_phone VARCHAR(15),
            is_default BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # ═══════════════════════════════════════════════════════════
    # 🏪 رستوران‌ها و شعب
    # ═══════════════════════════════════════════════════════════
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100),
            slug VARCHAR(100) UNIQUE,
            description TEXT,
            logo_url TEXT,
            cover_url TEXT,
            phone VARCHAR(15),
            email VARCHAR(255),
            address TEXT,
            city VARCHAR(100),
            latitude REAL,
            longitude REAL,
            rating REAL DEFAULT 0,
            total_reviews INTEGER DEFAULT 0,
            min_order_amount INTEGER DEFAULT 0,
            delivery_fee INTEGER DEFAULT 0,
            delivery_time_min INTEGER,
            delivery_time_max INTEGER,
            is_open BOOLEAN DEFAULT 1,
            opening_time TIME,
            closing_time TIME,
            working_days TEXT DEFAULT '["sat","sun","mon","tue","wed","thu","fri"]',
            categories TEXT DEFAULT '[]',
            tags TEXT DEFAULT '[]',
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS restaurant_branches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER,
            name VARCHAR(100),
            address TEXT,
            city VARCHAR(100),
            latitude REAL,
            longitude REAL,
            phone VARCHAR(15),
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
        )
    """)
    
    # ═══════════════════════════════════════════════════════════
    # 🍕 منو و محصولات
    # ═══════════════════════════════════════════════════════════
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER,
            name VARCHAR(100),
            description TEXT,
            icon VARCHAR(50),
            image_url TEXT,
            sort_order INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER,
            category_id INTEGER,
            name VARCHAR(100),
            description TEXT,
            image_url TEXT,
            price INTEGER,
            discount_price INTEGER,
            ingredients TEXT DEFAULT '[]',
            allergens TEXT DEFAULT '[]',
            calories INTEGER,
            prep_time_min INTEGER,
            is_available BOOLEAN DEFAULT 1,
            is_featured BOOLEAN DEFAULT 0,
            is_new BOOLEAN DEFAULT 0,
            tags TEXT DEFAULT '[]',
            options TEXT DEFAULT '[]',
            sort_order INTEGER DEFAULT 0,
            total_orders INTEGER DEFAULT 0,
            rating REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id),
            FOREIGN KEY (category_id) REFERENCES menu_categories(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            menu_item_id INTEGER,
            name VARCHAR(100),
            type VARCHAR(20),
            is_required BOOLEAN DEFAULT 0,
            max_selections INTEGER DEFAULT 1,
            choices TEXT DEFAULT '[]',
            FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
        )
    """)
    
    # ═══════════════════════════════════════════════════════════
    # 🛒 سفارشات
    # ═══════════════════════════════════════════════════════════
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            restaurant_id INTEGER,
            address_id INTEGER,
            order_number VARCHAR(20) UNIQUE,
            status VARCHAR(30) DEFAULT 'pending',
            subtotal INTEGER,
            discount_amount INTEGER DEFAULT 0,
            delivery_fee INTEGER DEFAULT 0,
            tax_amount INTEGER DEFAULT 0,
            total_amount INTEGER,
            payment_method VARCHAR(30),
            payment_status VARCHAR(20) DEFAULT 'pending',
            delivery_type VARCHAR(20) DEFAULT 'delivery',
            scheduled_time TIMESTAMP,
            estimated_delivery TIMESTAMP,
            actual_delivery TIMESTAMP,
            notes TEXT,
            rating INTEGER,
            review TEXT,
            coupon_code VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id),
            FOREIGN KEY (address_id) REFERENCES addresses(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            menu_item_id INTEGER,
            quantity INTEGER DEFAULT 1,
            unit_price INTEGER,
            total_price INTEGER,
            options TEXT DEFAULT '[]',
            notes TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            status VARCHAR(30),
            note TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    """)
    
    # ═══════════════════════════════════════════════════════════
    # 💳 پرداخت‌ها
    # ═══════════════════════════════════════════════════════════
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            order_id INTEGER,
            amount INTEGER,
            method VARCHAR(30),
            gateway VARCHAR(50),
            transaction_id VARCHAR(100),
            reference_id VARCHAR(100),
            status VARCHAR(20) DEFAULT 'pending',
            card_number VARCHAR(20),
            metadata TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wallet (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            balance INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wallet_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type VARCHAR(20),
            amount INTEGER,
            balance_after INTEGER,
            description TEXT,
            reference_id VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # ═══════════════════════════════════════════════════════════
    # 🎁 تخفیف‌ها و کوپن‌ها
    # ═══════════════════════════════════════════════════════════
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code VARCHAR(50) UNIQUE,
            type VARCHAR(20),
            value INTEGER,
            min_order_amount INTEGER DEFAULT 0,
            max_discount INTEGER,
            usage_limit INTEGER,
            used_count INTEGER DEFAULT 0,
            per_user_limit INTEGER DEFAULT 1,
            restaurant_id INTEGER,
            valid_from TIMESTAMP,
            valid_until TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coupon_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coupon_id INTEGER,
            user_id INTEGER,
            order_id INTEGER,
            discount_amount INTEGER,
            used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (coupon_id) REFERENCES coupons(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    """)
    
    # ═══════════════════════════════════════════════════════════
    # ⭐ امتیاز وفاداری
    # ═══════════════════════════════════════════════════════════
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loyalty_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type VARCHAR(20),
            points INTEGER,
            balance_after INTEGER,
            description TEXT,
            order_id INTEGER,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loyalty_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100),
            description TEXT,
            points_required INTEGER,
            reward_type VARCHAR(30),
            reward_value TEXT,
            image_url TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ═══════════════════════════════════════════════════════════
    # ⭐ نظرات و امتیازها
    # ═══════════════════════════════════════════════════════════
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            restaurant_id INTEGER,
            order_id INTEGER,
            rating INTEGER,
            comment TEXT,
            food_rating INTEGER,
            delivery_rating INTEGER,
            packaging_rating INTEGER,
            images TEXT DEFAULT '[]',
            is_anonymous BOOLEAN DEFAULT 0,
            reply TEXT,
            replied_at TIMESTAMP,
            is_visible BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id),
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    """)
    
    # ═══════════════════════════════════════════════════════════
    # ❤️ علاقه‌مندی‌ها
    # ═══════════════════════════════════════════════════════════
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type VARCHAR(20),
            item_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, type, item_id)
        )
    """)
    
    # ═══════════════════════════════════════════════════════════
    # 🔔 اعلانات
    # ═══════════════════════════════════════════════════════════
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type VARCHAR(30),
            title VARCHAR(200),
            body TEXT,
            data TEXT DEFAULT '{}',
            image_url TEXT,
            is_read BOOLEAN DEFAULT 0,
            read_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS push_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            token TEXT UNIQUE,
            device_type VARCHAR(20),
            device_name VARCHAR(100),
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # ═══════════════════════════════════════════════════════════
    # 💬 پشتیبانی و تیکت
    # ═══════════════════════════════════════════════════════════
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            order_id INTEGER,
            category VARCHAR(50),
            subject VARCHAR(200),
            status VARCHAR(20) DEFAULT 'open',
            priority VARCHAR(20) DEFAULT 'normal',
            assigned_to INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            closed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ticket_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER,
            sender_id INTEGER,
            sender_type VARCHAR(20),
            message TEXT,
            attachments TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ticket_id) REFERENCES support_tickets(id)
        )
    """)
    
    # ═══════════════════════════════════════════════════════════
    # 💬 تاریخچه چت با AI
    # ═══════════════════════════════════════════════════════════
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_id VARCHAR(50),
            role VARCHAR(20),
            content TEXT,
            image_url TEXT,
            audio_url TEXT,
            intent VARCHAR(50),
            entities TEXT DEFAULT '{}',
            sentiment VARCHAR(20),
            confidence REAL,
            response_time_ms INTEGER,
            tokens_used INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT DEFAULT '{}',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title VARCHAR(200) DEFAULT 'مکالمه جدید',
            message_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # ═══════════════════════════════════════════════════════════
    # 👤 پروفایل مشتری (برای AI)
    # ═══════════════════════════════════════════════════════════
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            favorite_foods TEXT DEFAULT '[]',
            favorite_cuisines TEXT DEFAULT '[]',
            allergies TEXT DEFAULT '[]',
            dietary_preferences TEXT DEFAULT '[]',
            spice_level VARCHAR(20),
            avg_order_value REAL DEFAULT 0,
            total_orders INTEGER DEFAULT 0,
            total_spent INTEGER DEFAULT 0,
            last_order_date TIMESTAMP,
            preferred_payment VARCHAR(30),
            preferred_delivery_time TEXT,
            notes TEXT,
            tags TEXT DEFAULT '[]',
            loyalty_points INTEGER DEFAULT 0,
            loyalty_tier VARCHAR(20) DEFAULT 'bronze',
            personality_traits TEXT DEFAULT '{}',
            communication_style VARCHAR(30),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # ═══════════════════════════════════════════════════════════
    # 📊 تحلیل و آمار
    # ═══════════════════════════════════════════════════════════
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analytics_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_id VARCHAR(50),
            event_type VARCHAR(50),
            event_data TEXT DEFAULT '{}',
            page VARCHAR(100),
            device_type VARCHAR(20),
            platform VARCHAR(20),
            app_version VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            query TEXT,
            results_count INTEGER,
            clicked_item_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # ═══════════════════════════════════════════════════════════
    # 📢 کمپین‌ها و بازاریابی
    # ═══════════════════════════════════════════════════════════
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100),
            type VARCHAR(30),
            target_audience TEXT DEFAULT '{}',
            content TEXT,
            image_url TEXT,
            action_url TEXT,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            sent_count INTEGER DEFAULT 0,
            click_count INTEGER DEFAULT 0,
            conversion_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ═══════════════════════════════════════════════════════════
    # 👨‍🍳 کارکنان
    # ═══════════════════════════════════════════════════════════
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id),
            restaurant_id INTEGER REFERENCES restaurants(id),
            position VARCHAR(50),
            department VARCHAR(50),
            hire_date DATE,
            salary INTEGER,
            permissions TEXT DEFAULT '[]',
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            extra_data TEXT DEFAULT '{}'
        )
    """)
    
    # ═══════════════════════════════════════════════════════════
    # 🛵 پیک‌ها
    # ═══════════════════════════════════════════════════════════
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS delivery_persons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id),
            restaurant_id INTEGER REFERENCES restaurants(id),
            vehicle_type VARCHAR(30),
            vehicle_plate VARCHAR(20),
            license_number VARCHAR(50),
            rating REAL DEFAULT 5,
            total_deliveries INTEGER DEFAULT 0,
            status VARCHAR(20) DEFAULT 'offline',
            current_lat REAL,
            current_lng REAL,
            is_active BOOLEAN DEFAULT 1,
            extra_data TEXT DEFAULT '{}'
        )
    """)
    
    # ═══════════════════════════════════════════════════════════
    # 📦 موجودی و انبار
    # ═══════════════════════════════════════════════════════════
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER REFERENCES restaurants(id),
            name VARCHAR(100),
            sku VARCHAR(50),
            category VARCHAR(50),
            unit VARCHAR(20),
            quantity REAL DEFAULT 0,
            min_quantity REAL,
            cost_per_unit INTEGER,
            supplier_id INTEGER REFERENCES suppliers(id),
            expiry_date DATE,
            is_active BOOLEAN DEFAULT 1,
            extra_data TEXT DEFAULT '{}'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER REFERENCES restaurants(id),
            name VARCHAR(100),
            contact_person VARCHAR(100),
            phone VARCHAR(15),
            email VARCHAR(255),
            address TEXT,
            rating REAL,
            is_active BOOLEAN DEFAULT 1,
            extra_data TEXT DEFAULT '{}'
        )
    """)
    
    # ═══════════════════════════════════════════════════════════
    # 🪑 میزها و رزرو
    # ═══════════════════════════════════════════════════════════
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER REFERENCES restaurants(id),
            table_number VARCHAR(20),
            capacity INTEGER,
            location VARCHAR(50),
            status VARCHAR(20) DEFAULT 'available',
            qr_code VARCHAR(100),
            is_active BOOLEAN DEFAULT 1,
            extra_data TEXT DEFAULT '{}'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER REFERENCES restaurants(id),
            user_id INTEGER REFERENCES users(id),
            table_id INTEGER REFERENCES tables(id),
            reservation_code VARCHAR(20) UNIQUE,
            date DATE,
            time TIME,
            duration_minutes INTEGER DEFAULT 90,
            party_size INTEGER,
            guest_name VARCHAR(100),
            guest_phone VARCHAR(15),
            status VARCHAR(20) DEFAULT 'pending',
            special_requests TEXT,
            occasion VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            extra_data TEXT DEFAULT '{}'
        )
    """)
    
    # ═══════════════════════════════════════════════════════════
    # 💰 هزینه‌ها و گزارش‌ها
    # ═══════════════════════════════════════════════════════════
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER REFERENCES restaurants(id),
            category VARCHAR(50),
            amount INTEGER,
            description TEXT,
            receipt_url TEXT,
            date DATE,
            created_by INTEGER REFERENCES users(id),
            extra_data TEXT DEFAULT '{}'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER REFERENCES restaurants(id),
            date DATE,
            total_orders INTEGER DEFAULT 0,
            total_revenue INTEGER DEFAULT 0,
            total_expenses INTEGER DEFAULT 0,
            net_profit INTEGER DEFAULT 0,
            avg_order_value REAL DEFAULT 0,
            new_customers INTEGER DEFAULT 0,
            data TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ═══════════════════════════════════════════════════════════
    # 🧪 تست و فیچر فلگ
    # ═══════════════════════════════════════════════════════════
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feature_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) UNIQUE,
            description TEXT,
            is_enabled BOOLEAN DEFAULT 0,
            rollout_percent INTEGER DEFAULT 0,
            user_segments TEXT DEFAULT '[]',
            extra_data TEXT DEFAULT '{}'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ab_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100),
            description TEXT,
            variants TEXT DEFAULT '[]',
            traffic_split TEXT DEFAULT '{}',
            metric VARCHAR(50),
            is_active BOOLEAN DEFAULT 1,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            results TEXT DEFAULT '{}',
            extra_data TEXT DEFAULT '{}'
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Database initialized with 40+ tables!")


# ═══════════════════════════════════════════════════════════
# 🔄 Migration System - برای اضافه کردن فیلدهای جدید
# ═══════════════════════════════════════════════════════════

def add_column_if_not_exists(cursor, table: str, column: str, column_type: str):
    """اضافه کردن ستون اگر وجود نداشته باشد"""
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
        print(f"  ✓ Added {table}.{column}")
        return True
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            return False  # Column exists
        raise e


def run_migrations():
    """
    اجرای مایگریشن‌ها برای اضافه کردن فیلدهای جدید
    
    💡 برای اضافه کردن فیلد جدید:
    1. به MIGRATIONS اضافه کن
    2. python -c "import database; database.run_migrations()" اجرا کن
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    print("\n🔄 Running migrations...")
    
    # ═══════════════════════════════════════════════════════════
    # لیست مایگریشن‌ها
    # فرمت: (table, column, type)
    # ═══════════════════════════════════════════════════════════
    
    MIGRATIONS = [
        # فیلدهای جدید users
        ("users", "national_id", "VARCHAR(20)"),
        ("users", "job_title", "VARCHAR(100)"),
        ("users", "company", "VARCHAR(200)"),
        ("users", "instagram", "VARCHAR(100)"),
        ("users", "telegram", "VARCHAR(100)"),
        ("users", "timezone", "VARCHAR(50) DEFAULT 'Asia/Tehran'"),
        ("users", "notification_settings", "TEXT DEFAULT '{}'"),
        ("users", "marketing_consent", "BOOLEAN DEFAULT 1"),
        ("users", "deleted_at", "TIMESTAMP"),
        ("users", "extra_data", "TEXT DEFAULT '{}'"),
        
        # فیلدهای جدید customer_profiles
        ("customer_profiles", "favorite_cuisines", "TEXT DEFAULT '[]'"),
        ("customer_profiles", "disliked_foods", "TEXT DEFAULT '[]'"),
        ("customer_profiles", "portion_size", "VARCHAR(20)"),
        ("customer_profiles", "order_frequency", "VARCHAR(20)"),
        ("customer_profiles", "preferred_order_time", "TEXT"),
        ("customer_profiles", "preferred_delivery_type", "VARCHAR(20)"),
        ("customer_profiles", "lifetime_value", "INTEGER DEFAULT 0"),
        ("customer_profiles", "first_order_date", "TIMESTAMP"),
        ("customer_profiles", "customer_segment", "VARCHAR(30)"),
        ("customer_profiles", "churn_risk", "REAL DEFAULT 0"),
        ("customer_profiles", "satisfaction_score", "REAL"),
        ("customer_profiles", "nps_score", "INTEGER"),
        ("customer_profiles", "preferred_contact_method", "VARCHAR(20)"),
        ("customer_profiles", "best_contact_time", "TEXT"),
        ("customer_profiles", "interests", "TEXT DEFAULT '[]'"),
        ("customer_profiles", "special_dates", "TEXT DEFAULT '[]'"),
        ("customer_profiles", "last_profile_update", "TIMESTAMP"),
        ("customer_profiles", "extra_data", "TEXT DEFAULT '{}'"),
        
        # فیلدهای جدید sessions
        ("sessions", "refresh_token", "VARCHAR(64)"),
        ("sessions", "device_id", "VARCHAR(100)"),
        ("sessions", "location", "TEXT"),
        
        # فیلدهای جدید addresses
        ("addresses", "street", "VARCHAR(200)"),
        ("addresses", "alley", "VARCHAR(100)"),
        ("addresses", "building_name", "VARCHAR(100)"),
        ("addresses", "delivery_instructions", "TEXT"),
        ("addresses", "is_verified", "BOOLEAN DEFAULT 0"),
        
        # فیلدهای جدید restaurants
        ("restaurants", "owner_id", "INTEGER REFERENCES users(id)"),
        ("restaurants", "short_description", "VARCHAR(500)"),
        ("restaurants", "images", "TEXT DEFAULT '[]'"),
        ("restaurants", "whatsapp", "VARCHAR(15)"),
        ("restaurants", "website", "VARCHAR(255)"),
        ("restaurants", "instagram", "VARCHAR(100)"),
        ("restaurants", "free_delivery_above", "INTEGER"),
        ("restaurants", "delivery_radius_km", "REAL"),
        ("restaurants", "accepts_online_payment", "BOOLEAN DEFAULT 1"),
        ("restaurants", "accepts_cash", "BOOLEAN DEFAULT 1"),
        ("restaurants", "holiday_dates", "TEXT DEFAULT '[]'"),
        ("restaurants", "cuisine_types", "TEXT DEFAULT '[]'"),
        ("restaurants", "features", "TEXT DEFAULT '[]'"),
        ("restaurants", "commission_rate", "REAL DEFAULT 0"),
        ("restaurants", "bank_account", "TEXT"),
        ("restaurants", "tax_id", "VARCHAR(50)"),
        ("restaurants", "extra_data", "TEXT DEFAULT '{}'"),
        
        # فیلدهای جدید menu_items
        ("menu_items", "sku", "VARCHAR(50)"),
        ("menu_items", "name_en", "VARCHAR(100)"),
        ("menu_items", "short_description", "VARCHAR(300)"),
        ("menu_items", "video_url", "TEXT"),
        ("menu_items", "discount_percent", "INTEGER"),
        ("menu_items", "discount_until", "TIMESTAMP"),
        ("menu_items", "nutrition_info", "TEXT DEFAULT '{}'"),
        ("menu_items", "serving_size", "VARCHAR(50)"),
        ("menu_items", "spice_level", "VARCHAR(20)"),
        ("menu_items", "is_bestseller", "BOOLEAN DEFAULT 0"),
        ("menu_items", "is_chef_special", "BOOLEAN DEFAULT 0"),
        ("menu_items", "stock_count", "INTEGER"),
        ("menu_items", "low_stock_alert", "INTEGER"),
        ("menu_items", "max_per_order", "INTEGER"),
        ("menu_items", "extra_data", "TEXT DEFAULT '{}'"),
        
        # فیلدهای جدید orders
        ("orders", "branch_id", "INTEGER REFERENCES restaurant_branches(id)"),
        ("orders", "table_id", "INTEGER REFERENCES tables(id)"),
        ("orders", "delivery_person_id", "INTEGER REFERENCES delivery_persons(id)"),
        ("orders", "order_type", "VARCHAR(20) DEFAULT 'delivery'"),
        ("orders", "substatus", "VARCHAR(30)"),
        ("orders", "service_fee", "INTEGER DEFAULT 0"),
        ("orders", "tip_amount", "INTEGER DEFAULT 0"),
        ("orders", "is_scheduled", "BOOLEAN DEFAULT 0"),
        ("orders", "estimated_prep_time", "INTEGER"),
        ("orders", "prep_started_at", "TIMESTAMP"),
        ("orders", "ready_at", "TIMESTAMP"),
        ("orders", "picked_up_at", "TIMESTAMP"),
        ("orders", "delivered_at", "TIMESTAMP"),
        ("orders", "items_count", "INTEGER DEFAULT 0"),
        ("orders", "delivery_instructions", "TEXT"),
        ("orders", "refund_amount", "INTEGER DEFAULT 0"),
        ("orders", "review_images", "TEXT DEFAULT '[]'"),
        ("orders", "source", "VARCHAR(30)"),
        ("orders", "device_type", "VARCHAR(20)"),
        ("orders", "app_version", "VARCHAR(20)"),
        ("orders", "extra_data", "TEXT DEFAULT '{}'"),
    ]
    
    added = 0
    for table, column, column_type in MIGRATIONS:
        if add_column_if_not_exists(cursor, table, column, column_type):
            added += 1
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Migration complete! ({added} new columns added)")


# ===== User Functions =====

def create_user(phone: str = None, email: str = None, name: str = None) -> int:
    """ایجاد کاربر جدید"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO users (phone, email, name) VALUES (?, ?, ?)
    """, (phone, email, name))
    
    user_id = cursor.lastrowid
    
    # ساخت پروفایل مشتری
    cursor.execute("""
        INSERT INTO customer_profiles (user_id) VALUES (?)
    """, (user_id,))
    
    conn.commit()
    conn.close()
    return user_id


def get_user_by_phone(phone: str) -> Optional[Dict]:
    """دریافت کاربر با شماره موبایل"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE phone = ?", (phone,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_email(email: str) -> Optional[Dict]:
    """دریافت کاربر با ایمیل"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """دریافت کاربر با ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_last_login(user_id: int):
    """آپدیت زمان آخرین لاگین"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET last_login = ? WHERE id = ?
    """, (datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()


# ===== Chat History Functions =====

def save_message(user_id: int, role: str, content: str, image_url: str = None, metadata: dict = None):
    """ذخیره پیام در تاریخچه"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_history (user_id, role, content, image_url, metadata)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, role, content, image_url, json.dumps(metadata or {})))
    conn.commit()
    conn.close()


def get_chat_history(user_id: int, limit: int = 50) -> List[Dict]:
    """دریافت تاریخچه چت کاربر"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM chat_history 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in reversed(rows)]


def get_recent_context(user_id: int, limit: int = 10) -> str:
    """دریافت context اخیر برای Gemini"""
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
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT cp.*, u.name, u.phone, u.email
        FROM customer_profiles cp
        JOIN users u ON cp.user_id = u.id
        WHERE cp.user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        profile = dict(row)
        profile['favorite_foods'] = json.loads(profile.get('favorite_foods', '[]'))
        profile['allergies'] = json.loads(profile.get('allergies', '[]'))
        profile['dietary_preferences'] = json.loads(profile.get('dietary_preferences', '[]'))
        return profile
    return None


def update_customer_profile(user_id: int, **kwargs):
    """آپدیت پروفایل مشتری"""
    conn = get_connection()
    cursor = conn.cursor()
    
    allowed_fields = ['favorite_foods', 'allergies', 'dietary_preferences', 
                      'avg_order_value', 'total_orders', 'last_order_date', 'notes']
    
    for key, value in kwargs.items():
        if key in allowed_fields:
            if key in ['favorite_foods', 'allergies', 'dietary_preferences']:
                value = json.dumps(value)
            cursor.execute(f"""
                UPDATE customer_profiles SET {key} = ? WHERE user_id = ?
            """, (value, user_id))
    
    conn.commit()
    conn.close()


def get_customer_context(user_id: int) -> str:
    """
    ساخت context کامل مشتری برای ارسال به Gemini
    شامل: نام، ترجیحات، آلرژی‌ها، تاریخچه سفارش و...
    """
    profile = get_customer_profile(user_id)
    if not profile:
        return ""
    
    context_parts = []
    
    if profile.get('name'):
        context_parts.append(f"نام مشتری: {profile['name']}")
    
    if profile.get('favorite_foods'):
        context_parts.append(f"غذاهای مورد علاقه: {', '.join(profile['favorite_foods'])}")
    
    if profile.get('allergies'):
        context_parts.append(f"⚠️ آلرژی‌ها: {', '.join(profile['allergies'])}")
    
    if profile.get('dietary_preferences'):
        context_parts.append(f"رژیم غذایی: {', '.join(profile['dietary_preferences'])}")
    
    if profile.get('total_orders', 0) > 0:
        context_parts.append(f"تعداد سفارشات قبلی: {profile['total_orders']}")
    
    if profile.get('notes'):
        context_parts.append(f"یادداشت: {profile['notes']}")
    
    return "\n".join(context_parts)


# Initialize database on import
init_database()

