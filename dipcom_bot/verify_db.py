#!/usr/bin/env python3
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

conn = pymysql.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    port=int(os.getenv('DB_PORT', 3306)),
    user=os.getenv('DB_USER', 'bot_admin'),
    password=os.getenv('DB_PASSWORD', 'SecurePass123'),
    database=os.getenv('DB_NAME', 'resource_bot'),
    charset='utf8mb4',
)

cursor = conn.cursor()
cursor.execute("SHOW TABLES;")
tables = cursor.fetchall()

print("✅ Tables in resource_bot database:")
for table in tables:
    print(f"   - {table[0]}")

print("\n📋 System settings:")
cursor.execute("SELECT * FROM system_settings;")
settings = cursor.fetchall()
for setting in settings:
    print(f"   {setting}")

cursor.close()
conn.close()
