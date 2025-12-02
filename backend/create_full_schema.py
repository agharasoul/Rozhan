"""
🏗️ ساخت Schema کامل PostgreSQL
"""

import psycopg2

conn = psycopg2.connect('postgresql://postgres:aseman777@localhost:5432/rozhan')
conn.autocommit = True
cur = conn.cursor()

print('🏗️ Creating comprehensive database schema...\n')

# ========== RESTAURANTS ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS restaurants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE,
    logo_url TEXT,
    banner_url TEXT,
    description TEXT,
    address TEXT,
    lat DECIMAL(10,8),
    lng DECIMAL(11,8),
    phone VARCHAR(20),
    email VARCHAR(255),
    website VARCHAR(255),
    rating DECIMAL(2,1) DEFAULT 0,
    review_count INTEGER DEFAULT 0,
    delivery_fee INTEGER DEFAULT 0,
    min_order_amount INTEGER DEFAULT 0,
    avg_delivery_time INTEGER DEFAULT 30,
    opening_time TIME,
    closing_time TIME,
    is_open BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    cuisine_types JSONB DEFAULT '[]',
    tags JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ restaurants')

# ========== MENU CATEGORIES ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS menu_categories (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER REFERENCES restaurants(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    image_url TEXT,
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ menu_categories')

# ========== MENU ITEMS ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS menu_items (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER REFERENCES restaurants(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES menu_categories(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price INTEGER NOT NULL,
    discount_price INTEGER,
    image_url TEXT,
    calories INTEGER,
    prep_time INTEGER,
    ingredients JSONB DEFAULT '[]',
    allergens JSONB DEFAULT '[]',
    tags JSONB DEFAULT '[]',
    is_vegetarian BOOLEAN DEFAULT FALSE,
    is_vegan BOOLEAN DEFAULT FALSE,
    is_spicy BOOLEAN DEFAULT FALSE,
    spice_level INTEGER DEFAULT 0,
    is_available BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    sort_order INTEGER DEFAULT 0,
    rating DECIMAL(2,1) DEFAULT 0,
    order_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ menu_items')

# ========== MENU OPTIONS (Add-ons) ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS menu_options (
    id SERIAL PRIMARY KEY,
    menu_item_id INTEGER REFERENCES menu_items(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    price INTEGER DEFAULT 0,
    is_required BOOLEAN DEFAULT FALSE,
    max_selections INTEGER DEFAULT 1,
    options JSONB DEFAULT '[]'
)
""")
print('✓ menu_options')

# ========== ADDRESSES ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS addresses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(100),
    full_address TEXT NOT NULL,
    unit VARCHAR(50),
    floor VARCHAR(20),
    lat DECIMAL(10,8),
    lng DECIMAL(11,8),
    city VARCHAR(100),
    district VARCHAR(100),
    postal_code VARCHAR(20),
    receiver_name VARCHAR(100),
    receiver_phone VARCHAR(20),
    notes TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ addresses')

# ========== ORDERS ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    restaurant_id INTEGER REFERENCES restaurants(id),
    address_id INTEGER REFERENCES addresses(id),
    order_number VARCHAR(20) UNIQUE,
    status VARCHAR(50) DEFAULT 'pending',
    subtotal INTEGER DEFAULT 0,
    delivery_fee INTEGER DEFAULT 0,
    discount INTEGER DEFAULT 0,
    tax INTEGER DEFAULT 0,
    total INTEGER DEFAULT 0,
    payment_method VARCHAR(50),
    payment_status VARCHAR(50) DEFAULT 'pending',
    delivery_type VARCHAR(50) DEFAULT 'delivery',
    scheduled_for TIMESTAMP,
    notes TEXT,
    rating INTEGER,
    review TEXT,
    estimated_delivery TIMESTAMP,
    actual_delivery TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ orders')

# ========== ORDER ITEMS ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    menu_item_id INTEGER REFERENCES menu_items(id),
    name VARCHAR(255),
    quantity INTEGER DEFAULT 1,
    unit_price INTEGER,
    total_price INTEGER,
    options JSONB DEFAULT '[]',
    notes TEXT
)
""")
print('✓ order_items')

# ========== ORDER STATUS HISTORY ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS order_status_history (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    status VARCHAR(50),
    note TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ order_status_history')

# ========== PAYMENTS ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    user_id INTEGER REFERENCES users(id),
    amount INTEGER NOT NULL,
    method VARCHAR(50),
    status VARCHAR(50) DEFAULT 'pending',
    gateway VARCHAR(50),
    transaction_id VARCHAR(255),
    ref_number VARCHAR(255),
    card_number VARCHAR(20),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ payments')

# ========== WALLET ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS wallet (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) UNIQUE,
    balance INTEGER DEFAULT 0,
    total_earned INTEGER DEFAULT 0,
    total_spent INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ wallet')

# ========== WALLET TRANSACTIONS ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS wallet_transactions (
    id SERIAL PRIMARY KEY,
    wallet_id INTEGER REFERENCES wallet(id),
    user_id INTEGER REFERENCES users(id),
    type VARCHAR(50),
    amount INTEGER,
    balance_after INTEGER,
    description TEXT,
    reference_type VARCHAR(50),
    reference_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ wallet_transactions')

# ========== COUPONS ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS coupons (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(255),
    description TEXT,
    type VARCHAR(50) DEFAULT 'percent',
    value INTEGER,
    min_order INTEGER DEFAULT 0,
    max_discount INTEGER,
    usage_limit INTEGER,
    used_count INTEGER DEFAULT 0,
    per_user_limit INTEGER DEFAULT 1,
    valid_from TIMESTAMP,
    valid_until TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    restaurant_id INTEGER REFERENCES restaurants(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ coupons')

# ========== COUPON USAGE ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS coupon_usage (
    id SERIAL PRIMARY KEY,
    coupon_id INTEGER REFERENCES coupons(id),
    user_id INTEGER REFERENCES users(id),
    order_id INTEGER REFERENCES orders(id),
    discount_amount INTEGER,
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ coupon_usage')

# ========== FAVORITES ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS favorites (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    menu_item_id INTEGER REFERENCES menu_items(id) ON DELETE CASCADE,
    restaurant_id INTEGER REFERENCES restaurants(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, menu_item_id)
)
""")
print('✓ favorites')

# ========== REVIEWS ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    order_id INTEGER REFERENCES orders(id),
    restaurant_id INTEGER REFERENCES restaurants(id),
    menu_item_id INTEGER REFERENCES menu_items(id),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    food_rating INTEGER,
    delivery_rating INTEGER,
    packaging_rating INTEGER,
    comment TEXT,
    images JSONB DEFAULT '[]',
    is_verified BOOLEAN DEFAULT FALSE,
    reply TEXT,
    replied_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ reviews')

# ========== NOTIFICATIONS ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50),
    title VARCHAR(255),
    body TEXT,
    data JSONB DEFAULT '{}',
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ notifications')

# ========== PUSH TOKENS ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS push_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    device_type VARCHAR(50),
    device_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ push_tokens')

# ========== SUPPORT TICKETS ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS support_tickets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    order_id INTEGER REFERENCES orders(id),
    subject VARCHAR(255),
    category VARCHAR(100),
    priority VARCHAR(50) DEFAULT 'medium',
    status VARCHAR(50) DEFAULT 'open',
    assigned_to VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP
)
""")
print('✓ support_tickets')

# ========== TICKET MESSAGES ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS ticket_messages (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES support_tickets(id) ON DELETE CASCADE,
    sender_type VARCHAR(50),
    sender_id INTEGER,
    message TEXT,
    attachments JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ ticket_messages')

# ========== LOYALTY TRANSACTIONS ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS loyalty_transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    points INTEGER,
    type VARCHAR(50),
    description TEXT,
    reference_type VARCHAR(50),
    reference_id INTEGER,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ loyalty_transactions')

# ========== LOYALTY REWARDS ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS loyalty_rewards (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    points_required INTEGER,
    reward_type VARCHAR(50),
    reward_value INTEGER,
    image_url TEXT,
    quantity_available INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ loyalty_rewards')

# ========== SEARCH HISTORY ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS search_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    query VARCHAR(255),
    results_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ search_history')

# ========== ANALYTICS EVENTS ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS analytics_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    session_id VARCHAR(255),
    event_type VARCHAR(100),
    event_name VARCHAR(255),
    properties JSONB DEFAULT '{}',
    device_info JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ analytics_events')

# ========== DELIVERY PERSONS ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS delivery_persons (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    phone VARCHAR(20),
    email VARCHAR(255),
    vehicle_type VARCHAR(50),
    vehicle_number VARCHAR(50),
    lat DECIMAL(10,8),
    lng DECIMAL(11,8),
    status VARCHAR(50) DEFAULT 'offline',
    rating DECIMAL(2,1) DEFAULT 5.0,
    total_deliveries INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ delivery_persons')

# ========== DELIVERY TRACKING ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS delivery_tracking (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    delivery_person_id INTEGER REFERENCES delivery_persons(id),
    status VARCHAR(50),
    lat DECIMAL(10,8),
    lng DECIMAL(11,8),
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ delivery_tracking')

# ========== PROMOTIONS ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS promotions (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    description TEXT,
    image_url TEXT,
    type VARCHAR(50),
    target_type VARCHAR(50),
    target_id INTEGER,
    action_type VARCHAR(50),
    action_value TEXT,
    priority INTEGER DEFAULT 0,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ promotions')

# ========== BANNERS ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS banners (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    image_url TEXT NOT NULL,
    link_type VARCHAR(50),
    link_value TEXT,
    position VARCHAR(50) DEFAULT 'home',
    sort_order INTEGER DEFAULT 0,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    click_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ banners')

# ========== APP SETTINGS ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS app_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    type VARCHAR(50) DEFAULT 'string',
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ app_settings')

# ========== FEATURE FLAGS ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS feature_flags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_enabled BOOLEAN DEFAULT FALSE,
    rollout_percentage INTEGER DEFAULT 0,
    user_ids JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ feature_flags')

# ========== AI LEARNING ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS ai_learned_patterns (
    id SERIAL PRIMARY KEY,
    pattern_type VARCHAR(100),
    pattern_key VARCHAR(255),
    pattern_value TEXT,
    confidence DECIMAL(3,2) DEFAULT 0,
    usage_count INTEGER DEFAULT 0,
    last_used TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ ai_learned_patterns')

# ========== USER PREFERENCES ==========
cur.execute("""
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    language VARCHAR(10) DEFAULT 'fa',
    theme VARCHAR(20) DEFAULT 'dark',
    notifications_enabled BOOLEAN DEFAULT TRUE,
    email_notifications BOOLEAN DEFAULT TRUE,
    sms_notifications BOOLEAN DEFAULT TRUE,
    push_notifications BOOLEAN DEFAULT TRUE,
    location_sharing BOOLEAN DEFAULT FALSE,
    data_collection BOOLEAN DEFAULT TRUE,
    personalization BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print('✓ user_preferences')

# ========== CREATE INDEXES ==========
print('\n📇 Creating indexes...')
cur.execute('CREATE INDEX IF NOT EXISTS idx_menu_items_restaurant ON menu_items(restaurant_id)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_menu_items_category ON menu_items(category_id)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_orders_restaurant ON orders(restaurant_id)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_addresses_user ON addresses(user_id)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_reviews_restaurant ON reviews(restaurant_id)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_analytics_user ON analytics_events(user_id)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_analytics_event ON analytics_events(event_type)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_delivery_tracking_order ON delivery_tracking(order_id)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_wallet_transactions_user ON wallet_transactions(user_id)')

print('\n' + '=' * 50)
print('✅ ALL TABLES CREATED SUCCESSFULLY!')
print('=' * 50)

conn.close()

