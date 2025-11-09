# LearnR Scripts

Utility scripts for managing the LearnR platform.

## Admin User Management

### Create Admin User

Create a new admin or super_admin user for the platform.

**Basic Usage:**
```bash
# Interactive mode (prompts for all info)
python scripts/create_admin_user.py

# Command-line mode with password prompt
python scripts/create_admin_user.py \
  --email admin@learnr.com \
  --first-name Admin \
  --last-name User \
  --role admin

# Fully automated (password in command - less secure)
python scripts/create_admin_user.py \
  --email admin@learnr.com \
  --password SecurePass123 \
  --first-name Admin \
  --last-name User \
  --role admin
```

**Required Environment Variables:**
- `DATABASE_URL`: PostgreSQL connection string
- `ENCRYPTION_KEY`: Fernet key for PII encryption

**Roles:**
- `admin`: Can manage courses, content, and users
- `super_admin`: Full system access (same as admin in MVP)

**Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit

**Examples:**

Create first admin (bootstrap):
```bash
export DATABASE_URL="postgresql://user:pass@localhost/learnr_db"
export ENCRYPTION_KEY="your-fernet-key"

python scripts/create_admin_user.py \
  --email admin@learnr.com \
  --role super_admin
# Will prompt for password securely
```

Create additional admin:
```bash
python scripts/create_admin_user.py \
  --email manager@learnr.com \
  --first-name Course \
  --last-name Manager \
  --role admin
```

**Security Notes:**
- Passwords are hashed using Argon2id (cost factor 12)
- Email and names are encrypted at rest using Fernet
- Creation is logged in security_logs table
- Script prevents duplicate emails

---

## Database Management

### Setup Database
```bash
./scripts/setup_database.sh
```
Initializes the PostgreSQL database with all tables and triggers.

### Seed Data
```bash
./scripts/seed_data.sh
# or
python scripts/seed_data.py
```
Populates the database with sample courses and knowledge areas.

### Backup Database
```bash
./scripts/backup_database.sh
```
Creates a timestamped backup of the database.

### Restore Database
```bash
./scripts/restore_database.sh backup_file.sql
```
Restores database from a backup file.

---

## Testing Scripts

### Test Database Connection
```bash
python scripts/test_database.py
```
Verifies database connectivity and basic queries.

### Test Diagnostic Flow
```bash
./scripts/test_diagnostic_flow.sh
# or
python scripts/test_diagnostic_simple.py
```
Tests the diagnostic assessment workflow.

### Test Practice Flow
```bash
python scripts/test_practice_flow.py
```
Tests the practice session workflow.

### Test Dashboard
```bash
python scripts/test_dashboard.py
```
Tests the dashboard endpoints.

### Test Spaced Repetition
```bash
python scripts/test_spaced_repetition.py
```
Tests the spaced repetition system.

---

## Development Workflows

### Initial Setup
1. Set up database:
   ```bash
   ./scripts/setup_database.sh
   ```

2. Run migrations:
   ```bash
   alembic upgrade head
   ```

3. Create admin user:
   ```bash
   python scripts/create_admin_user.py \
     --email admin@learnr.com \
     --role super_admin
   ```

4. Seed sample data:
   ```bash
   python scripts/seed_data.py
   ```

### Adding New Admin Users

For production:
```bash
python scripts/create_admin_user.py \
  --email newadmin@company.com \
  --first-name FirstName \
  --last-name LastName \
  --role admin
```

For development/testing:
```bash
python scripts/create_admin_user.py \
  --email test@example.com \
  --password TestPass123 \
  --role admin
```

---

## Troubleshooting

**"DATABASE_URL not set"**
- Ensure environment variable is exported:
  ```bash
  export DATABASE_URL="postgresql://user:pass@localhost/learnr_db"
  ```

**"ENCRYPTION_KEY not set"**
- Generate and set encryption key:
  ```bash
  export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
  ```

**"User already exists"**
- Check existing users:
  ```bash
  psql $DATABASE_URL -c "SELECT email FROM users WHERE role IN ('admin', 'super_admin');"
  ```

**"Failed to connect to database"**
- Verify PostgreSQL is running
- Check DATABASE_URL format: `postgresql://user:password@host:port/database`
- Test connection: `psql $DATABASE_URL`

---

## Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DATABASE_URL` | Yes | PostgreSQL connection string | `postgresql://user:pass@localhost/learnr_db` |
| `ENCRYPTION_KEY` | Yes | Fernet encryption key for PII | `generated-fernet-key-here` |
| `OPENAI_API_KEY` | No | OpenAI API key for embeddings | `sk-...` |

---

## Security Best Practices

1. **Never commit credentials** to version control
2. **Use strong passwords** for admin users (12+ characters recommended)
3. **Enable 2FA** for super_admin users in production
4. **Rotate encryption keys** periodically (requires re-encryption migration)
5. **Backup regularly** before major operations
6. **Test scripts** in development before running in production
7. **Use interactive mode** for password entry (more secure than command-line)

---

## Contributing

When adding new scripts:
1. Add comprehensive docstrings
2. Include usage examples in this README
3. Handle errors gracefully
4. Use argparse for command-line arguments
5. Follow existing script patterns
