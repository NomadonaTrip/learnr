#!/bin/bash
#
# Database Restore Script for Timezone Migration Rollback
#
# Restores database from backup created by backup_database.sh
#
# Usage: ./scripts/restore_database.sh <backup_directory>
# Example: ./scripts/restore_database.sh backups/timezone_migration_20251108_143022
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check arguments
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: No backup directory specified${NC}"
    echo ""
    echo "Usage: $0 <backup_directory>"
    echo ""
    echo "Available backups:"
    ls -d backups/timezone_migration_* 2>/dev/null | sed 's/^/  /' || echo "  No backups found"
    exit 1
fi

BACKUP_DIR="$1"

# Verify backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${RED}Error: Backup directory not found: $BACKUP_DIR${NC}"
    exit 1
fi

# Configuration
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/learnr_db}"

# Extract connection details
DB_USER=$(echo $DATABASE_URL | sed -E 's|.*://([^:]+):.*|\1|')
DB_PASSWORD=$(echo $DATABASE_URL | sed -E 's|.*://[^:]+:([^@]+)@.*|\1|')
DB_HOST=$(echo $DATABASE_URL | sed -E 's|.*@([^:]+):.*|\1|')
DB_PORT=$(echo $DATABASE_URL | sed -E 's|.*:([0-9]+)/.*|\1|')
DB_NAME=$(echo $DATABASE_URL | sed -E 's|.*/(.*)$|\1|')

echo -e "${RED}=== WARNING: Database Restore ===${NC}"
echo ""
echo "This will REPLACE the current database with backup data!"
echo ""
echo "Database: $DB_NAME"
echo "Host: $DB_HOST:$DB_PORT"
echo "Backup: $BACKUP_DIR"
echo ""

# Show backup metadata if available
if [ -f "$BACKUP_DIR/backup_metadata.txt" ]; then
    echo -e "${YELLOW}Backup Information:${NC}"
    head -10 "$BACKUP_DIR/backup_metadata.txt" | sed 's/^/  /'
    echo ""
fi

# Confirm restore
read -p "Are you sure you want to proceed? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled"
    exit 0
fi

# Export password
export PGPASSWORD="$DB_PASSWORD"

echo ""
echo -e "${YELLOW}Starting restore process...${NC}"

# 1. Drop all connections to the database
echo -e "${YELLOW}Terminating active connections...${NC}"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = '$DB_NAME'
  AND pid <> pg_backend_pid();
" > /dev/null 2>&1 || true

# 2. Restore from full backup
if [ -f "$BACKUP_DIR/full_backup.dump" ]; then
    echo -e "${YELLOW}Restoring full backup (schema + data)...${NC}"

    # Drop and recreate database
    echo -e "${YELLOW}Recreating database...${NC}"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;"

    # Enable pgvector extension
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;"

    # Restore backup
    pg_restore \
      -h "$DB_HOST" \
      -p "$DB_PORT" \
      -U "$DB_USER" \
      -d "$DB_NAME" \
      -v \
      --no-owner \
      --no-acl \
      "$BACKUP_DIR/full_backup.dump"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Database restored successfully from full backup${NC}"
    else
        echo -e "${RED}✗ Restore failed${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Full backup file not found: $BACKUP_DIR/full_backup.dump${NC}"
    exit 1
fi

# 3. Verify restore
echo ""
echo -e "${YELLOW}Verifying restored database...${NC}"

# Check table counts
echo "Table counts:"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
SELECT
    tablename,
    n_live_tup as row_count
FROM pg_stat_user_tables
WHERE n_live_tup > 0
ORDER BY n_live_tup DESC
LIMIT 10;
" | sed 's/^/  /'

# Check for DateTime columns (should be TIMESTAMP, not TIMESTAMPTZ if this is pre-migration backup)
echo ""
echo "DateTime column types (sample):"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
SELECT
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE column_name IN ('created_at', 'next_review_at', 'completed_at')
LIMIT 5;
" | sed 's/^/  /'

# Cleanup
unset PGPASSWORD

echo ""
echo -e "${GREEN}=== Restore completed successfully ===${NC}"
echo ""
echo "Database has been restored to the state captured in:"
echo "  $BACKUP_DIR"
echo ""
echo "Next steps:"
echo "  - Verify data integrity"
echo "  - Re-run Alembic migration if needed"
echo "  - Run tests to confirm restore"
