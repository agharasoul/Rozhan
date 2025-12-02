-- ═══════════════════════════════════════════════════════════
-- 🆕 جداول اضافی برای توسعه آینده
-- برای اجرا: sqlite3 rozhan.db < schema_extensions.sql
-- ═══════════════════════════════════════════════════════════

-- 👨‍🍳 کارکنان
CREATE TABLE IF NOT EXISTS staff (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    restaurant_id INTEGER REFERENCES restaurants(id),
    position VARCHAR(50),
    hire_date DATE,
    salary INTEGER,
    is_active BOOLEAN DEFAULT 1,
    extra_data TEXT DEFAULT '{}'
);

-- 🛵 پیک‌ها
CREATE TABLE IF NOT EXISTS delivery_persons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    vehicle_type VARCHAR(30),
    vehicle_plate VARCHAR(20),
    rating REAL DEFAULT 5,
    status VARCHAR(20) DEFAULT 'offline',
    current_lat REAL,
    current_lng REAL,
    extra_data TEXT DEFAULT '{}'
);

-- 📦 موجودی
CREATE TABLE IF NOT EXISTS inventory_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER REFERENCES restaurants(id),
    name VARCHAR(100),
    sku VARCHAR(50),
    unit VARCHAR(20),
    quantity REAL DEFAULT 0,
    min_quantity REAL,
    cost_per_unit INTEGER,
    extra_data TEXT DEFAULT '{}'
);

-- 🏭 تأمین‌کنندگان
CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER REFERENCES restaurants(id),
    name VARCHAR(100),
    phone VARCHAR(15),
    email VARCHAR(255),
    extra_data TEXT DEFAULT '{}'
);

-- 🪑 میزها
CREATE TABLE IF NOT EXISTS tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER REFERENCES restaurants(id),
    table_number VARCHAR(20),
    capacity INTEGER,
    status VARCHAR(20) DEFAULT 'available',
    extra_data TEXT DEFAULT '{}'
);

-- 📅 رزروها
CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER REFERENCES restaurants(id),
    user_id INTEGER REFERENCES users(id),
    table_id INTEGER REFERENCES tables(id),
    date DATE,
    time TIME,
    party_size INTEGER,
    status VARCHAR(20) DEFAULT 'pending',
    extra_data TEXT DEFAULT '{}'
);

-- 💰 هزینه‌ها
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER REFERENCES restaurants(id),
    category VARCHAR(50),
    amount INTEGER,
    description TEXT,
    date DATE,
    extra_data TEXT DEFAULT '{}'
);

-- 📊 گزارش‌ها
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER REFERENCES restaurants(id),
    type VARCHAR(50),
    period VARCHAR(20),
    data TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 🧪 تست A/B
CREATE TABLE IF NOT EXISTS ab_tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100),
    variants TEXT DEFAULT '[]',
    traffic_split TEXT DEFAULT '{}',
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 🚩 فیچر فلگ
CREATE TABLE IF NOT EXISTS feature_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE,
    is_enabled BOOLEAN DEFAULT 0,
    rollout_percent INTEGER DEFAULT 0,
    user_segments TEXT DEFAULT '[]',
    extra_data TEXT DEFAULT '{}'
);
