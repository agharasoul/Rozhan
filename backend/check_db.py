import sys
sys.stdout.reconfigure(encoding='utf-8')
import database_pg as db

conn = db.get_connection()
cur = conn.cursor()

# List tables
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
tables = [r['table_name'] for r in cur.fetchall()]
print("📋 Tables:", tables)

# Check restaurants
cur.execute("SELECT COUNT(*) as cnt FROM restaurants")
r = cur.fetchone()
print(f"🏪 Restaurants: {r['cnt']}")

# Check menu_items
cur.execute("SELECT COUNT(*) as cnt FROM menu_items")
m = cur.fetchone()
print(f"🍕 Menu items: {m['cnt']}")

# Check orders
cur.execute("SELECT COUNT(*) as cnt FROM orders")
o = cur.fetchone()
print(f"📦 Orders: {o['cnt']}")

conn.close()
