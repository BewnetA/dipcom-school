import sqlite3
import aiosqlite
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def row_to_dict(row):
    """Convert a sqlite3.Row to a dictionary"""
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}

class Database:
    def __init__(self, db_name: str = None):
        if db_name is None:
            # Use the same DB as Django backend (now in same directory)
            db_name = os.path.join(os.path.dirname(__file__), '..', 'db.sqlite3')
        self.db_name = db_name
        self.connection = None
    
    async def init_db(self):
        """Initialize database connection and tables"""
        try:
            self.connection = await aiosqlite.connect(self.db_name)
            # Enable foreign keys
            await self.connection.execute("PRAGMA foreign_keys = ON")
            # Set row factory to return dict-like rows
            self.connection.row_factory = aiosqlite.Row
            await self.init_database()
            logger.info("Database initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def close_db(self):
        """Close database connection"""
        if self.connection:
            await self.connection.close()
            logger.info("Database connection closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Context manager for database connections"""
        try:
            yield self.connection
            await self.connection.commit()
        except Exception as e:
            await self.connection.rollback()
            logger.error(f"Database error: {e}")
            raise
    
    async def init_database(self):
        """Initialize database tables (if not already created by Django)"""
        async with self.get_connection() as conn:
            # Note: Django will create these tables, but we ensure they exist
            # Users table (common_botuser)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS common_botuser (
                    user_id INTEGER PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    father_name TEXT NOT NULL,
                    phone_number TEXT,
                    username TEXT,
                    status TEXT DEFAULT 'pending',
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    enrolled_at TIMESTAMP
                )
            ''')
            
            # Modules table (common_botmodule)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS common_botmodule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module_name TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER
                )
            ''')
            
            # Resources table (common_botresource)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS common_botresource (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module_id INTEGER,
                    file_id TEXT NOT NULL,
                    file_name TEXT,
                    file_type TEXT,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    uploaded_by INTEGER,
                    FOREIGN KEY (module_id) REFERENCES common_botmodule (id) ON DELETE CASCADE
                )
            ''')
            
            # Logs table (common_botlog)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS common_botlog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_common_botuser_status ON common_botuser(status)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_common_botresource_module ON common_botresource(module_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_common_botlog_user ON common_botlog(user_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_common_botlog_timestamp ON common_botlog(timestamp)')
            
            logger.info("Database tables initialized successfully")
    
    # User methods
    async def register_user(self, user_id: int, full_name: str, father_name: str, 
                           phone_number: str = None, username: str = None, status: str = 'pending') -> bool:
        """Register a new user"""
        try:
            async with self.get_connection() as conn:
                await conn.execute('''
                    INSERT OR REPLACE INTO common_botuser (user_id, full_name, father_name, phone_number, username, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, full_name, father_name, phone_number, username, status))
                return True
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return False
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute('SELECT * FROM common_botuser WHERE user_id = ?', (user_id,))
                row = await cursor.fetchone()
                if row:
                    # Convert row to dictionary properly
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    async def update_user_status(self, user_id: int, status: str) -> bool:
        """Update user enrollment status"""
        try:
            async with self.get_connection() as conn:
                await conn.execute('''
                    UPDATE common_botuser 
                    SET status = ?, enrolled_at = CASE WHEN ? = 'enrolled' THEN CURRENT_TIMESTAMP ELSE enrolled_at END
                    WHERE user_id = ?
                ''', (status, status, user_id))
                return True
        except Exception as e:
            logger.error(f"Error updating user status: {e}")
            return False
    
    async def get_all_users(self, status: str = None) -> List[Dict]:
        """Get all users, optionally filtered by status"""
        try:
            async with self.get_connection() as conn:
                if status:
                    cursor = await conn.execute('SELECT * FROM common_botuser WHERE status = ? ORDER BY registered_at DESC', (status,))
                else:
                    cursor = await conn.execute('SELECT * FROM common_botuser ORDER BY registered_at DESC')
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []
    
    # Module methods
    async def add_module(self, module_name: str, created_by: int) -> bool:
        """Add a new module"""
        try:
            async with self.get_connection() as conn:
                await conn.execute('INSERT INTO common_botmodule (module_name, created_by) VALUES (?, ?)', 
                                 (module_name, created_by))
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"Module '{module_name}' already exists")
            return False
        except Exception as e:
            logger.error(f"Error adding module: {e}")
            return False
    
    async def get_modules(self) -> List[Dict]:
        """Get all modules"""
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute('SELECT * FROM common_botmodule ORDER BY module_name')
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting modules: {e}")
            return []
    
    async def get_module(self, module_id: int) -> Optional[Dict]:
        """Get module by ID"""
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute('SELECT * FROM common_botmodule WHERE id = ?', (module_id,))
                row = await cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting module: {e}")
            return None
    
    async def get_module_by_name(self, module_name: str) -> Optional[Dict]:
        """Get module by name"""
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute('SELECT * FROM common_botmodule WHERE module_name = ?', (module_name,))
                row = await cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting module by name: {e}")
            return None
    
    async def delete_module(self, module_id: int) -> bool:
        """Delete a module and its resources"""
        try:
            async with self.get_connection() as conn:
                await conn.execute('DELETE FROM common_botmodule WHERE id = ?', (module_id,))
                return True
        except Exception as e:
            logger.error(f"Error deleting module: {e}")
            return False
    
    # Resource methods
    async def add_resource(self, module_id: int, file_id: str, file_name: str, 
                          file_type: str, uploaded_by: int) -> bool:
        """Add a resource to a module"""
        try:
            async with self.get_connection() as conn:
                await conn.execute('''
                    INSERT INTO common_botresource (module_id, file_id, file_name, file_type, uploaded_by)
                    VALUES (?, ?, ?, ?, ?)
                ''', (module_id, file_id, file_name, file_type, uploaded_by))
                return True
        except Exception as e:
            logger.error(f"Error adding resource: {e}")
            return False
    
    async def get_module_resources(self, module_id: int) -> List[Dict]:
        """Get all resources for a module"""
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute('SELECT * FROM common_botresource WHERE module_id = ? ORDER BY uploaded_at DESC', (module_id,))
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting module resources: {e}")
            return []
    
    async def get_resource(self, resource_id: int) -> Optional[Dict]:
        """Get a single resource by ID"""
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute('SELECT * FROM common_botresource WHERE id = ?', (resource_id,))
                row = await cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting resource: {e}")
            return None
    
    async def delete_resource(self, resource_id: int) -> bool:
        """Delete a resource"""
        try:
            async with self.get_connection() as conn:
                await conn.execute('DELETE FROM common_botresource WHERE id = ?', (resource_id,))
                return True
        except Exception as e:
            logger.error(f"Error deleting resource: {e}")
            return False
    
    # Logging
    async def log_action(self, user_id: int, action: str, details: str = None):
        """Log user actions"""
        try:
            async with self.get_connection() as conn:
                await conn.execute('INSERT INTO common_botlog (user_id, action, details) VALUES (?, ?, ?)',
                                 (user_id, action, details))
        except Exception as e:
            logger.error(f"Error logging action: {e}")

# Initialize database instance
db = Database()
