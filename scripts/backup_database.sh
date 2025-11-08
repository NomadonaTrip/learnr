#!/bin/bash
#
# Database Backup Script for Timezone Migration
#
# Creates three types of backups before migration:
# 1. Full backup (schema + data)
# 2. Schema-only backup
# 3. Data-only backup
#
# Usage: ./scripts/backup_database.sh
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="backups/timezone_migration_$(date +%Y%m%d_%H%M%S)"
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/learnr_db}"

# Extract connection details from DATABASE_URL
# Format: postgresql://user:password@host:port/database
DB_USER=$(echo $DATABASE_URL | sed -E 's|.*://([^:]+):.*|\1|')
DB_PASSWORD=$(echo $DATABASE_URL | sed -E 's|.*://[^:]+:([^@]+)@.*|\1|')
DB_HOST=$(echo $DATABASE_URL | sed -E 's|.*@([^:]+):.*|\1|')
DB_PORT=$(echo $DATABASE_URL | sed -E 's|.*:([0-9]+)/.*|\1|')
DB_NAME=$(echo $DATABASE_URL | sed -E 's|.*/(.*)$|\1|')

echo -e "${GREEN}=== Database Backup Script ===${NC}"
echo ""
echo "Database: $DB_NAME"
echo "Host: $DB_HOST:$DB_PORT"
echo "Backup Directory: $BACKUP_DIR"
echo ""

# Create backup directory
echo -e "${YELLOW}Creating backup directory...${NC}"
mkdir -p "$BACKUP_DIR"

# Export password for pg_dump
export PGPASSWORD="$DB_PASSWORD"

# 1. Full Backup (schema + data)
echo -e "${YELLOW}Creating full backup (schema + data)...${NC}"
pg_dump \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -F c \
  -b \
  -v \
  -f "$BACKUP_DIR/full_backup.dump"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Full backup created successfully${NC}"
else
    echo -e "${RED}✗ Full backup failed${NC}"
    exit 1
fi

# 2. Schema-Only Backup
echo -e "${YELLOW}Creating schema-only backup...${NC}"
pg_dump \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  --schema-only \
  -f "$BACKUP_DIR/schema_backup.sql"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Schema-only backup created successfully${NC}"
else
    echo -e "${RED}✗ Schema-only backup failed${NC}"
    exit 1
fi

# 3. Data-Only Backup
echo -e "${YELLOW}Creating data-only backup...${NC}"
pg_dump \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  --data-only \
  -F c \
  -b \
  -v \
  -f "$BACKUP_DIR/data_backup.dump"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Data-only backup created successfully${NC}"
else
    echo -e "${RED}✗ Data-only backup failed${NC}"
    exit 1
fi

# 4. Backup specific tables with DateTime columns (for targeted testing)
echo -e "${YELLOW}Creating backup of critical tables...${NC}"
pg_dump \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -t spaced_repetition_cards \
  -t sessions \
  -t question_attempts \
  -f "$BACKUP_DIR/critical_tables_backup.sql"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Critical tables backup created successfully${NC}"
else
    echo -e "${RED}✗ Critical tables backup failed${NC}"
    exit 1
fi

# 5. Create metadata file
echo -e "${YELLOW}Creating backup metadata...${NC}"
cat > "$BACKUP_DIR/backup_metadata.txt" << EOF
Backup Metadata
===============

Timestamp: $(date +"%Y-%m-%d %H:%M:%S")
Database: $DB_NAME
Host: $DB_HOST:$DB_PORT
Purpose: Timezone migration from TIMESTAMP to TIMESTAMPTZ

Backup Files:
- full_backup.dump: Complete database (schema + data) in custom format
- schema_backup.sql: Schema-only in SQL format
- data_backup.dump: Data-only in custom format
- critical_tables_backup.sql: Spaced repetition and session tables (SQL format)

Database Statistics:
EOF

# Add table counts
echo "" >> "$BACKUP_DIR/backup_metadata.txt"
echo "Table Row Counts:" >> "$BACKUP_DIR/backup_metadata.txt"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
SELECT
    schemaname || '.' || tablename as table_name,
    n_live_tup as row_count
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;
" >> "$BACKUP_DIR/backup_metadata.txt"

# Calculate backup sizes
echo "" >> "$BACKUP_DIR/backup_metadata.txt"
echo "Backup Sizes:" >> "$BACKUP_DIR/backup_metadata.txt"
du -h "$BACKUP_DIR"/* | sed 's|^|  |' >> "$BACKUP_DIR/backup_metadata.txt"

echo -e "${GREEN}✓ Backup metadata created${NC}"

# Verify backups
echo ""
echo -e "${YELLOW}Verifying backups...${NC}"

# Check that all backup files exist and are not empty
REQUIRED_FILES=("full_backup.dump" "schema_backup.sql" "data_backup.dump" "critical_tables_backup.sql" "backup_metadata.txt")
ALL_OK=true

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$BACKUP_DIR/$file" ]; then
        echo -e "${RED}✗ Missing file: $file${NC}"
        ALL_OK=false
    elif [ ! -s "$BACKUP_DIR/$file" ]; then
        echo -e "${RED}✗ Empty file: $file${NC}"
        ALL_OK=false
    else
        SIZE=$(du -h "$BACKUP_DIR/$file" | cut -f1)
        echo -e "${GREEN}✓ $file ($SIZE)${NC}"
    fi
done

# Cleanup
unset PGPASSWORD

echo ""
if [ "$ALL_OK" = true ]; then
    echo -e "${GREEN}=== Backup completed successfully ===${NC}"
    echo ""
    echo "Backup location: $BACKUP_DIR"
    echo ""
    echo "To restore from backup:"
    echo "  Full restore:   pg_restore -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c $BACKUP_DIR/full_backup.dump"
    echo "  Schema only:    psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f $BACKUP_DIR/schema_backup.sql"
    echo ""
    echo "Next step: Run Alembic migration (Phase 3)"
    exit 0
else
    echo -e "${RED}=== Backup completed with errors ===${NC}"
    echo "Please review errors above"
    exit 1
fi
