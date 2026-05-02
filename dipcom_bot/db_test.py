#!/usr/bin/env python3
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def test_connection():
    try:
        conn = await asyncpg.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', 5432),
            database=os.getenv('DB_NAME', 'resource_bot'),
            user=os.getenv('DB_USER', 'bot_admin'),
            password=os.getenv('DB_PASSWORD', 'SecurePass123')
        )
        print("✅ PostgreSQL connection successful!")
        
        # Test creating a table
        await conn.execute('CREATE TABLE IF NOT EXISTS test_table (id SERIAL PRIMARY KEY)')
        print("✅ Can create tables (permissions work)")
        
        await conn.close()
        return True
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        print("\nPossible fixes:")
        print("1. Install PostgreSQL: sudo apt install postgresql")
        print("2. Start PostgreSQL: sudo systemctl start postgresql")
        print("3. Create database with the setup commands above")
        return False

if __name__ == "__main__":
    asyncio.run(test_connection())