#!/usr/bin/env python3
"""
Initialize the resource_bot database with required tables
Run this script once to set up the database schema for the bot
"""

import os
import pymysql
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_connection():
    """Get connection to MySQL database"""
    return pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER', 'bot_admin'),
        password=os.getenv('DB_PASSWORD', 'SecurePass123'),
        database=os.getenv('DB_NAME', 'resource_bot'),
        charset='utf8mb4',
        autocommit=True
    )

def init_database():
    """Initialize database tables"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        logger.info(f"Connecting to database: {os.getenv('DB_NAME', 'resource_bot')}")
        
        # Create users table
        logger.info("Creating users table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                full_name VARCHAR(255) NOT NULL,
                father_name VARCHAR(120) DEFAULT '',
                phone_number VARCHAR(32) DEFAULT '',
                username VARCHAR(150) DEFAULT '',
                `status` VARCHAR(32) DEFAULT 'pending',
                registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                enrolled_at DATETIME NULL,
                INDEX idx_status (`status`),
                INDEX idx_registered_at (registered_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        ''')
        
        # Create modules table
        logger.info("Creating modules table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS modules (
                id INT AUTO_INCREMENT PRIMARY KEY,
                module_name VARCHAR(255) UNIQUE NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by BIGINT NULL,
                INDEX idx_module_name (module_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        ''')
        
        # Create resources table
        logger.info("Creating resources table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resources (
                id INT AUTO_INCREMENT PRIMARY KEY,
                module_id INT NOT NULL,
                file_id TEXT NOT NULL,
                file_name VARCHAR(255) DEFAULT '',
                file_type VARCHAR(50) DEFAULT '',
                uploaded_by BIGINT NULL,
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE,
                INDEX idx_module_id (module_id),
                INDEX idx_uploaded_at (uploaded_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        ''')
        
        # Create logs table
        logger.info("Creating logs table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NULL,
                action VARCHAR(255) NOT NULL,
                details TEXT DEFAULT '',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_timestamp (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        ''')
        
        # Create system_settings table
        logger.info("Creating system_settings table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                `key` VARCHAR(120) UNIQUE NOT NULL,
                value_json JSON DEFAULT '{}',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_key (`key`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        ''')
        
        # Create students_student table
        logger.info("Creating students_student table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students_student (
                id VARCHAR(32) PRIMARY KEY,
                name VARCHAR(120) NOT NULL,
                phone VARCHAR(32) DEFAULT '',
                father_name VARCHAR(120) DEFAULT '',
                telegram_user_id BIGINT UNIQUE NULL,
                telegram_username VARCHAR(150) DEFAULT '',
                batch_id VARCHAR(32) NULL,
                payment_status VARCHAR(20) DEFAULT 'not_paid',
                tuition_fee INT UNSIGNED DEFAULT 12000,
                amount_paid INT UNSIGNED DEFAULT 0,
                graduation_status VARCHAR(20) DEFAULT 'not_graduated',
                graduated BOOLEAN DEFAULT FALSE,
                meta JSON DEFAULT '{}',
                grade SMALLINT UNSIGNED NULL,
                employment_status VARCHAR(20) DEFAULT 'no',
                registration_type VARCHAR(20) DEFAULT 'online',
                `status` VARCHAR(20) DEFAULT 'pending',
                rejected_at DATETIME NULL,
                registration_date DATE DEFAULT CURDATE(),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_batch (batch_id),
                INDEX idx_payment_status (payment_status),
                INDEX idx_employment_status (employment_status),
                INDEX idx_telegram_user_id (telegram_user_id),
                INDEX idx_phone (phone)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        ''')
        
        # Create surveys_survey table
        logger.info("Creating surveys_survey table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS surveys_survey (
                id VARCHAR(50) PRIMARY KEY,
                question TEXT NOT NULL,
                survey_type VARCHAR(50) DEFAULT 'yes_no',
                last_sent DATE DEFAULT CURDATE(),
                response_yes INT DEFAULT 0,
                response_no INT DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_survey_type (survey_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        ''')
        
        # Create students_employmentcheckin table
        logger.info("Creating students_employmentcheckin table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students_employmentcheckin (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(32) NOT NULL,
                survey_id VARCHAR(50) NOT NULL,
                is_employed BOOLEAN DEFAULT FALSE,
                checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students_student(id) ON DELETE CASCADE,
                INDEX idx_student_id (student_id),
                INDEX idx_survey_id (survey_id),
                INDEX idx_checked_at (checked_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        ''')
        
        # Insert default course fees if not exists
        logger.info("Inserting default course fees...")
        cursor.execute('''
            INSERT IGNORE INTO system_settings (`key`, value_json)
            VALUES ('course_fees', JSON_OBJECT('computer', 12000, 'office', 12000));
        ''')
        
        conn.commit()
        logger.info("✅ Database initialized successfully!")
        logger.info("Tables created:")
        logger.info("  - users")
        logger.info("  - modules")
        logger.info("  - resources")
        logger.info("  - logs")
        logger.info("  - system_settings")
        logger.info("  - students_student")
        logger.info("  - surveys_survey")
        logger.info("  - students_employmentcheckin")
        
        cursor.close()
        conn.close()
        
    except pymysql.Error as e:
        logger.error(f"❌ Database error: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        raise

if __name__ == '__main__':
    init_database()
