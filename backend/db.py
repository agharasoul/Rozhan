"""
🗄️ Database Wrapper
انتخاب خودکار بین SQLite و PostgreSQL+Redis
"""

import os

DB_MODE = os.environ.get('DB_MODE', 'sqlite').lower()

if DB_MODE == 'postgres':
    print("📦 Using PostgreSQL + Redis")
    from database_pg import *
else:
    print("📦 Using SQLite")
    from database import *

