# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**LearnR** is an AI-powered adaptive learning platform for CBAP (Certified Business Analysis Professional) exam preparation, built with comprehensive TDD specifications. The platform uses:
- **Backend**: FastAPI + Python 3.11
- **Frontend**: Next.js 14 + React (planned)
- **Database**: PostgreSQL 15 + pgvector
- **Payment**: Stripe integration
- **AI**: OpenAI embeddings for semantic search

**Development Approach**: TDD with comprehensive Technical Design Documents (TDDocs) serving as executable specifications.

## Architecture

### Multi-Course Platform Design

The platform is designed for extensibility beyond CBAP:
- **Multi-course support**: CBAP (6 KAs), PSM1 (3 KAs), CFA (10 KAs) - variable knowledge area counts per course
- **Course lifecycle**: Draft → Active → Archived with wizard-style creation (Decision #65)
- **No hardcoded course logic**: All algorithms work dynamically based on course_id and KA structure

### Core Learning System

**Adaptive Learning Algorithm** (Decision #3, #19):
- **1PL IRT** (Item Response Theory) for competency estimation in MVP
- **2PL IRT upgrade path**: `discrimination` field reserved (NULL in MVP, Decision #64)
- Real-time competency updates after each question attempt
- Question selection based on user competency and difficulty matching

**Spaced Repetition** (Decision #31, #32):
- **SM-2 algorithm** for optimal retention
- Tracks easiness factor, interval days, and repetition count
- Cards scheduled based on performance quality (0-5 rating)

**Knowledge Architecture**:
- Course → Knowledge Areas (variable count) → Domains (optional sub-topics)
- KA weights must sum to 100% per course (enforced via database trigger)
- Questions and content chunks mapped to KAs and domains

### Database Architecture

**23 tables across 5 categories**:

1. **Core** (5 tables): users, user_profiles, courses, knowledge_areas, domains
2. **Content** (3 tables): questions, answer_choices, content_chunks
3. **Learning** (5 tables): sessions, question_attempts, user_competency, spaced_repetition_cards, reading_consumed
4. **Financial** (8 tables): subscription_plans, subscriptions, payments, refunds, chargebacks, payment_methods, invoices, revenue_events
5. **Security** (2 tables): security_logs, rate_limit_entries

**Key Design Patterns**:
- UUIDs for all primary keys (security, no sequential IDs)
- Field-level encryption for PII (email, names) using Fernet (Decision #59)
- Hybrid properties in SQLAlchemy for transparent encryption/decryption
- Immutable audit trail (security_logs cannot be updated/deleted)
- PCI DSS compliant payment storage (tokenized via Stripe)

**Critical Indexes**:
```sql
-- Question selection (adaptive algorithm)
CREATE INDEX idx_questions_adaptive ON questions(course_id, ka_id, difficulty, is_active);

-- Competency lookups
CREATE INDEX idx_competency_dashboard ON user_competency(user_id, ka_id, competency_score);

-- Spaced repetition
CREATE INDEX idx_sr_cards_due ON spaced_repetition_cards(user_id, next_review_at) WHERE is_due = true;
```

### API Design

**RESTful FastAPI** with:
- JWT authentication (1-hour expiry, refresh tokens)
- Role-based access control: learner, admin, super_admin
- Pydantic v2 for request/response validation
- Rate limiting: 100 req/min (authenticated users)
- Pagination for all list endpoints (page, per_page)
- OpenAPI 3.0 auto-generated documentation at `/docs`

**Key Endpoint Groups**:
- `/v1/auth/*` - Registration, login, 2FA
- `/v1/onboarding/*` - Profile setup, course selection
- `/v1/sessions/*` - Diagnostic, practice, mock exams
- `/v1/dashboard` - Progress tracking, competency scores
- `/v1/reviews/*` - Spaced repetition due cards
- `/v1/admin/*` - Course management, metrics, user management
- `/v1/webhooks/stripe` - Payment event processing

### Security & Compliance

**Authentication** (Decision #53):
- Argon2id password hashing (cost factor 12)
- JWT tokens with RS256 signing
- 2FA support (TOTP, Decision #50)

**Data Protection** (Decision #59):
- PII encrypted at rest (AES-256 via Fernet)
- HTTPS only (enforced at infrastructure level)
- Rate limiting to prevent brute force
- IP allowlisting for admin access (Decision #56)

**GDPR Compliance**:
- User data export capability
- Account deletion with 30-day anonymization window
- Immutable security logs for audit trail

## Development Commands

### Environment Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies (when requirements.txt exists)
pip install -r requirements.txt

# Set encryption key for PII
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Database connection
export DATABASE_URL="postgresql://user:pass@localhost/learnr_db"
```

### Database Operations

```bash
# Apply migrations (Alembic)
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Rollback one migration
alembic downgrade -1

# Seed initial data (courses, KAs)
python scripts/seed_data.py
```

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_models.py

# Run with coverage
pytest --cov=app --cov-report=html

# Run only unit tests (fast)
pytest -m unit

# Run integration tests (slower)
pytest -m integration
```

### Running the Application

```bash
# Development server with auto-reload
uvicorn app.main:app --reload --port 8000

# Production server
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Technical Design Documents (TDDocs)

All specifications are in `/docs/`:

1. **TDDoc_DatabaseSchema.md** (v1.3) - Complete PostgreSQL schema with 23 tables
2. **TDDoc_DataModels.md** (v1.0) - SQLAlchemy ORM models + Pydantic schemas
3. **TDDoc_API_Endpoints.md** (v1.0) - 45+ RESTful endpoints with request/response contracts
4. **TDDoc_Algorithms.md** - IRT competency estimation, adaptive selection, SM-2 spaced repetition
5. **TDDoc_AdminDashboard_FinancialQueries.md** - Revenue metrics (MRR, ARR, churn)
6. **TDDoc_Admin_Bootstrap_Process.md** - Admin user creation and initial setup
7. **TDDoc_Content_Quality_Evaluation_System.md** - LLM-generated question validation

**TDD Workflow**:
1. TDDocs serve as executable specifications
2. Write tests from TDDoc specs (before implementation)
3. Implement code to pass tests (red-green-refactor)
4. All business logic decisions documented in TDDocs

## File Structure

```
learnr_build/
├── app/
│   ├── models/           # SQLAlchemy ORM models
│   │   ├── database.py   # Base, session config
│   │   ├── user.py       # User, UserProfile
│   │   ├── course.py     # Course, KnowledgeArea, Domain
│   │   ├── question.py   # Question, AnswerChoice
│   │   ├── learning.py   # UserCompetency, Session, QuestionAttempt
│   │   ├── spaced_repetition.py
│   │   ├── financial.py  # Subscription, Payment, Refund, etc.
│   │   └── security.py   # SecurityLog, RateLimitEntry
│   ├── schemas/          # Pydantic models for API
│   │   ├── user.py
│   │   ├── course.py
│   │   ├── question.py
│   │   ├── learning.py
│   │   ├── financial.py
│   │   └── auth.py
│   ├── api/              # FastAPI routers
│   │   ├── v1/
│   │   │   ├── auth.py
│   │   │   ├── onboarding.py
│   │   │   ├── sessions.py
│   │   │   ├── dashboard.py
│   │   │   ├── admin.py
│   │   │   └── webhooks.py
│   ├── services/         # Business logic
│   │   ├── auth.py
│   │   ├── adaptive_learning.py
│   │   ├── spaced_repetition.py
│   │   ├── competency.py
│   │   └── payments.py
│   ├── utils/
│   │   ├── encryption.py  # PII encryption (Fernet)
│   │   ├── validators.py  # Custom Pydantic validators
│   │   └── security.py    # Password hashing, JWT
│   └── main.py           # FastAPI application
├── tests/
│   ├── unit/             # Fast, isolated tests
│   ├── integration/      # Database + API tests
│   └── e2e/              # End-to-end flows
├── alembic/              # Database migrations
├── docs/                 # TDDocs (specifications)
└── scripts/              # Admin utilities, seeding
```

## Important Patterns & Conventions

### Encryption Pattern

All PII fields use hybrid properties for transparent encryption:

```python
# In SQLAlchemy model (app/models/user.py)
_email = Column("email", String(255), unique=True, nullable=False)

@hybrid_property
def email(self) -> str:
    return decrypt_field(self._email)

@email.setter
def email(self, value: str):
    self._email = encrypt_field(value)

# Usage is transparent
user.email = "test@example.com"  # Automatically encrypted in DB
print(user.email)  # Automatically decrypted: "test@example.com"
```

### Question Selection Algorithm

Adaptive selection based on competency (from TDDoc_Algorithms.md):

```python
# 1. Get user's weakest KA
weakest_ka = min(user_competencies, key=lambda x: x.competency_score)

# 2. Select questions matching difficulty ±0.1 of competency
target_difficulty = weakest_ka.competency_score
questions = query_questions(
    course_id=user.course_id,
    ka_id=weakest_ka.ka_id,
    difficulty_range=(target_difficulty - 0.1, target_difficulty + 0.1),
    exclude_recent=True,
    limit=10
)
```

### Course Addition (Multi-Course Support)

To add a new course (Decision #63, #65):

1. **Create course** (status='draft'):
   ```sql
   INSERT INTO courses (course_code, course_name, status, ...)
   VALUES ('PSM1', 'Professional Scrum Master I', 'draft', ...);
   ```

2. **Add knowledge areas** (must sum to 100%):
   ```sql
   INSERT INTO knowledge_areas (course_id, ka_code, weight_percentage, ...)
   VALUES
     ('course_id', 'SCRUM_THEORY', 33.33, ...),
     ('course_id', 'SCRUM_ROLES', 33.33, ...),
     ('course_id', 'SCRUM_EVENTS', 33.34, ...);
   ```

3. **Bulk import questions** (min 200):
   - Use CSV upload via admin API: `POST /v1/admin/courses/{id}/questions/bulk`
   - Questions distributed across all KAs proportionally

4. **Add content chunks** (min 50):
   - Generate embeddings via OpenAI API
   - Store as VECTOR(3072) in content_chunks table

5. **Publish course**:
   ```sql
   UPDATE courses SET status='active', wizard_completed=true WHERE course_id='...';
   ```

**No code changes needed** - all algorithms work dynamically based on course structure.

### Financial Metrics (Admin Dashboard)

Key queries from TDDoc_AdminDashboard_FinancialQueries.md:

```sql
-- Monthly Recurring Revenue (MRR)
SELECT SUM(
  CASE
    WHEN billing_interval = 'monthly' THEN price_amount
    WHEN billing_interval = 'annual' THEN price_amount / 12
  END
) as mrr
FROM subscriptions s
JOIN subscription_plans p ON s.plan_id = p.plan_id
WHERE s.status = 'active';

-- Churn Rate (%)
SELECT
  COUNT(*) FILTER (WHERE canceled_at IS NOT NULL) * 100.0 /
  COUNT(*) as churn_rate
FROM subscriptions
WHERE current_period_start >= NOW() - INTERVAL '30 days';
```

## Key Decisions & Constraints

**IRT Parameters** (Decision #64):
- MVP uses **1PL IRT** (only `difficulty` parameter)
- `discrimination` field exists but is NULL (reserved for 2PL upgrade)
- Avoids migration overhead when upgrading to 2PL post-MVP

**Course Status Workflow** (Decision #65):
- Draft courses invisible to learners (only admins see them)
- Auto-deleted after 7 days if not completed (abandoned wizard)
- Only `status='active'` courses shown in learner-facing endpoints

**Weight Validation** (Decision #63):
- KA weights validated via database trigger
- Must sum to exactly 100.00% (±0.01 tolerance)
- Validation happens at transaction commit (allows incremental insertion)

**Stripe Integration** (Decision #66):
- Webhooks process payment events asynchronously
- Payment methods stored as tokens only (PCI compliant)
- Subscription lifecycle: trialing → active → canceled
- Revenue events log all financial transactions (immutable)

## Common Tasks

### Adding a New API Endpoint

1. Define Pydantic schemas in `app/schemas/`
2. Create route in `app/api/v1/`
3. Write tests in `tests/integration/api/`
4. Implement business logic in `app/services/`
5. Update TDDoc_API_Endpoints.md

### Modifying Database Schema

1. Update SQLAlchemy models in `app/models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review migration file in `alembic/versions/`
4. Apply: `alembic upgrade head`
5. Update TDDoc_DatabaseSchema.md

### Running Tests for a Specific Feature

```bash
# Test user authentication
pytest tests/unit/test_auth.py tests/integration/api/test_auth.py -v

# Test adaptive learning algorithm
pytest tests/unit/test_adaptive_learning.py -v

# Test spaced repetition
pytest tests/unit/test_spaced_repetition.py -v
```

## Troubleshooting

**Encryption errors**: Ensure `ENCRYPTION_KEY` environment variable is set and consistent across environments.

**Database connection issues**: Check `DATABASE_URL` format: `postgresql://user:pass@host:port/dbname`

**Migration conflicts**: If Alembic detects conflicts, manually review migration files or reset: `alembic downgrade base && alembic upgrade head`

**PII not decrypting**: Verify hybrid properties are accessed (not private `_email` field directly).

**Stripe webhooks failing**: Verify webhook signature validation is enabled and secret is configured.

## References

- **Database Schema**: docs/TDDoc_DatabaseSchema.md (complete table definitions)
- **API Contracts**: docs/TDDoc_API_Endpoints.md (all 45+ endpoints)
- **Data Models**: docs/TDDoc_DataModels.md (SQLAlchemy + Pydantic)
- **Algorithms**: docs/TDDoc_Algorithms.md (IRT, SM-2, adaptive selection)
- **Financial Queries**: docs/TDDoc_AdminDashboard_FinancialQueries.md (MRR, ARR, churn)
