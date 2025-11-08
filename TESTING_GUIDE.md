# LearnR API Testing Guide

Complete guide to test the LearnR MVP API after Docker setup is complete.

## Prerequisites

✅ Docker Desktop WSL2 integration enabled
✅ PostgreSQL container running
✅ Database migration applied (25 tables created)
✅ Test data seeded (CBAP course, questions, test users)
✅ API server running

## Quick Start

```bash
# 1. Start the API server
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 2. Open API documentation
# Browser: http://localhost:8000/docs
```

## Test Credentials

**Test Learner:**
- Email: `learner@test.com`
- Password: `Test123Pass`

**Test Admin:**
- Email: `admin@test.com`
- Password: `Admin123Pass`

**Bootstrap Super Admin:**
- Email: From `.env` file (`BOOTSTRAP_ADMIN_EMAIL`)
- Password: From `.env` file (`BOOTSTRAP_ADMIN_PASSWORD`)
- ⚠️ Will be forced to change password on first login

---

## Testing Flow 1: Complete User Journey

### Step 1: Register New User

```bash
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@test.com",
    "password": "NewUser123",
    "first_name": "New",
    "last_name": "User"
  }'
```

**Expected Response (201):**
```json
{
  "user_id": "uuid-here",
  "email": "newuser@test.com",
  "first_name": "New",
  "last_name": "User",
  "role": "learner",
  "is_active": true,
  "email_verified": false,
  "two_factor_enabled": false,
  "must_change_password": false,
  ...
}
```

### Step 2: Login

```bash
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@test.com",
    "password": "NewUser123"
  }'
```

**Expected Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Save the access_token for next steps!**

### Step 3: Get Available Courses

```bash
curl -X GET http://localhost:8000/v1/onboarding/courses \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Expected Response (200):**
```json
[
  {
    "course_id": "cbap-uuid-here",
    "course_code": "CBAP",
    "course_name": "Certified Business Analysis Professional",
    "status": "active",
    ...
  }
]
```

**Save the course_id for next step!**

### Step 4: Complete Onboarding

```bash
curl -X POST http://localhost:8000/v1/onboarding/profile \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "CBAP_COURSE_UUID_HERE",
    "current_level": "intermediate",
    "daily_commitment_minutes": 60,
    "exam_date": "2025-12-15",
    "target_score_percentage": 85,
    "motivation": "Career advancement in business analysis"
  }'
```

**Expected Response (201):**
```json
{
  "profile_id": "uuid-here",
  "user_id": "uuid-here",
  "course_id": "cbap-uuid",
  "current_level": "intermediate",
  "daily_commitment_minutes": 60,
  ...
}
```

**This also creates UserCompetency records for all 6 KAs!**

### Step 5: Create Practice Session

```bash
curl -X POST http://localhost:8000/v1/sessions \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_type": "practice"
  }'
```

**Expected Response (201):**
```json
{
  "session_id": "session-uuid-here",
  "user_id": "user-uuid",
  "session_type": "practice",
  "total_questions": 0,
  "correct_answers": 0,
  "is_completed": false,
  ...
}
```

**Save the session_id!**

### Step 6: Get First Question (Adaptive)

```bash
curl -X GET http://localhost:8000/v1/sessions/SESSION_UUID/next-question \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Expected Response (200):**
```json
{
  "question_id": "question-uuid",
  "course_id": "cbap-uuid",
  "ka_id": "ka-uuid",
  "question_text": "Sample question 1 for Business Analysis Planning...",
  "question_type": "multiple_choice",
  "answer_choices": [
    {
      "choice_id": "choice-a-uuid",
      "choice_letter": "A",
      "choice_text": "Option A - Incorrect answer..."
    },
    {
      "choice_id": "choice-b-uuid",
      "choice_letter": "B",
      "choice_text": "Option B - Correct answer..."
    }
  ]
}
```

**Note: Correct answer is NOT shown! (is_correct field is hidden)**

### Step 7: Submit Answer

```bash
curl -X POST http://localhost:8000/v1/sessions/SESSION_UUID/attempt \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question_id": "QUESTION_UUID",
    "selected_choice_id": "CHOICE_UUID",
    "time_spent_seconds": 45
  }'
```

**Expected Response (200):**
```json
{
  "attempt_id": "attempt-uuid",
  "is_correct": true,
  "correct_choice_id": "choice-b-uuid",
  "correct_choice_letter": "B",
  "explanation": "Explanation for B: This is the correct answer because...",
  "competency_at_attempt": 0.50,
  ...
}
```

**This updates UserCompetency for the question's KA!**

### Step 8: Repeat Steps 6-7 multiple times

Try answering 5-10 questions to see:
- Adaptive selection (focuses on weakest KA)
- Competency score changes
- Session stats update

### Step 9: Complete Session

```bash
curl -X POST http://localhost:8000/v1/sessions/SESSION_UUID/complete \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "duration_minutes": 15
  }'
```

**Expected Response (200):**
```json
{
  "session_id": "session-uuid",
  "is_completed": true,
  "completed_at": "2025-10-31T12:30:00Z",
  "total_questions": 10,
  "correct_answers": 7,
  "accuracy_percentage": 70.0,
  "duration_minutes": 15
}
```

---

## Testing Flow 2: Authentication Features

### Test Password Change

```bash
curl -X POST http://localhost:8000/v1/auth/change-password \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "NewUser123",
    "new_password": "UpdatedPass456"
  }'
```

### Test Token Refresh

```bash
curl -X POST http://localhost:8000/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

### Test Get Current User

```bash
curl -X GET http://localhost:8000/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Testing Flow 3: Using Swagger UI (Recommended)

The easiest way to test is using Swagger UI:

1. **Open Browser:** http://localhost:8000/docs

2. **Authenticate:**
   - Click "Authorize" button (🔓 icon)
   - Login to get access token
   - Paste token (without "Bearer " prefix)
   - Click "Authorize"

3. **Test Endpoints:**
   - All endpoints now include authentication
   - Click "Try it out" on any endpoint
   - Fill in parameters
   - Click "Execute"
   - See response below

4. **Test Complete Flow:**
   - POST /v1/auth/register → Create user
   - POST /v1/auth/login → Get token
   - GET /v1/onboarding/courses → Get CBAP course
   - POST /v1/onboarding/profile → Complete onboarding
   - POST /v1/sessions → Create session
   - GET /v1/sessions/{id}/next-question → Get question
   - POST /v1/sessions/{id}/attempt → Submit answer
   - Repeat getting questions and submitting answers
   - POST /v1/sessions/{id}/complete → Complete session

---

## Verification Checklist

After running the full flow, verify in the database:

```bash
# Connect to PostgreSQL
docker exec -it learnr_postgres psql -U postgres -d learnr_db

# Check users
SELECT user_id, email, role, is_active FROM users;

# Check user profiles
SELECT user_id, course_id, current_level, daily_commitment_minutes FROM user_profiles;

# Check user competencies (should be 6 records per user who completed onboarding)
SELECT user_id, ka_id, competency_score, questions_attempted, questions_correct FROM user_competency;

# Check sessions
SELECT session_id, user_id, session_type, total_questions, correct_answers, is_completed FROM sessions;

# Check question attempts
SELECT user_id, question_id, is_correct, competency_at_attempt FROM question_attempts ORDER BY attempted_at DESC LIMIT 10;

# Check security logs
SELECT event_type, success, ip_address, occurred_at FROM security_logs ORDER BY occurred_at DESC LIMIT 10;

# Exit
\q
```

---

## Expected Behavior

### ✅ What Should Work:

1. **Registration:**
   - Creates encrypted user record
   - Validates password strength
   - Returns user data (no password)

2. **Login:**
   - Verifies email/password (Argon2id)
   - Returns JWT access + refresh tokens
   - Logs security event
   - Updates last_login_at

3. **Onboarding:**
   - Creates user profile
   - Initializes 6 UserCompetency records (one per KA)
   - All start at 0.50 competency score

4. **Adaptive Question Selection:**
   - Finds user's weakest KA
   - Selects question matching competency ±0.15
   - Avoids last 20 attempted questions

5. **Answer Submission:**
   - Records attempt
   - Updates session stats
   - Updates competency score (IRT algorithm)
   - Returns correct answer + explanation

6. **Competency Updates:**
   - Correct answer: Score increases (weighted by difficulty)
   - Incorrect answer: Score decreases
   - Score clamped to [0.00, 1.00]

### ⚠️ What Might Not Work Yet:

- Dashboard endpoints (not implemented)
- Spaced repetition (not implemented)
- Admin endpoints (not implemented)
- Stripe webhooks (not implemented)
- Content search (not implemented)
- Rate limiting (not implemented)

---

## Troubleshooting

### 401 Unauthorized
- Token expired (1 hour lifetime) → Use refresh token
- Token invalid → Login again
- Missing "Bearer " prefix → Add it

### 404 Not Found
- Check UUIDs are correct
- Verify resource belongs to authenticated user

### 400 Bad Request
- Check request body matches schema
- Verify all required fields present
- Check data types and validation rules

### 500 Internal Server Error
- Check API server logs
- Check PostgreSQL logs: `docker logs learnr_postgres`
- Verify database connection in .env

---

## Next Steps After Testing

Once basic flow works:

1. ✅ Verify competency updates work correctly
2. ✅ Test with multiple users
3. ✅ Test edge cases (wrong passwords, invalid data)
4. ⏳ Build dashboard endpoints
5. ⏳ Build spaced repetition endpoints
6. ⏳ Build admin endpoints
7. ⏳ Write automated tests
8. ⏳ Build frontend

Happy testing! 🚀
