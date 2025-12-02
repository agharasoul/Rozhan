"""
🚀 مهاجرت از SQLite به PostgreSQL
اطلاعات رو میخونه و میریزه توی دیتابیس جدید
"""

import sqlite3
import psycopg2
import json
from datetime import datetime

# SQLite Connection
sqlite_conn = sqlite3.connect('rozhan.db')
sqlite_conn.row_factory = sqlite3.Row
sqlite_cursor = sqlite_conn.cursor()

# PostgreSQL Connection
pg_conn = psycopg2.connect('postgresql://postgres:aseman777@localhost:5432/rozhan')
pg_cursor = pg_conn.cursor()

def migrate():
    print("📦 Starting Migration...")
    
    # 1️⃣ Users
    print("👤 Migrating Users...")
    sqlite_cursor.execute("SELECT * FROM users")
    users = sqlite_cursor.fetchall()
    for user in users:
        try:
            pg_cursor.execute("""
                INSERT INTO users (id, phone, email, name, created_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (user['id'], user['phone'], user['email'], user['name'], user['created_at']))
        except Exception as e:
            print(f"❌ User Error ({user['id']}): {e}")
            pg_conn.rollback()
    pg_conn.commit()
    
    # 2️⃣ Chat History
    print("💬 Migrating Chat History...")
    sqlite_cursor.execute("SELECT * FROM chat_history")
    chats = sqlite_cursor.fetchall()
    for chat in chats:
        try:
            pg_cursor.execute("""
                INSERT INTO chat_history (id, user_id, role, content, image_url, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (chat['id'], chat['user_id'], chat['role'], chat['content'], chat['image_url'], chat['created_at']))
        except Exception as e:
            print(f"❌ Chat Error ({chat['id']}): {e}")
            pg_conn.rollback()
    pg_conn.commit()
    
    # 3️⃣ Customer Profiles
    print("🧠 Migrating Profiles...")
    sqlite_cursor.execute("SELECT * FROM customer_profiles")
    profiles = sqlite_cursor.fetchall()
    for p in profiles:
        try:
            # Fix JSON fields
            fav_foods = p['favorite_foods'] if p['favorite_foods'] else '[]'
            allergies = p['allergies'] if p['allergies'] else '[]'
            diet = p['dietary_preferences'] if p['dietary_preferences'] else '[]'
            extra = p['extra_data'] if p['extra_data'] else '{}'
            
            pg_cursor.execute("""
                INSERT INTO customer_profiles (
                    user_id, favorite_foods, allergies, dietary_preferences, 
                    avg_order_value, total_orders, notes, loyalty_points
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
            """, (
                p['user_id'], fav_foods, allergies, diet,
                p['avg_order_value'], p['total_orders'], extra, p['loyalty_points']
            ))
        except Exception as e:
            print(f"❌ Profile Error ({p['user_id']}): {e}")
            pg_conn.rollback()
    pg_conn.commit()
    
    print("✅ Migration Complete!")

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"❌ Fatal Error: {e}")
    finally:
        sqlite_conn.close()
        pg_conn.close()

