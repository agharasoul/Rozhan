"""
🌱 داده‌های نمونه برای تست
"""

import db

def seed_restaurant_and_menu():
    """اضافه کردن رستوران و منوی نمونه"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # چک کن رستوران هست یا نه
    cursor.execute("SELECT id FROM restaurants LIMIT 1")
    if cursor.fetchone():
        print("📦 داده‌ها قبلاً اضافه شده!")
        conn.close()
        return
    
    print("🌱 Adding sample data...")
    
    # 1️⃣ رستوران نمونه
    cursor.execute("""
        INSERT INTO restaurants (name, logo_url, address, phone, rating, delivery_fee, min_order_amount, is_open, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "پیتزا روژان",
        "🍕",
        "تهران، خیابان ولیعصر",
        "021-12345678",
        4.5,
        15000,
        50000,
        1,
        1
    ))
    restaurant_id = cursor.lastrowid
    print(f"  ✅ Restaurant added (ID: {restaurant_id})")
    
    # 2️⃣ دسته‌بندی‌ها
    categories = [
        ("🍕 پیتزا", "pizza", 1),
        ("🍔 برگر", "burger", 2),
        ("🥗 سالاد", "salad", 3),
        ("🥤 نوشیدنی", "drink", 4),
    ]
    
    category_ids = {}
    for name, icon, order in categories:
        cursor.execute("""
            INSERT INTO menu_categories (restaurant_id, name, icon, sort_order, is_active)
            VALUES (?, ?, ?, ?, 1)
        """, (restaurant_id, name, icon, order))
        category_ids[icon] = cursor.lastrowid
    print(f"  ✅ {len(categories)} categories added")
    
    # 3️⃣ آیتم‌های منو
    menu_items = [
        # پیتزا
        ("پیتزا پپرونی", "پیتزا با پپرونی تازه و پنیر موزارلا", 180000, "pizza", 1),
        ("پیتزا مخصوص", "پیتزا با گوشت، قارچ، فلفل و زیتون", 220000, "pizza", 2),
        ("پیتزا سبزیجات", "پیتزا گیاهی با سبزیجات تازه", 160000, "pizza", 3),
        ("پیتزا مارگاریتا", "پیتزا کلاسیک با گوجه و ریحان", 150000, "pizza", 4),
        
        # برگر
        ("چیزبرگر", "برگر گوشت با پنیر چدار", 120000, "burger", 1),
        ("دبل برگر", "دو لایه گوشت با پنیر", 180000, "burger", 2),
        ("برگر مرغ", "فیله مرغ سوخاری", 110000, "burger", 3),
        
        # سالاد
        ("سالاد سزار", "کاهو، مرغ، نان تست، سس سزار", 85000, "salad", 1),
        ("سالاد فصل", "سبزیجات تازه فصل", 65000, "salad", 2),
        
        # نوشیدنی
        ("نوشابه", "کوکا / فانتا / اسپرایت", 15000, "drink", 1),
        ("دوغ", "دوغ محلی", 12000, "drink", 2),
        ("آب معدنی", "۵۰۰ میلی‌لیتر", 8000, "drink", 3),
    ]
    
    for name, desc, price, cat, order in menu_items:
        cursor.execute("""
            INSERT INTO menu_items (restaurant_id, category_id, name, description, price, sort_order, is_available)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (restaurant_id, category_ids[cat], name, desc, price, order))
    print(f"  ✅ {len(menu_items)} menu items added")
    
    conn.commit()
    conn.close()
    print("\n✅ Sample data ready!")


if __name__ == "__main__":
    seed_restaurant_and_menu()

