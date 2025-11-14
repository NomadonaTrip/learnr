# LearnR - Quick Start Guide

Get LearnR running locally in under 10 minutes.

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Git

---

## Backend Setup (5 minutes)

### 1. Set Up Database

```bash
# Start PostgreSQL (if not running)
# macOS/Linux:
sudo service postgresql start

# Create database
createdb learnr_db

# Or using psql:
psql -U postgres
CREATE DATABASE learnr_db;
\q
```

### 2. Configure Backend

```bash
# Navigate to project root
cd learnr_build

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://postgres:password@localhost/learnr_db"
export SECRET_KEY="your-secret-key-change-in-production"
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# On Windows, use 'set' instead of 'export'
```

### 3. Run Migrations

```bash
# Apply database migrations
alembic upgrade head

# Seed CBAP course data (optional but recommended)
python scripts/seed_cbap_course.py
```

### 4. Start Backend Server

```bash
# Development server with auto-reload
uvicorn app.main:app --reload --port 8000

# Server will start at: http://localhost:8000
# API docs available at: http://localhost:8000/docs
```

---

## Frontend Setup (3 minutes)

### 1. Install Dependencies

```bash
# Open a new terminal window
cd frontend

# Install npm packages
npm install
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.local.example .env.local

# Edit .env.local (optional - defaults to localhost:8000)
# NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Start Frontend Server

```bash
# Development server
npm run dev

# Frontend will start at: http://localhost:3000
```

---

## Testing the Application

### 1. Register a New User

1. Open http://localhost:3000
2. Click "Sign up" or navigate to `/register`
3. Fill in the registration form:
   - First Name: John
   - Last Name: Doe
   - Email: test@example.com
   - Password: TestPassword123
4. Click "Create Account"

### 2. Explore the Dashboard

After registration, you'll be redirected to the dashboard at `/dashboard`:
- View your overall competency (will be 0% initially)
- See knowledge area breakdown
- Check quick action cards

### 3. Start a Practice Session

1. Click "Practice Questions" from the dashboard
2. Select session type (e.g., "Diagnostic Test")
3. Choose question count (e.g., 10 questions)
4. Click "Start Session"
5. Answer questions and see real-time feedback
6. Review your session summary

### 4. Take a Mock Exam

1. Navigate to "Mock Exams" from the sidebar
2. Click "Start Mock Exam"
3. Answer questions with the timer running
4. Use the question navigator to jump between questions
5. Submit and view comprehensive results

### 5. View Study Materials

1. Navigate to "Study Materials"
2. Select a recommendation strategy
3. Browse personalized content
4. Mark content as read

### 6. Review Flashcards

1. Navigate to "Review Cards"
2. View flashcards for spaced repetition
3. Rate your recall quality
4. Complete the review session

### 7. Track Your Progress

1. Navigate to "Progress"
2. View exam readiness indicator
3. Check detailed KA mastery breakdown
4. See achievement badges

---

## Verification Checklist

- [ ] Backend running at http://localhost:8000
- [ ] Backend API docs accessible at http://localhost:8000/docs
- [ ] Frontend running at http://localhost:3000
- [ ] Can register a new user
- [ ] Can login successfully
- [ ] Dashboard loads with data
- [ ] Can start and complete a practice session
- [ ] Can view content recommendations
- [ ] Can take a mock exam
- [ ] All pages load without errors

---

## Common Issues & Solutions

### **Backend Issues**

**Database connection error:**
```bash
# Check PostgreSQL is running
sudo service postgresql status

# Verify DATABASE_URL is correct
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL
```

**Migration errors:**
```bash
# Reset database (WARNING: deletes all data)
alembic downgrade base
alembic upgrade head
```

**Import errors:**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

---

### **Frontend Issues**

**Module not found errors:**
```bash
# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

**API connection errors:**
```bash
# Check backend is running
curl http://localhost:8000/health

# Verify .env.local settings
cat .env.local

# Check browser console for CORS errors
```

**Port already in use:**
```bash
# Frontend (3000)
lsof -ti:3000 | xargs kill -9

# Backend (8000)
lsof -ti:8000 | xargs kill -9
```

---

## Development Workflow

### **Running Tests (Backend)**

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/integration/test_auth_endpoints.py -v

# Run only unit tests
pytest -m unit
```

### **Code Quality**

```bash
# Backend linting
flake8 app/

# Frontend linting
npm run lint

# Frontend type checking
npm run type-check
```

### **Database Operations**

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Seed data
python scripts/seed_cbap_course.py
```

---

## Next Steps

1. ✅ **You're up and running!**
2. Read `LAUNCH_STATUS.md` for project status
3. Review `frontend/FRONTEND_BUILD_SUMMARY.md` for frontend details
4. Check `frontend/COMPONENTS_GUIDE.md` for component examples
5. Explore API docs at http://localhost:8000/docs
6. Join development - see `CLAUDE.md` for contribution guidelines

---

**Happy coding! 🚀**

Build with LearnR and help future CBAP candidates succeed!
