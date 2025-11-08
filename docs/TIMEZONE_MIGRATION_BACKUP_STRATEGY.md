# Timezone Migration - Backup Strategy

**Purpose:** Ensure safe rollback capability during timezone migration from `TIMESTAMP` to `TIMESTAMPTZ`
**Created:** 2025-11-08
**Phase:** 2 of 7

---

## Overview

Before executing the timezone migration (converting 70 DateTime columns from TIMESTAMP to TIMESTAMPTZ), we must create comprehensive backups to enable quick rollback if issues arise.

**Risk Level:** Medium - Schema change affecting 70 columns across 23 tables
**Rollback Time:** < 5 minutes with proper backups
**Data Loss Risk:** Zero (if backups are verified)

---

## Backup Types

### 1. Full Backup (Schema + Data)
**File:** `full_backup.dump`
**Format:** PostgreSQL custom format (`.dump`)
**Purpose:** Complete database snapshot for full restore
**Size:** ~Depends on data volume (typically 10-100 MB for development)

**Advantages:**
- Single file contains everything
- Fastest restore option
- Includes all database objects (tables, indexes, sequences, triggers)

**Restore Command:**
```bash
pg_restore -h localhost -p 5432 -U postgres -d learnr_db -c full_backup.dump
```

---

### 2. Schema-Only Backup
**File:** `schema_backup.sql`
**Format:** Plain SQL
**Purpose:** Table definitions, indexes, constraints
**Size:** ~500 KB

**Advantages:**
- Human-readable SQL
- Easy to inspect table definitions
- Useful for creating test databases

**Restore Command:**
```bash
psql -h localhost -p 5432 -U postgres -d learnr_db -f schema_backup.sql
```

---

### 3. Data-Only Backup
**File:** `data_backup.dump`
**Format:** PostgreSQL custom format
**Purpose:** All table data without schema
**Size:** ~Depends on data volume

**Advantages:**
- Restore data into existing schema
- Useful if schema migration partially succeeds

**Restore Command:**
```bash
pg_restore -h localhost -p 5432 -U postgres -d learnr_db --data-only data_backup.dump
```

---

### 4. Critical Tables Backup
**File:** `critical_tables_backup.sql`
**Format:** Plain SQL
**Purpose:** Backup of tables most affected by timezone migration
**Tables Included:**
- `spaced_repetition_cards` (PRIMARY CULPRIT - next_review_at, last_reviewed_at)
- `sessions` (started_at, completed_at)
- `question_attempts` (attempted_at)

**Advantages:**
- Quick verification of critical data
- Targeted restore if only specific tables affected

---

## Backup Execution

### Prerequisites
- PostgreSQL client tools installed (`pg_dump`, `pg_restore`, `psql`)
- `DATABASE_URL` environment variable set
- Sufficient disk space (estimate 2-3x current database size)

### Automated Backup Script

```bash
# Run backup script
./scripts/backup_database.sh

# Expected output:
# === Database Backup Script ===
#
# Database: learnr_db
# Host: localhost:5432
# Backup Directory: backups/timezone_migration_20251108_143022
#
# Creating backup directory...
# Creating full backup (schema + data)...
# ✓ Full backup created successfully
# Creating schema-only backup...
# ✓ Schema-only backup created successfully
# Creating data-only backup...
# ✓ Data-only backup created successfully
# Creating backup of critical tables...
# ✓ Critical tables backup created successfully
# Creating backup metadata...
# ✓ Backup metadata created
#
# Verifying backups...
# ✓ full_backup.dump (45M)
# ✓ schema_backup.sql (512K)
# ✓ data_backup.dump (42M)
# ✓ critical_tables_backup.sql (8.2M)
# ✓ backup_metadata.txt (4.0K)
#
# === Backup completed successfully ===
```

### Manual Backup (if script fails)

```bash
# Set environment variables
export PGPASSWORD="your_password"
DB_NAME="learnr_db"
DB_HOST="localhost"
DB_PORT="5432"
DB_USER="postgres"
BACKUP_DIR="backups/timezone_migration_$(date +%Y%m%d_%H%M%S)"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Full backup
pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -F c -b -v -f "$BACKUP_DIR/full_backup.dump"

# Schema-only backup
pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  --schema-only -f "$BACKUP_DIR/schema_backup.sql"

# Data-only backup
pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  --data-only -F c -b -v -f "$BACKUP_DIR/data_backup.dump"

# Cleanup
unset PGPASSWORD
```

---

## Backup Verification

### 1. File Existence Check
```bash
ls -lh backups/timezone_migration_20251108_143022/

# Expected output:
# -rw-r--r-- 1 user user  45M Nov  8 14:30 full_backup.dump
# -rw-r--r-- 1 user user 512K Nov  8 14:30 schema_backup.sql
# -rw-r--r-- 1 user user  42M Nov  8 14:30 data_backup.dump
# -rw-r--r-- 1 user user 8.2M Nov  8 14:30 critical_tables_backup.sql
# -rw-r--r-- 1 user user 4.0K Nov  8 14:30 backup_metadata.txt
```

### 2. Backup Integrity Check
```bash
# Test full backup can be read
pg_restore --list backups/timezone_migration_20251108_143022/full_backup.dump | head -20

# Should show table of contents without errors
```

### 3. Test Restore to Temporary Database
```bash
# Create test database
psql -h localhost -U postgres -c "CREATE DATABASE learnr_test_restore;"

# Restore backup
pg_restore -h localhost -U postgres -d learnr_test_restore -v \
  backups/timezone_migration_20251108_143022/full_backup.dump

# Verify table count
psql -h localhost -U postgres -d learnr_test_restore -c "\dt"

# Cleanup
psql -h localhost -U postgres -c "DROP DATABASE learnr_test_restore;"
```

---

## Restore Procedures

### Full Database Restore (Rollback)

**When to use:** Migration failed catastrophically, database is corrupted

```bash
# Use automated restore script
./scripts/restore_database.sh backups/timezone_migration_20251108_143022

# Expected time: 2-5 minutes
```

**Manual Restore:**
```bash
export PGPASSWORD="your_password"

# Terminate active connections
psql -h localhost -U postgres -d postgres -c "
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE datname = 'learnr_db' AND pid <> pg_backend_pid();
"

# Drop and recreate database
psql -h localhost -U postgres -c "DROP DATABASE learnr_db;"
psql -h localhost -U postgres -c "CREATE DATABASE learnr_db;"

# Enable pgvector extension
psql -h localhost -U postgres -d learnr_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Restore from backup
pg_restore -h localhost -U postgres -d learnr_db -v \
  backups/timezone_migration_20251108_143022/full_backup.dump

unset PGPASSWORD
```

---

### Partial Restore (Critical Tables Only)

**When to use:** Migration succeeded mostly, but specific tables have issues

```bash
# Restore only spaced_repetition_cards table
psql -h localhost -U postgres -d learnr_db -c "TRUNCATE spaced_repetition_cards CASCADE;"

pg_restore -h localhost -U postgres -d learnr_db -v \
  -t spaced_repetition_cards \
  backups/timezone_migration_20251108_143022/full_backup.dump
```

---

### Alembic Migration Rollback (Preferred)

**When to use:** Migration applied but needs to be reverted cleanly

```bash
# This is Phase 6 - detailed in TIMEZONE_MIGRATION_ROLLBACK_PROCEDURES.md

# Quick rollback one migration
alembic downgrade -1

# Verify rollback
alembic current
psql -h localhost -U postgres -d learnr_db -c "
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'spaced_repetition_cards'
  AND column_name = 'next_review_at';
"
# Should show: next_review_at | timestamp without time zone
```

---

## Backup Storage Best Practices

### Local Development
- **Location:** `backups/timezone_migration_YYYYMMDD_HHMMSS/`
- **Retention:** Keep until migration confirmed successful + 7 days
- **Size Limit:** No limit for development

### Staging Environment
- **Location:** Cloud storage (AWS S3, Google Cloud Storage, Azure Blob)
- **Retention:** 30 days minimum
- **Encryption:** Required (encrypt backups at rest)

### Production Environment
- **Location:** Multi-region cloud storage with versioning
- **Retention:** 90 days minimum
- **Encryption:** Required (AES-256)
- **Access Control:** Restricted to database administrators only
- **Testing:** Verify restore capability monthly

---

## Disk Space Requirements

### Estimate Backup Size
```bash
# Check current database size
psql -h localhost -U postgres -d learnr_db -c "
SELECT pg_size_pretty(pg_database_size('learnr_db')) as database_size;
"

# Check table sizes
psql -h localhost -U postgres -d learnr_db -c "
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
"
```

### Minimum Free Space
- **Development:** Current DB size × 3
- **Production:** Current DB size × 5

---

## Troubleshooting

### Issue: "pg_dump: command not found"
**Solution:** Install PostgreSQL client tools
```bash
# Ubuntu/Debian
sudo apt-get install postgresql-client

# macOS
brew install postgresql

# Verify
pg_dump --version
```

### Issue: "pg_dump: error: connection to server failed"
**Solution:** Check DATABASE_URL and network connectivity
```bash
# Test connection
psql -h localhost -p 5432 -U postgres -d learnr_db -c "SELECT version();"

# Check DATABASE_URL format
echo $DATABASE_URL
# Expected: postgresql://user:password@host:port/database
```

### Issue: "Out of disk space"
**Solution:** Free up space or use compressed backups
```bash
# Check available space
df -h

# Use compressed backups (custom format is already compressed)
# If using plain SQL, compress manually:
pg_dump -h localhost -U postgres -d learnr_db --schema-only | gzip > schema_backup.sql.gz
```

### Issue: "Permission denied"
**Solution:** Ensure user has sufficient privileges
```bash
# Grant necessary permissions
psql -h localhost -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE learnr_db TO your_user;"
```

---

## Backup Metadata

Each backup directory includes `backup_metadata.txt` with:
- Timestamp of backup
- Database name, host, port
- Table row counts (snapshot at backup time)
- Backup file sizes
- Purpose of backup

**Example:**
```
Backup Metadata
===============

Timestamp: 2025-11-08 14:30:22
Database: learnr_db
Host: localhost:5432
Purpose: Timezone migration from TIMESTAMP to TIMESTAMPTZ

Backup Files:
- full_backup.dump: Complete database (schema + data) in custom format
- schema_backup.sql: Schema-only in SQL format
- data_backup.dump: Data-only in custom format
- critical_tables_backup.sql: Spaced repetition and session tables (SQL format)

Table Row Counts:
  users              | 150
  sessions           | 1250
  question_attempts  | 8500
  spaced_repetition_cards | 3200
  ...

Backup Sizes:
  45M    full_backup.dump
  512K   schema_backup.sql
  42M    data_backup.dump
  8.2M   critical_tables_backup.sql
  4.0K   backup_metadata.txt
```

---

## Checklist

Before proceeding to Phase 3 (Alembic Migration), verify:

- [ ] Backup script executed successfully (`./scripts/backup_database.sh`)
- [ ] All 5 backup files created (full, schema, data, critical, metadata)
- [ ] Backup files are non-zero size
- [ ] Backup integrity verified (`pg_restore --list` works)
- [ ] Test restore to temporary database succeeded
- [ ] Backup metadata file contains expected information
- [ ] Sufficient disk space available for migration
- [ ] Restore script tested (`./scripts/restore_database.sh`)

---

## Next Steps

Once backups are verified:

1. **Proceed to Phase 3:** Create Alembic migration script
2. **Do NOT delete backups** until migration is confirmed successful
3. **Keep backup location** documented in case rollback is needed

---

**Backup Strategy Completed:** Ready for Phase 3
**Estimated Rollback Time:** < 5 minutes with automated scripts
**Risk Mitigation:** ✅ Complete
