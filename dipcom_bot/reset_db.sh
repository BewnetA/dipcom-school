#!/bin/bash

# Database configuration
DB_NAME="resource_bot"
DB_USER="bot_admin"
DB_PASS="SecurePass123"

echo "⚠️  WARNING: This will delete ALL data from the $DB_NAME database!"
echo "This action cannot be undone!"
read -p "Are you sure you want to continue? (yes/no): " confirmation

if [ "$confirmation" != "yes" ]; then
    echo "Operation cancelled."
    exit 0
fi

echo "🗑️  Resetting database..."

# Drop and recreate the database
sudo -u postgres psql <<EOF
-- Terminate all connections to the database
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = '$DB_NAME';

-- Drop the database if it exists
DROP DATABASE IF EXISTS $DB_NAME;

-- Recreate the database
CREATE DATABASE $DB_NAME;

-- Reconnect to the new database
\c $DB_NAME

-- Grant all privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
GRANT ALL ON SCHEMA public TO $DB_USER;
GRANT CREATE ON SCHEMA public TO $DB_USER;

-- Set ownership
ALTER DATABASE $DB_NAME OWNER TO $DB_USER;

EOF

if [ $? -eq 0 ]; then
    echo "✅ Database has been completely reset!"
    echo "📝 The bot will recreate all tables automatically when started."
else
    echo "❌ Failed to reset database. Please check your PostgreSQL configuration."
fi