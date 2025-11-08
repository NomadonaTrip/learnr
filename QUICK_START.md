# LearnR Quick Start Guide

Once Docker Desktop WSL2 integration is enabled, run these commands:

## 1. Verify Docker Works

```bash
docker --version
docker-compose --version
```

Expected output:
```
Docker version 24.x.x, build xxxxx
Docker Compose version v2.x.x
```

## 2. Run Automated Setup (One Command!)

```bash
bash scripts/setup_database.sh
```

This script will:
- ✅ Start PostgreSQL container
- ✅ Wait for PostgreSQL to be ready
- ✅ Generate Alembic migration (25 tables)
- ✅ Apply migration to database
- ✅ Verify all tables created

## 3. Seed Test Data

```bash
bash scripts/seed_data.sh
```

This creates:
- ✅ CBAP course with 6 knowledge areas
- ✅ 30 sample questions (5 per KA)
- ✅ Test learner account: learner@test.com / Test123Pass
- ✅ Test admin account: admin@test.com / Admin123Pass

## 4. Start API Server

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server will start on: http://localhost:8000

## 5. Test the API

### Option A: Swagger UI (Recommended)
Open browser: http://localhost:8000/docs

### Option B: Manual Testing
See TESTING_GUIDE.md for complete curl commands

### Quick Test Flow:
1. POST /v1/auth/login (email: learner@test.com, password: Test123Pass)
2. Copy access_token
3. Click "Authorize" button in Swagger UI
4. Paste token (without "Bearer")
5. Try all endpoints!

## Common Commands

```bash
# View PostgreSQL logs
docker logs learnr_postgres

# Connect to database
docker exec -it learnr_postgres psql -U postgres -d learnr_db

# Stop all containers
docker-compose down

# Restart containers
docker-compose restart

# View API logs
# (Just watch the uvicorn terminal)

# Re-seed database (WARNING: deletes all data)
docker-compose down -v
bash scripts/setup_database.sh
bash scripts/seed_data.sh
```

## Files Reference

| File | Purpose |
|------|---------|
| DOCKER_SETUP_GUIDE.md | How to enable Docker Desktop WSL2 |
| TESTING_GUIDE.md | Complete API testing guide |
| QUICK_START.md | This file - quick commands |
| API_ENDPOINTS_COMPLETE.md | All endpoint documentation |
| MODELS_COMPLETE.md | Database schema documentation |
| SCHEMAS_COMPLETE.md | Pydantic schemas documentation |

## Troubleshooting

**Docker not found**
→ Enable Docker Desktop WSL2 integration (see DOCKER_SETUP_GUIDE.md)

**Port 5432 already in use**
→ Another PostgreSQL is running: `sudo service postgresql stop`

**Migration fails**
→ Check .env file has correct DATABASE_URL

**Can't connect to database**
→ Wait 10 seconds for PostgreSQL to start, then retry

**Permission denied on scripts**
→ Run: `chmod +x scripts/*.sh`

## What's Next?

After successful setup:
1. ✅ Test full user flow (registration → onboarding → practice)
2. ⏳ Build dashboard endpoints
3. ⏳ Build spaced repetition endpoints  
4. ⏳ Build admin endpoints
5. ⏳ Write automated tests
6. ⏳ Deploy to production

Happy coding! 🚀
