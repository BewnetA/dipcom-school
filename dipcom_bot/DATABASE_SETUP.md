# Database Fix: Missing Tables Issue

## Problem
When registering a new user from the bot, the following errors occurred:
```
ERROR:handlers.user:Error querying course fees: (1146, "Table 'resource_bot.system_settings' doesn't exist")
ERROR:handlers.user:Error inserting student: (1146, "Table 'resource_bot.students_student' doesn't exist")
```

## Root Cause
The bot was configured to use the `resource_bot` MySQL database, but the required tables had not been created in that database. The bot code was trying to access:
- `system_settings` - to retrieve course fee configurations
- `students_student` - to store and retrieve student registration data

## Solution
Created two initialization scripts to set up the database:

### 1. `init_db.py` - Database Initialization
This script creates the required tables with proper structure:
- **system_settings**: Stores configuration data (e.g., course fees)
- **students_student**: Stores student information linked to Telegram users

Run this script once after setting up the bot:
```bash
python3 init_db.py
```

### 2. `verify_db.py` - Database Verification
Use this script to verify the database is properly set up:
```bash
python3 verify_db.py
```

## Tables Created

### system_settings
```sql
CREATE TABLE system_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    `key` VARCHAR(120) UNIQUE NOT NULL,
    value_json JSON DEFAULT '{}',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_key (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### students_student
```sql
CREATE TABLE students_student (
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
```

## Default Data
The `system_settings` table is pre-populated with default course fees:
```json
{
  "computer": 12000,
  "office": 12000
}
```

## Next Steps
1. Run `python3 init_db.py` to initialize the database (if not already done)
2. Verify with `python3 verify_db.py`
3. The bot should now work without database-related errors when registering new users

## Database Configuration
The database connection details are stored in `/dipcom_bot/.env`:
```
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=resource_bot
DB_USER=bot_admin
DB_PASSWORD=SecurePass123
```
