#!/usr/bin/env python3
"""
Clear all data from database tables without dropping the database or tables.
This preserves the table structure but removes all records.
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

async def clear_all_data():
    """Clear all data from all tables while preserving structure"""
    
    # Database configuration from .env
    config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'user': os.getenv('DB_USER', 'bot_admin'),
        'password': os.getenv('DB_PASSWORD', 'SecurePass123'),
        'database': os.getenv('DB_NAME', 'resource_bot')
    }
    
    print("=" * 60)
    print("🗑️  DATABASE DATA CLEARING UTILITY")
    print("=" * 60)
    print(f"Database: {config['database']}")
    print(f"Host: {config['host']}:{config['port']}")
    print("=" * 60)
    
    # Show warning
    print("\n⚠️  WARNING: This will DELETE ALL DATA from ALL tables!")
    print("The table structures will remain intact.")
    print("This action CANNOT be undone!\n")
    
    confirmation = input("Type 'CLEAR ALL DATA' to continue: ")
    
    if confirmation != "CLEAR ALL DATA":
        print("\n❌ Operation cancelled.")
        return False
    
    try:
        # Connect to database
        conn = await asyncpg.connect(**config)
        print("\n✅ Connected to database")
        
        # Get list of all tables in public schema
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        
        if not tables:
            print("❌ No tables found in database!")
            await conn.close()
            return False
        
        # Show current counts
        print("\n📊 Current data counts:")
        counts_before = {}
        for table in tables:
            table_name = table['table_name']
            count = await conn.fetchval(f'SELECT COUNT(*) FROM "{table_name}"')
            counts_before[table_name] = count
            print(f"  📋 {table_name}: {count} records")
        
        # Confirm again if there's data
        total_records = sum(counts_before.values())
        if total_records > 0:
            print(f"\n📊 Total records to delete: {total_records}")
            final_confirm = input("\nType 'YES' to proceed with deletion: ")
            if final_confirm != "YES":
                print("❌ Operation cancelled.")
                await conn.close()
                return False
        
        # Disable triggers temporarily to avoid foreign key issues
        print("\n🗑️  Clearing data from all tables...")
        await conn.execute('SET session_replication_role = replica;')
        
        # Clear each table
        for table in tables:
            table_name = table['table_name']
            try:
                # TRUNCATE is faster than DELETE and resets sequences
                await conn.execute(f'TRUNCATE TABLE "{table_name}" CASCADE')
                print(f"  ✅ Cleared: {table_name}")
            except Exception as e:
                # If TRUNCATE fails, try DELETE
                try:
                    await conn.execute(f'DELETE FROM "{table_name}"')
                    print(f"  ✅ Cleared: {table_name} (using DELETE)")
                except Exception as e2:
                    print(f"  ❌ Failed to clear {table_name}: {e2}")
        
        # Re-enable triggers
        await conn.execute('SET session_replication_role = DEFAULT;')
        
        # Reset all sequences (auto-increment counters)
        print("\n🔄 Resetting sequences...")
        sequences = await conn.fetch("""
            SELECT sequence_name 
            FROM information_schema.sequences 
            WHERE sequence_schema = 'public'
        """)
        
        for seq in sequences:
            try:
                await conn.execute(f'ALTER SEQUENCE "{seq["sequence_name"]}" RESTART WITH 1')
                print(f"  ✅ Reset: {seq['sequence_name']}")
            except Exception as e:
                print(f"  ⚠️  Could not reset {seq['sequence_name']}: {e}")
        
        # Verify clearing
        print("\n✅ Verifying clearing...")
        counts_after = {}
        all_cleared = True
        for table in tables:
            table_name = table['table_name']
            count = await conn.fetchval(f'SELECT COUNT(*) FROM "{table_name}"')
            counts_after[table_name] = count
            if count > 0:
                all_cleared = False
                print(f"  ⚠️  {table_name}: {count} records remaining")
            else:
                print(f"  ✅ {table_name}: 0 records")
        
        await conn.close()
        
        # Summary
        print("\n" + "=" * 60)
        if all_cleared:
            print("✅ SUCCESS: All data has been cleared from the database!")
            print(f"📊 Total records removed: {total_records}")
        else:
            print("⚠️  PARTIAL SUCCESS: Some data could not be cleared")
        
        print("=" * 60)
        print("\n💡 Next steps:")
        print("1. Restart your bot: python main.py")
        print("2. The bot will work with fresh empty tables")
        print("3. Users will need to register again")
        print("4. Admins will need to add new modules and resources")
        
        return all_cleared
        
    except Exception as e:
        print(f"\n❌ Error clearing data: {e}")
        return False

async def main():
    success = await clear_all_data()
    if not success:
        print("\n💡 Troubleshooting tips:")
        print("1. Make sure PostgreSQL is running: sudo systemctl start postgresql")
        print("2. Check your .env file has correct database credentials")
        print("3. Verify you have permission to modify the database")
        print("4. Try running with: sudo -u postgres python clear_data.py")

if __name__ == "__main__":
    asyncio.run(main())