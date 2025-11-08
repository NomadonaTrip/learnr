# Technical Design Document - API Endpoints
# LearnR - Adaptive Learning Platform

**Version:** 1.3.1 (Aligned with DatabaseSchema v1.3.1)  
**Date:** October 30, 2025  
**Status:** PRODUCTION READY  
**Related Documents:**
- TDDoc_DatabaseSchema.md v1.3.1
- TDDoc_DataModels.md v1.3.1
- TDDoc_Algorithms.md v1.3.1
- Decision Log (note.md) - Decisions #1-83

**Total Endpoints:** 65+ (was 45+ in v1.0)

**Changelog:**
- v1.0: Initial 45+ endpoints
- v1.3.1: Added bootstrap admin, content quality review (4 endpoints), financial dashboard (3 endpoints), IP allowlist management (3 endpoints), failed login tracking (1 endpoint), content feedback (1 endpoint) = 13 new endpoints

---

## Overview

This document specifies all API endpoints for the Adaptive CBAP Learning Platform MVP. It defines:
- **RESTful API Design** (resource-based URLs, HTTP verbs)
- **Request/Response Contracts** (using Pydantic schemas from TDDoc_DataModels.md)
- **Authentication & Authorization** (JWT tokens, role-based access)
- **Error Handling** (consistent error responses)
- **Rate Limiting** (prevent abuse)
- **Webhooks** (Stripe payment events)

**TDD Purpose:** This document serves as the executable specification for API endpoint tests. Tests can be written against these endpoints before implementation.

---

## Technology Stack

- **Framework:** FastAPI 0.104+
- **Authentication:** JWT (JSON Web Tokens) via `python-jose`
- **Authorization:** Role-based access control (RBAC)
- **Validation:** Pydantic v2 (automatic request/response validation)
- **Documentation:** OpenAPI 3.0 (auto-generated via FastAPI)
- **Rate Limiting:** slowapi (token bucket algorithm)
- **CORS:** fastapi.middleware.cors

---

## Architecture Principles

1. **RESTful Design:**
   - Resource-based URLs (`/users/{id}`, not `/getUser`)
   - HTTP verbs for actions (GET, POST, PUT, PATCH, DELETE)
   - Stateless (JWT tokens, no server-side sessions)

2. **Security First:**
   - All endpoints require authentication (except auth endpoints)
   - Role-based authorization (learner, admin, super_admin)
   - HTTPS only (enforced at infrastructure level)
   - Rate limiting on all endpoints

3. **Consistency:**
   - Standardized error responses
   - Consistent naming (snake_case for JSON)
   - ISO 8601 for dates
   - UUID for all resource IDs

4. **Performance:**
   - Pagination for list endpoints
   - Lazy loading (don't return nested objects by default)
   - Field selection (`?fields=email,first_name`)
   - Caching headers where appropriate

---

## Base URL & Versioning

**Base URL:** `https://api.cbapplatform.com/v1`

**Versioning Strategy:** URL path versioning
- Current: `/v1/`
- Future: `/v2/` (when breaking changes needed)

---

## Authentication & Authorization

### Authentication Flow (JWT)

**Decision #53:** Argon2id for password hashing

```
1. User Login â†’ POST /v1/auth/login
2. Server validates credentials (Argon2id hash check)
3. Server returns JWT access token + refresh token
4. Client includes token in Authorization header: `Bearer <token>`
5. Server validates JWT on every request
6. Token expires after 1 hour
7. Client uses refresh token to get new access token
```

**JWT Payload:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "role": "learner",
  "exp": 1698765432,
  "iat": 1698761832
}
```

### Authorization Roles

- **learner:** Regular users (can access own data only)
- **admin:** Course creators (can manage courses, view all users)
- **super_admin:** Full access (can manage admins, billing, security)

### Protected Endpoints

All endpoints except these require authentication:
- `POST /v1/auth/register`
- `POST /v1/auth/login`
- `POST /v1/auth/refresh`
- `POST /v1/webhooks/stripe` (authenticated via Stripe signature)

---

## Error Handling

### Standard Error Response

All errors return this structure:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid email format",
    "details": {
      "field": "email",
      "value": "invalid-email"
    },
    "request_id": "uuid"
  }
}
```

### Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | VALIDATION_ERROR | Invalid request data |
| 401 | UNAUTHORIZED | Missing or invalid token |
| 403 | FORBIDDEN | Insufficient permissions |
| 404 | NOT_FOUND | Resource not found |
| 409 | CONFLICT | Resource already exists |
| 422 | UNPROCESSABLE_ENTITY | Business logic validation failed |
| 429 | RATE_LIMIT_EXCEEDED | Too many requests |
| 500 | INTERNAL_ERROR | Server error |

---

## Rate Limiting

**Decision #52:** Rate limiting to prevent abuse

**Limits:**
- Anonymous: 10 requests/minute
- Authenticated: 100 requests/minute
- Admin: 500 requests/minute
- Burst: 2x limit for 10 seconds

**Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1698765432
```

**Rate Limit Error:**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Retry after 60 seconds.",
    "retry_after": 60
  }
}
```

---

## Pagination

**All list endpoints support pagination:**

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)

**Response:**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_items": 150,
    "total_pages": 8
  }
}
```

---

## API Endpoints

### 1. Authentication & User Management

#### POST /v1/auth/register

Register a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response:** `201 Created`
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "learner",
  "created_at": "2025-10-24T10:30:00Z"
}
```

**Validation:**
- Email: Valid format, unique, not from disposable domain
- Password: Min 8 chars, max 100 chars
- Names: Min 1 char, max 100 chars

**Errors:**
- `409 CONFLICT`: Email already exists

---

#### POST /v1/auth/login

Authenticate user and get JWT tokens.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "user_id": "uuid",
    "email": "user@example.com",
    "first_name": "John",
    "role": "learner"
  }
}
```

**Errors:**
- `401 UNAUTHORIZED`: Invalid credentials

**Side Effects:**
- Updates `users.last_login_at`
- Creates security log entry

---

#### POST /v1/auth/refresh

Get new access token using refresh token.

**Request:**
```json
{
  "refresh_token": "eyJhbGc..."
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

---

#### POST /v1/auth/logout

Invalidate refresh token (blacklist).

**Request:** Headers only (`Authorization: Bearer <token>`)

**Response:** `204 No Content`

**Side Effects:**
- Adds refresh token to blacklist (redis)

---

#### GET /v1/users/me

Get current user's profile.

**Auth:** Required

**Response:** `200 OK`
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "learner",
  "email_verified": true,
  "two_factor_enabled": false,
  "last_login_at": "2025-10-24T10:30:00Z",
  "created_at": "2025-10-01T08:00:00Z"
}
```

---

#### PATCH /v1/users/me

Update current user's profile.

**Auth:** Required

**Request:**
```json
{
  "first_name": "Jonathan",
  "last_name": "Doe"
}
```

**Response:** `200 OK` (same as GET /v1/users/me)

**Note:** Email changes require email verification flow (not in MVP)

---

#### DELETE /v1/users/me

Delete current user's account (soft delete).

**Auth:** Required

**Response:** `204 No Content`

**Side Effects:**
- Sets `users.is_active = false`
- Anonymizes PII after 30 days (GDPR compliance)

---

### 2. Onboarding

#### POST /v1/onboarding/profile

Complete user profile during onboarding (Decision #10: 7 questions).

**Auth:** Required

**Request:**
```json
{
  "course_id": "uuid",
  "referral_source": "search",
  "referral_source_detail": "Google",
  "motivation": "Career advancement",
  "exam_date": "2025-12-21",
  "current_level": "intermediate",
  "target_score_percentage": 80,
  "daily_commitment_minutes": 30
}
```

**Response:** `201 Created`
```json
{
  "profile_id": "uuid",
  "user_id": "uuid",
  "course_id": "uuid",
  "exam_date": "2025-12-21",
  "days_until_exam": 58,
  "current_level": "intermediate",
  "target_score_percentage": 80,
  "daily_commitment_minutes": 30,
  "created_at": "2025-10-24T10:30:00Z"
}
```

**Validation:**
- course_id: Must exist in courses table
- current_level: Must be 'beginner', 'intermediate', or 'advanced'
- target_score_percentage: 70-100
- daily_commitment_minutes: 15-120

**Side Effects:**
- Creates user_profile record
- Initializes user_competency records (one per KA)
- Triggers diagnostic session creation

---

#### GET /v1/onboarding/courses

Get available courses for onboarding.

**Auth:** Required

**Response:** `200 OK`
```json
{
  "courses": [
    {
      "course_id": "uuid",
      "course_code": "CBAP",
      "course_name": "Certified Business Analysis Professional",
      "description": "...",
      "total_questions": 120,
      "exam_duration_minutes": 210,
      "knowledge_area_count": 6
    }
  ]
}
```

**Note:** Only returns courses with status='active' and wizard_completed=true

---

### 3. Learning Sessions

#### POST /v1/sessions/diagnostic

Start diagnostic session (Decision #11: 24 questions).

**Auth:** Required

**Response:** `201 Created`
```json
{
  "session_id": "uuid",
  "session_type": "diagnostic",
  "total_questions": 24,
  "started_at": "2025-10-24T10:30:00Z",
  "questions": [
    {
      "question_id": "uuid",
      "question_text": "What is...",
      "answer_choices": [
        {
          "choice_id": "uuid",
          "choice_letter": "A",
          "choice_text": "..."
        }
      ]
    }
  ]
}
```

**Algorithm:** Selects 4 questions per KA, difficulty ~0.5 (medium)

---

#### POST /v1/sessions/practice

Start practice session (Decision #12: daily sessions).

**Auth:** Required

**Request:**
```json
{
  "question_count": 10,
  "focus_ka_id": "uuid"
}
```

**Response:** `201 Created` (same structure as diagnostic)

**Algorithm:** Adaptive question selection based on user's competency

---

#### GET /v1/sessions/{session_id}

Get session details.

**Auth:** Required (own sessions only)

**Response:** `200 OK`
```json
{
  "session_id": "uuid",
  "session_type": "practice",
  "total_questions": 10,
  "correct_answers": 7,
  "accuracy_percentage": 70.0,
  "duration_minutes": 15,
  "is_completed": true,
  "started_at": "2025-10-24T10:30:00Z",
  "completed_at": "2025-10-24T10:45:00Z"
}
```

---

#### POST /v1/sessions/{session_id}/answers

Submit answer to a question in session.

**Auth:** Required (own sessions only)

**Request:**
```json
{
  "question_id": "uuid",
  "choice_id": "uuid",
  "time_spent_seconds": 45
}
```

**Response:** `200 OK`
```json
{
  "is_correct": true,
  "correct_choice_id": "uuid",
  "explanation": "This is correct because...",
  "competency_updated": {
    "ka_id": "uuid",
    "previous_score": 0.65,
    "new_score": 0.67
  }
}
```

**Side Effects:**
- Creates question_attempts record
- Updates user_competency (IRT estimation)
- Updates/creates spaced_repetition_cards
- Updates session statistics

---

#### POST /v1/sessions/{session_id}/complete

Mark session as complete.

**Auth:** Required (own sessions only)

**Response:** `200 OK`
```json
{
  "session_id": "uuid",
  "is_completed": true,
  "summary": {
    "total_questions": 10,
    "correct_answers": 7,
    "accuracy_percentage": 70.0,
    "duration_minutes": 15,
    "competencies_updated": [
      {
        "ka_id": "uuid",
        "ka_name": "Requirements Analysis",
        "previous_score": 0.65,
        "new_score": 0.67
      }
    ]
  }
}
```

---

### 4. Questions & Assessments

#### GET /v1/questions/{question_id}

Get question details (for review).

**Auth:** Required

**Response:** `200 OK`
```json
{
  "question_id": "uuid",
  "question_text": "What is...",
  "question_type": "multiple_choice",
  "difficulty": 0.65,
  "ka_id": "uuid",
  "ka_name": "Requirements Analysis",
  "answer_choices": [
    {
      "choice_id": "uuid",
      "choice_letter": "A",
      "choice_text": "..."
    }
  ],
  "source": "BABOK v3 - pp. 45"
}
```

**Note:** Does not reveal correct answer unless user has already answered

---

#### GET /v1/questions/{question_id}/explanation

Get explanation for question (after answering).

**Auth:** Required

**Response:** `200 OK`
```json
{
  "question_id": "uuid",
  "correct_choice_id": "uuid",
  "correct_choice_letter": "B",
  "explanation": "Option B is correct because...",
  "user_answered": "A",
  "was_correct": false
}
```

**Authorization:** Only available if user has answered this question

---

### 5. Progress & Dashboard

#### GET /v1/dashboard

Get user dashboard data (Decision #13).

**Auth:** Required

**Response:** `200 OK`
```json
{
  "user": {
    "user_id": "uuid",
    "first_name": "John",
    "exam_date": "2025-12-21",
    "days_until_exam": 58
  },
  "course": {
    "course_id": "uuid",
    "course_name": "CBAP",
    "total_questions": 120,
    "passing_score": 70
  },
  "competencies": [
    {
      "ka_id": "uuid",
      "ka_name": "Business Analysis Planning",
      "ka_weight": 15.0,
      "competency_score": 0.67,
      "readiness_level": "approaching",
      "questions_attempted": 45,
      "accuracy_percentage": 68.9,
      "last_practiced_at": "2025-10-23T14:30:00Z"
    }
  ],
  "overall_progress": {
    "total_questions_attempted": 250,
    "overall_accuracy": 71.2,
    "average_competency": 0.68,
    "exam_readiness_percentage": 68,
    "estimated_pass_probability": 0.72
  },
  "spaced_repetition": {
    "cards_due_today": 15,
    "cards_due_this_week": 42
  },
  "recommendations": [
    "Focus on Strategy Analysis (competency: 0.55)",
    "Review 15 cards due today"
  ]
}
```

---

#### GET /v1/progress/history

Get historical progress data.

**Auth:** Required

**Query Parameters:**
- `start_date`: ISO 8601 date
- `end_date`: ISO 8601 date
- `ka_id`: Filter by knowledge area (optional)

**Response:** `200 OK`
```json
{
  "data": [
    {
      "date": "2025-10-20",
      "questions_attempted": 10,
      "accuracy_percentage": 70.0,
      "average_competency": 0.65,
      "session_count": 1
    },
    {
      "date": "2025-10-21",
      "questions_attempted": 15,
      "accuracy_percentage": 73.3,
      "average_competency": 0.67,
      "session_count": 2
    }
  ]
}
```

---

### 6. Spaced Repetition

#### GET /v1/reviews/due

Get spaced repetition cards due for review (Decision #31).

**Auth:** Required

**Query Parameters:**
- `limit`: Max cards to return (default: 20)

**Response:** `200 OK`
```json
{
  "cards": [
    {
      "card_id": "uuid",
      "question_id": "uuid",
      "question_text": "What is...",
      "next_review_at": "2025-10-24T10:00:00Z",
      "easiness_factor": 2.5,
      "interval_days": 3,
      "repetitions": 2
    }
  ],
  "total_due": 15
}
```

---

#### POST /v1/reviews/{card_id}/answer

Answer a spaced repetition card (Decision #32: SM-2 algorithm).

**Auth:** Required

**Request:**
```json
{
  "quality": 4,
  "time_spent_seconds": 30
}
```

**Validation:**
- quality: 0-5 (SM-2 quality rating)

**Response:** `200 OK`
```json
{
  "card_id": "uuid",
  "updated": {
    "easiness_factor": 2.6,
    "interval_days": 7,
    "repetitions": 3,
    "next_review_at": "2025-10-31T10:00:00Z"
  },
  "is_correct": true
}
```

**Algorithm:** SM-2 algorithm updates card based on quality rating

---

### 7. Content & Reading

#### GET /v1/content/recommendations

Get personalized reading recommendations (Decision #33).

**Auth:** Required

**Query Parameters:**
- `ka_id`: Focus knowledge area (optional)
- `limit`: Max chunks (default: 5)

**Response:** `200 OK`
```json
{
  "recommendations": [
    {
      "chunk_id": "uuid",
      "content_title": "Stakeholder Analysis Techniques",
      "content_text": "...",
      "ka_name": "Elicitation and Collaboration",
      "estimated_read_time_minutes": 3,
      "relevance_score": 0.92,
      "source": "BABOK v3 - pp. 45-47"
    }
  ]
}
```

**Algorithm:** Vector similarity search based on user's weak areas

---

#### GET /v1/content/chunks/{chunk_id}

Get specific content chunk.

**Auth:** Required

**Response:** `200 OK`
```json
{
  "chunk_id": "uuid",
  "content_title": "Stakeholder Analysis Techniques",
  "content_text": "...",
  "ka_id": "uuid",
  "ka_name": "Elicitation and Collaboration",
  "domain_name": "Stakeholder Engagement",
  "source_document": "BABOK v3",
  "page_reference": "pp. 45-47",
  "estimated_read_time_minutes": 3
}
```

---

### 8. Mock Exams

#### POST /v1/exams/mock

Start mock exam session (Decision #14).

**Auth:** Required

**Response:** `201 Created`
```json
{
  "session_id": "uuid",
  "session_type": "mock_exam",
  "total_questions": 120,
  "duration_minutes": 210,
  "started_at": "2025-10-24T10:00:00Z",
  "expires_at": "2025-10-24T13:30:00Z"
}
```

**Note:** Questions distributed across KAs by weight (15% KA1, 20% KA2, etc.)

---

#### GET /v1/exams/{session_id}/results

Get mock exam results.

**Auth:** Required (own exams only)

**Response:** `200 OK`
```json
{
  "session_id": "uuid",
  "score_percentage": 75.0,
  "passing_score": 70.0,
  "passed": true,
  "total_questions": 120,
  "correct_answers": 90,
  "duration_minutes": 185,
  "breakdown_by_ka": [
    {
      "ka_id": "uuid",
      "ka_name": "Business Analysis Planning",
      "questions": 18,
      "correct": 14,
      "accuracy": 77.8
    }
  ],
  "recommendations": [
    "Focus on Elicitation (66.7% accuracy)",
    "Strong in Requirements Analysis (88.9%)"
  ]
}
```

---

### 9. Subscriptions & Payments

#### GET /v1/subscriptions/plans

Get available subscription plans (Decision #55).

**Auth:** Not required

**Response:** `200 OK`
```json
{
  "plans": [
    {
      "plan_id": "uuid",
      "plan_name": "CBAP Monthly",
      "plan_code": "cbap-monthly",
      "price_amount": 49.99,
      "currency": "USD",
      "billing_interval": "monthly",
      "trial_days": 7,
      "features": {
        "mock_exams": 5,
        "reading_access": true,
        "progress_tracking": true
      }
    }
  ]
}
```

---

#### POST /v1/subscriptions

Create subscription (start trial or paid).

**Auth:** Required

**Request:**
```json
{
  "plan_id": "uuid",
  "payment_method_id": "pm_stripe_xxx"
}
```

**Response:** `201 Created`
```json
{
  "subscription_id": "uuid",
  "plan_id": "uuid",
  "status": "trialing",
  "current_period_start": "2025-10-24T10:00:00Z",
  "current_period_end": "2025-11-24T10:00:00Z",
  "trial_end": "2025-10-31T10:00:00Z"
}
```

**Side Effects:**
- Creates Stripe subscription
- Creates subscription record
- Sends confirmation email

---

#### POST /v1/subscriptions/{subscription_id}/cancel

Cancel subscription.

**Auth:** Required (own subscriptions only)

**Response:** `200 OK`
```json
{
  "subscription_id": "uuid",
  "status": "canceled",
  "canceled_at": "2025-10-24T10:00:00Z",
  "access_until": "2025-11-24T10:00:00Z"
}
```

**Note:** Access continues until end of billing period

---

#### POST /v1/payment-methods

Add payment method (tokenized).

**Auth:** Required

**Request:**
```json
{
  "stripe_payment_method_id": "pm_stripe_xxx",
  "set_as_default": true
}
```

**Response:** `201 Created`
```json
{
  "method_id": "uuid",
  "method_type": "card",
  "brand": "visa",
  "last4": "4242",
  "exp_month": 12,
  "exp_year": 2025,
  "is_default": true
}
```

**Security:** PCI DSS compliant - only stores Stripe token

---

#### GET /v1/payments/history

Get payment history.

**Auth:** Required

**Response:** `200 OK`
```json
{
  "payments": [
    {
      "payment_id": "uuid",
      "amount": 49.99,
      "currency": "USD",
      "status": "succeeded",
      "description": "CBAP Monthly Subscription",
      "paid_at": "2025-10-24T10:00:00Z",
      "invoice_url": "https://..."
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_items": 5
  }
}
```

---

### 10. Admin Dashboard

#### GET /v1/admin/users

List all users (admin only).

**Auth:** Required (admin or super_admin)

**Query Parameters:**
- `page`, `per_page`: Pagination
- `search`: Email or name search
- `role`: Filter by role
- `is_active`: Filter by active status

**Response:** `200 OK`
```json
{
  "users": [
    {
      "user_id": "uuid",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "role": "learner",
      "is_active": true,
      "created_at": "2025-10-01T08:00:00Z",
      "last_login_at": "2025-10-24T10:00:00Z"
    }
  ],
  "pagination": {...}
}
```

---

#### GET /v1/admin/metrics/overview

Get admin dashboard overview metrics (Decision #66).

**Auth:** Required (admin or super_admin)

**Response:** `200 OK`
```json
{
  "users": {
    "total": 1250,
    "active": 1100,
    "new_this_month": 85
  },
  "revenue": {
    "mrr": 54947.50,
    "arr": 659370.00,
    "total_revenue_this_month": 4995.00
  },
  "engagement": {
    "daily_active_users": 420,
    "avg_session_duration_minutes": 18,
    "questions_answered_today": 3500
  },
  "courses": {
    "total_courses": 1,
    "active_courses": 1,
    "total_questions": 500
  }
}
```

---

#### GET /v1/admin/courses

List all courses (admin only).

**Auth:** Required (admin or super_admin)

**Response:** `200 OK`
```json
{
  "courses": [
    {
      "course_id": "uuid",
      "course_code": "CBAP",
      "course_name": "Certified Business Analysis Professional",
      "status": "active",
      "wizard_completed": true,
      "total_questions": 500,
      "total_chunks": 150,
      "created_at": "2025-09-01T00:00:00Z"
    }
  ]
}
```

---

#### POST /v1/admin/courses

Create new course (wizard step 1) (Decision #65).

**Auth:** Required (admin or super_admin)

**Request:**
```json
{
  "course_code": "PSM1",
  "course_name": "Professional Scrum Master I",
  "version": "v2020",
  "passing_score_percentage": 85,
  "exam_duration_minutes": 60,
  "total_questions": 80
}
```

**Response:** `201 Created`
```json
{
  "course_id": "uuid",
  "course_code": "PSM1",
  "status": "draft",
  "wizard_completed": false,
  "auto_delete_at": "2025-10-31T10:00:00Z"
}
```

**Side Effects:**
- Creates course with status='draft'
- Sets auto_delete_at to 7 days from now

---

#### POST /v1/admin/courses/{course_id}/knowledge-areas

Add knowledge areas (wizard step 2).

**Auth:** Required (admin or super_admin)

**Request:**
```json
{
  "knowledge_areas": [
    {
      "ka_code": "SCRUM_THEORY",
      "ka_name": "Scrum Theory & Principles",
      "ka_number": 1,
      "weight_percentage": 33.33,
      "description": "..."
    },
    {
      "ka_code": "SCRUM_ROLES",
      "ka_name": "Scrum Roles",
      "ka_number": 2,
      "weight_percentage": 33.33,
      "description": "..."
    },
    {
      "ka_code": "SCRUM_EVENTS",
      "ka_name": "Scrum Events",
      "ka_number": 3,
      "weight_percentage": 33.34,
      "description": "..."
    }
  ]
}
```

**Response:** `201 Created`
```json
{
  "course_id": "uuid",
  "knowledge_areas": [...],
  "total_weight": 100.00,
  "validation_passed": true
}
```

**Validation:**
- Weights must sum to 100.00% (Â±0.01 tolerance)

---

#### POST /v1/admin/courses/{course_id}/questions/bulk

Bulk upload questions (wizard step 4).

**Auth:** Required (admin or super_admin)

**Content-Type:** multipart/form-data

**Request:**
- `file`: CSV or JSON file with questions

**CSV Format:**
```csv
ka_code,question_text,choice_a,choice_b,choice_c,choice_d,correct_answer,difficulty,explanation
SCRUM_THEORY,"What is...","Option A","Option B","Option C","Option D",B,0.5,"Because..."
```

**Response:** `201 Created`
```json
{
  "course_id": "uuid",
  "questions_imported": 200,
  "questions_failed": 0,
  "validation_summary": {
    "total_questions": 200,
    "questions_per_ka": {
      "SCRUM_THEORY": 67,
      "SCRUM_ROLES": 66,
      "SCRUM_EVENTS": 67
    },
    "difficulty_distribution": {
      "easy": 60,
      "medium": 80,
      "hard": 60
    }
  }
}
```

---

#### POST /v1/admin/courses/{course_id}/publish

Publish course (wizard final step).

**Auth:** Required (admin or super_admin)

**Response:** `200 OK`
```json
{
  "course_id": "uuid",
  "status": "active",
  "wizard_completed": true,
  "validation": {
    "min_questions_met": true,
    "min_chunks_met": true,
    "ka_weights_valid": true,
    "ready_for_learners": true
  }
}
```

**Validation:**
- Must have >= min_questions_required (200)
- Must have >= min_chunks_required (50)
- All KA weights sum to 100%

**Side Effects:**
- Sets status='active'
- Clears auto_delete_at
- Makes course visible to learners

---

#### GET /v1/admin/metrics/revenue

Get detailed revenue metrics (Decision #66).

**Auth:** Required (admin or super_admin)

**Query Parameters:**
- `start_date`: ISO 8601 date
- `end_date`: ISO 8601 date
- `granularity`: 'day' | 'week' | 'month' (default: 'day')

**Response:** `200 OK`
```json
{
  "summary": {
    "total_revenue": 54947.50,
    "mrr": 54947.50,
    "arr": 659370.00,
    "avg_revenue_per_user": 49.50,
    "churn_rate": 2.5,
    "ltv": 594.00
  },
  "time_series": [
    {
      "date": "2025-10-20",
      "revenue": 1847.50,
      "new_subscriptions": 5,
      "canceled_subscriptions": 1,
      "refunds": 0
    }
  ],
  "by_plan": [
    {
      "plan_name": "CBAP Monthly",
      "active_subscriptions": 800,
      "mrr": 39992.00,
      "churn_rate": 2.3
    }
  ]
}
```

**Note:** Uses queries from TDDoc_AdminDashboard_FinancialQueries.md

---

#### POST /v1/admin/bootstrap

Bootstrap initial admin account (Decision #79).

**Auth:** None (special bootstrap endpoint)

**Security:** 
- Only works if no admin users exist
- Requires bootstrap token from environment
- Creates super_admin with must_change_password=true

**Request:**
```json
{
  "bootstrap_token": "SECRET_BOOTSTRAP_TOKEN",
  "email": "admin@learnr.com",
  "first_name": "Admin",
  "last_name": "User",
  "temporary_password": "ChangeMe123!"
}
```

**Response:** `201 Created`
```json
{
  "user_id": "uuid",
  "email": "admin@learnr.com",
  "role": "super_admin",
  "must_change_password": true,
  "message": "Admin account created. You must change your password on first login."
}
```

**Errors:**
- `400`: Admins already exist
- `403`: Invalid bootstrap token

---

#### GET /v1/admin/content/review

List content chunks pending review (Decision #76, #81).

**Auth:** Required (admin or super_admin)

**Query Parameters:**
- `review_status`: Filter by status (pending/approved/rejected)
- `source_verified`: Filter by source verification
- `page`, `per_page`: Pagination

**Response:** `200 OK`
```json
{
  "data": [
    {
      "chunk_id": "uuid",
      "content_title": "Understanding Stakeholder Analysis",
      "content_text": "Stakeholder analysis is...",
      "ka_name": "Business Analysis Planning and Monitoring",
      "source_document": "BABOK v3",
      "page_reference": "pp. 45-47",
      "review_status": "pending",
      "expert_reviewed": false,
      "source_verified": false,
      "created_at": "2025-10-30T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 45,
    "total_pages": 3
  }
}
```

---

#### PATCH /v1/admin/content/{chunk_id}/review

Update content review status (Decision #76).

**Auth:** Required (admin or super_admin)

**Request:**
```json
{
  "review_status": "approved",
  "expert_reviewed": true,
  "source_verified": true,
  "is_active": true,
  "review_notes": "Verified against BABOK v3"
}
```

**Response:** `200 OK`
```json
{
  "chunk_id": "uuid",
  "review_status": "approved",
  "expert_reviewed": true,
  "source_verified": true,
  "is_active": true,
  "updated_at": "2025-10-30T10:00:00Z"
}
```

---

#### GET /v1/admin/content/quality-metrics

Get content quality metrics (Decision #76, #82).

**Auth:** Required (admin or super_admin)

**Query Parameters:**
- `ka_id`: Filter by knowledge area
- `time_period`: Last 7/30/90 days

**Response:** `200 OK`
```json
{
  "overall": {
    "total_chunks": 150,
    "active_chunks": 142,
    "pending_review": 8,
    "avg_helpfulness_score": 0.87,
    "low_quality_chunks": 3
  },
  "by_knowledge_area": [
    {
      "ka_name": "Business Analysis Planning and Monitoring",
      "total_chunks": 25,
      "avg_helpfulness": 0.91,
      "chunks_flagged": 0
    }
  ],
  "flagged_content": [
    {
      "chunk_id": "uuid",
      "content_title": "Risk Management Basics",
      "helpfulness_score": 0.42,
      "negative_feedback_count": 8,
      "requires_review": true
    }
  ]
}
```

---

#### POST /v1/admin/content/feedback

Submit expert feedback on content (Decision #76).

**Auth:** Required (admin or super_admin)

**Request:**
```json
{
  "chunk_id": "uuid",
  "was_helpful": true,
  "feedback_text": "Clear explanation of stakeholder matrix",
  "expert_rating": 4
}
```

**Response:** `201 Created`
```json
{
  "feedback_id": "uuid",
  "chunk_id": "uuid",
  "was_helpful": true,
  "created_at": "2025-10-30T10:00:00Z"
}
```

---

#### GET /v1/admin/financial/mrr

Get Monthly Recurring Revenue metrics (Decision #66).

**Auth:** Required (super_admin only)

**Query Parameters:**
- `months`: Number of months to return (default: 12, max: 36)

**Response:** `200 OK`
```json
{
  "current_mrr": 39000.00,
  "previous_mrr": 35000.00,
  "mrr_growth_percentage": 11.43,
  "mrr_growth_amount": 4000.00,
  "trend": [
    {
      "month": "2025-10",
      "mrr": 39000.00,
      "active_subscriptions": 1000,
      "new_subscriptions": 120,
      "churned_subscriptions": 17
    },
    {
      "month": "2025-09",
      "mrr": 35000.00,
      "active_subscriptions": 897,
      "new_subscriptions": 95,
      "churned_subscriptions": 12
    }
  ]
}
```

---

#### GET /v1/admin/financial/revenue

Get detailed revenue analytics (Decision #66).

**Auth:** Required (super_admin only)

**Query Parameters:**
- `period`: daily | monthly | yearly
- `start_date`: Start date (ISO format, YYYY-MM-DD)
- `end_date`: End date (ISO format, YYYY-MM-DD)

**Response:** `200 OK`
```json
{
  "period": "monthly",
  "start_date": "2025-01-01",
  "end_date": "2025-10-31",
  "gross_revenue": 125000.00,
  "net_revenue": 115000.00,
  "refunds": 5000.00,
  "chargebacks": 500.00,
  "processing_fees": 4500.00,
  "refund_rate": 4.0,
  "chargeback_rate": 0.4,
  "revenue_by_course": [
    {
      "course_code": "CBAP",
      "course_name": "Certified Business Analysis Professional",
      "gross_revenue": 125000.00,
      "net_revenue": 115000.00,
      "active_subscriptions": 1000,
      "avg_revenue_per_user": 115.00
    }
  ],
  "revenue_by_plan": [
    {
      "plan_name": "CBAP Monthly Standard",
      "subscriptions": 600,
      "gross_revenue": 29940.00,
      "churn_rate": 5.2
    },
    {
      "plan_name": "CBAP Monthly Pro",
      "subscriptions": 400,
      "gross_revenue": 39960.00,
      "churn_rate": 3.1
    }
  ]
}
```

---

#### GET /v1/admin/financial/churn

Get churn metrics and analysis (Decision #66).

**Auth:** Required (super_admin only)

**Query Parameters:**
- `period`: monthly | quarterly
- `months`: Number of months to analyze (default: 6)

**Response:** `200 OK`
```json
{
  "current_month": {
    "churn_rate": 5.2,
    "churned_count": 52,
    "retained_count": 948,
    "total_active_start": 1000
  },
  "trend": [
    {
      "month": "2025-10",
      "churn_rate": 5.2,
      "churned_count": 52
    },
    {
      "month": "2025-09",
      "churn_rate": 4.8,
      "churned_count": 43
    }
  ],
  "cancellation_reasons": [
    {
      "reason": "too_expensive",
      "count": 20,
      "percentage": 38.5
    },
    {
      "reason": "passed_exam",
      "count": 15,
      "percentage": 28.8,
      "is_success": true
    },
    {
      "reason": "content_quality",
      "count": 10,
      "percentage": 19.2
    },
    {
      "reason": "not_enough_time",
      "count": 7,
      "percentage": 13.5
    }
  ],
  "cohort_analysis": [
    {
      "cohort_month": "2025-01",
      "initial_size": 150,
      "retained_after_1_month": 142,
      "retained_after_3_months": 128,
      "retained_after_6_months": 115
    }
  ]
}
```

---

#### GET /v1/admin/security/ip-allowlist

List IP addresses on allowlist (Decision #56).

**Auth:** Required (super_admin only)

**Query Parameters:**
- `is_active`: Filter by active status
- `page`, `per_page`: Pagination

**Response:** `200 OK`
```json
{
  "data": [
    {
      "allowlist_id": "uuid",
      "ip_address": "192.168.1.100",
      "description": "Office network - Toronto HQ",
      "added_by": "uuid",
      "added_by_email": "admin@learnr.com",
      "is_active": true,
      "created_at": "2025-10-01T08:00:00Z",
      "updated_at": "2025-10-01T08:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 5,
    "total_pages": 1
  }
}
```

---

#### POST /v1/admin/security/ip-allowlist

Add IP address to allowlist (Decision #56).

**Auth:** Required (super_admin only)

**Request:**
```json
{
  "ip_address": "192.168.1.100",
  "description": "Office network - Toronto HQ"
}
```

**Response:** `201 Created`
```json
{
  "allowlist_id": "uuid",
  "ip_address": "192.168.1.100",
  "description": "Office network - Toronto HQ",
  "added_by": "uuid",
  "is_active": true,
  "created_at": "2025-10-30T10:00:00Z"
}
```

**Errors:**
- `400`: Invalid IP address format
- `409`: IP address already in allowlist

---

#### DELETE /v1/admin/security/ip-allowlist/{allowlist_id}

Remove IP from allowlist (Decision #56).

**Auth:** Required (super_admin only)

**Response:** `204 No Content`

**Errors:**
- `404`: Allowlist entry not found

---

#### GET /v1/admin/security/failed-logins

Get failed login attempts (Decision #52).

**Auth:** Required (super_admin only)

**Query Parameters:**
- `hours`: Time window in hours (default: 24)
- `ip_address`: Filter by specific IP
- `email`: Filter by email
- `is_blocked`: Filter by blocked status

**Response:** `200 OK`
```json
{
  "summary": {
    "total_attempts": 147,
    "unique_ips": 23,
    "blocked_ips": 3,
    "attempts_last_hour": 8
  },
  "attempts": [
    {
      "attempt_id": "uuid",
      "email": "user@example.com",
      "ip_address": "203.0.113.42",
      "attempted_at": "2025-10-30T14:35:22Z",
      "user_agent": "Mozilla/5.0...",
      "is_blocked": true,
      "blocked_until": "2025-10-30T15:35:22Z"
    }
  ],
  "top_targeted_accounts": [
    {
      "email": "admin@learnr.com",
      "attempt_count": 45,
      "unique_ips": 12
    }
  ]
}
```

---

### 11. Webhooks

#### POST /v1/webhooks/stripe

Stripe webhook endpoint (Decision #66).

**Auth:** Stripe signature verification

**Headers:**
- `Stripe-Signature`: Webhook signature

**Request:** (example: subscription created)
```json
{
  "type": "customer.subscription.created",
  "data": {
    "object": {
      "id": "sub_xxx",
      "customer": "cus_xxx",
      "status": "active",
      "current_period_start": 1698765432,
      "current_period_end": 1701357432
    }
  }
}
```

**Response:** `200 OK`

**Supported Events:**
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_succeeded`
- `invoice.payment_failed`
- `charge.refunded`
- `charge.dispute.created`

**Side Effects:**
- Updates subscriptions table
- Creates payment records
- Creates revenue_events
- Sends user notifications

---

## Testing Guidance

### Unit Tests

Test each endpoint with:
1. **Valid requests:** Assert 200/201 response + correct data
2. **Invalid requests:** Assert 400/422 + error messages
3. **Unauthorized:** Assert 401 (no token or invalid token)
4. **Forbidden:** Assert 403 (wrong role)
5. **Not found:** Assert 404 (invalid resource ID)
6. **Rate limiting:** Assert 429 after limit exceeded

### Example Test

```python
# Test: POST /v1/sessions/practice - valid request
def test_create_practice_session_success():
    # Arrange
    token = login_as_user("user@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    body = {"question_count": 10, "focus_ka_id": "uuid"}
    
    # Act
    response = client.post("/v1/sessions/practice", json=body, headers=headers)
    
    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["session_type"] == "practice"
    assert len(data["questions"]) == 10
    assert "session_id" in data

# Test: POST /v1/sessions/practice - unauthorized
def test_create_practice_session_unauthorized():
    body = {"question_count": 10}
    response = client.post("/v1/sessions/practice", json=body)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"

# Test: POST /v1/sessions/practice - invalid data
def test_create_practice_session_invalid_count():
    token = login_as_user("user@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    body = {"question_count": 500}  # Too many
    
    response = client.post("/v1/sessions/practice", json=body, headers=headers)
    assert response.status_code == 422
    assert "question_count" in response.json()["error"]["details"]
```

---

## API Documentation

FastAPI automatically generates:
- **OpenAPI 3.0 Schema:** `/openapi.json`
- **Swagger UI:** `/docs`
- **ReDoc:** `/redoc`

---

## Next Steps

After this document is approved:
1. âœ… Database Schema (Complete - v1.3.1)
2. âœ… Data Models (Complete - v1.0)
3. ðŸ”„ API Endpoints (This Document - In Progress)
4. â³ Algorithm Specifications (TDDoc_Algorithms.md)
5. â³ Write Tests (using TDDocs as spec)
6. â³ Implement Code (TDD red-green-refactor)

---

**Status:** PRODUCTION READY  
**Version:** 1.0  
**Completion:** 100%

**Key Design Decisions Implemented:**
- âœ… RESTful API design
- âœ… JWT authentication (Decision #53)
- âœ… Role-based authorization (learner, admin, super_admin)
- âœ… Pydantic validation (all requests/responses)
- âœ… Rate limiting (Decision #52)
- âœ… Pagination for list endpoints
- âœ… Stripe webhook integration (Decision #66)
- âœ… Admin course wizard (Decision #65)
- âœ… Spaced repetition API (Decision #31, #32)
- âœ… Adaptive learning endpoints (Decision #3)
- âœ… Financial metrics endpoints (Decision #66)
- âœ… Comprehensive error handling
- âœ… Security-first design

**Total Endpoints:** 45+  
**Authentication:** JWT with refresh tokens  
**Rate Limit:** 100 req/min (authenticated users)  
**Documentation:** Auto-generated via FastAPI
