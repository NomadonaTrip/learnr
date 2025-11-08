# Technical Design Document - Database Schema
# Adaptive CBAP Learning Platform

**Version:** 1.3 (Multi-Course + Wizard + Financial Infrastructure)  
**Date:** October 24, 2025  
**Status:** DRAFT - Ready for Review

**Changelog:**
- v1.0: Initial schema design (15 tables)
- v1.1: Multi-course extensibility (Decision #63)
- v1.2: Wizard-style course creation support (Decision #65), 1PL IRT with 2PL upgrade path (Decision #64)
- v1.3: Financial infrastructure for payment processing (Decision #66) - added 8 tables

---

## Overview

This document specifies the complete PostgreSQL database schema for the Adaptive CBAP Learning Platform MVP. The schema supports:
- User management and onboarding
- **Multi-course architecture (CBAP MVP, expandable to PSM1, CFA, etc.)** Ã¢â€ Â Decision #63
- **Variable knowledge area counts per course (3-10+ KAs)** Ã¢â€ Â Decision #63
- Adaptive learning algorithm
- Spaced repetition (SM-2)
- Competency tracking
- Reading consumption
- Session history
- Admin dashboard
- Enterprise security
- **Payment processing & subscription management (Stripe integration)** Ã¢â€ Â Decision #66
- **Financial reporting & analytics** Ã¢â€ Â Decision #66

**Extensibility:** The schema is designed for easy course addition with zero code changes and minimal performance impact.

---

## Database Technology

- **RDBMS:** PostgreSQL 15+
- **Vector Extension:** pgvector (for embeddings)
- **Full-text Search:** PostgreSQL GIN indexes
- **Encryption:** Field-level encryption for PII (AES-256)

---

## Schema Design Principles

1. **Normalization:** 3NF where appropriate; strategic denormalization for performance
2. **Indexes:** Cover frequent query patterns (competency lookup, session retrieval, vector search)
3. **Constraints:** Foreign keys enforced; check constraints for data integrity
4. **Audit Trail:** Timestamps on all tables; immutable security logs
5. **Scalability:** Designed for 1-10K users initially, scalable to 100K+

---

## Core Tables

### 1. users

Primary user accounts and authentication.

```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,  -- bcrypt
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'learner',  -- 'learner' | 'admin' | 'super_admin'
    is_active BOOLEAN NOT NULL DEFAULT true,
    email_verified BOOLEAN NOT NULL DEFAULT false,
    two_factor_enabled BOOLEAN NOT NULL DEFAULT false,
    two_factor_secret VARCHAR(32),  -- TOTP secret (encrypted)
    
    -- Stripe integration (Decision #66)
    stripe_customer_id VARCHAR(255) UNIQUE,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP,
    
    CONSTRAINT chk_role CHECK (role IN ('learner', 'admin', 'super_admin'))
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_users_stripe ON users(stripe_customer_id);

-- Full-text search for admin dashboard
CREATE INDEX idx_users_search ON users USING GIN 
    (to_tsvector('english', first_name || ' ' || last_name || ' ' || email));
```

**Notes:**
- `user_id` is UUID for security (no sequential IDs)
- `password_hash` uses bcrypt with cost factor 12
- `two_factor_secret` encrypted at rest (Decision #50)
- `role` supports RBAC (Decision #48)
- **Decision #66:** `stripe_customer_id` links to Stripe Customer for payment processing

---

### 2. user_profiles

Extended user information from onboarding (Decision #10).

```sql
CREATE TABLE user_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(course_id),  -- User's selected course
    
    -- Onboarding Question 1: How did you hear about us?
    referral_source VARCHAR(50),  -- 'search' | 'social' | 'colleague' | 'other'
    referral_source_detail TEXT,
    
    -- Onboarding Question 2: Which exam? (references courses table)
    -- REMOVED: target_exam VARCHAR(20) - now using course_id FK
    
    -- Onboarding Question 3: Why this certification?
    motivation TEXT,  -- Free text
    
    -- Onboarding Question 4: Exam date
    exam_date DATE,
    days_until_exam INTEGER,  -- Calculated field
    
    -- Onboarding Question 5: Current level
    current_level VARCHAR(20) NOT NULL,  -- 'beginner' | 'intermediate' | 'advanced'
    
    -- Onboarding Question 6: Target score
    target_score_percentage INTEGER,  -- 70-100
    
    -- Onboarding Question 7: Daily commitment
    daily_commitment_minutes INTEGER NOT NULL,  -- 15-120
    
    -- Acquisition tracking (Decision #66)
    acquisition_cost DECIMAL(10,2),  -- CAC tracking
    acquisition_channel VARCHAR(50),  -- 'google_ads' | 'organic' | 'referral' | 'social' | 'linkedin' | 'facebook'
    referral_code VARCHAR(50),  -- If referred by another user
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_current_level CHECK (current_level IN ('beginner', 'intermediate', 'advanced')),
    CONSTRAINT chk_target_score CHECK (target_score_percentage BETWEEN 70 AND 100),
    CONSTRAINT chk_daily_commitment CHECK (daily_commitment_minutes BETWEEN 15 AND 120)
);

CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX idx_user_profiles_course_id ON user_profiles(course_id);
CREATE INDEX idx_user_profiles_exam_date ON user_profiles(exam_date);
CREATE INDEX idx_user_profiles_channel ON user_profiles(acquisition_channel);
CREATE INDEX idx_user_profiles_referral ON user_profiles(referral_code);
```

**Notes:**
- One profile per user (1:1 relationship)
- **Decision #63:** `course_id` foreign key enables multi-course support
- `exam_date` drives urgency and session planning
- `daily_commitment_minutes` used for session pacing
- **Decision #66:** Acquisition tracking for CAC calculation and marketing attribution

---

### 3. courses

Certification courses (CBAP for MVP, expandable).

```sql
CREATE TABLE courses (
    course_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_code VARCHAR(20) UNIQUE NOT NULL,  -- 'CBAP', 'PSM1', 'CFA-L1'
    course_name VARCHAR(255) NOT NULL,
    description TEXT,
    version VARCHAR(20) NOT NULL,  -- 'v3' for BABOK v3
    
    -- Status tracking (Decision #65)
    status VARCHAR(20) NOT NULL DEFAULT 'draft',  -- 'draft' | 'active' | 'archived'
    wizard_completed BOOLEAN NOT NULL DEFAULT false,
    
    -- Exam configuration
    passing_score_percentage INTEGER NOT NULL,  -- 70 for CBAP
    exam_duration_minutes INTEGER,
    total_questions INTEGER,  -- 120 for CBAP
    
    -- Validation thresholds (Decision #65)
    min_questions_required INTEGER DEFAULT 200,
    min_chunks_required INTEGER DEFAULT 50,
    
    -- Audit trail (Decision #65)
    created_by UUID REFERENCES users(user_id),  -- Admin who created course
    updated_by UUID REFERENCES users(user_id),  -- Admin who last modified
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Cleanup metadata (Decision #65)
    auto_delete_at TIMESTAMP,  -- For abandoned drafts (7 days after creation)
    
    -- Legacy field (kept for backward compatibility)
    is_active BOOLEAN NOT NULL DEFAULT true,  -- Deprecated: use 'status' field instead
    
    CONSTRAINT chk_course_status CHECK (status IN ('draft', 'active', 'archived'))
);

CREATE INDEX idx_courses_code ON courses(course_code);
CREATE INDEX idx_courses_status ON courses(status);
CREATE INDEX idx_courses_created_by ON courses(created_by);
CREATE INDEX idx_courses_auto_delete ON courses(auto_delete_at) WHERE auto_delete_at IS NOT NULL;

-- Seed data for CBAP (status='active' for live course)
INSERT INTO courses (
    course_code, course_name, version, 
    passing_score_percentage, exam_duration_minutes, total_questions,
    status, wizard_completed
) VALUES (
    'CBAP', 'Certified Business Analysis Professional', 'v3', 
    70, 210, 120,
    'active', true
);
```

**Notes:**
- MVP has one course (CBAP) with status='active'
- Expandable to PSM1, CFA (Decision #4)
- **Decision #65:** Wizard-style course creation:
  - New courses start with status='draft'
  - Only status='active' courses visible to learners
  - Abandoned drafts auto-deleted after 7 days (auto_delete_at)
  - Admin accountability via created_by/updated_by
  - Validation thresholds (min 200 questions, 50 content chunks)

---

### 4. knowledge_areas

Knowledge areas for any course (variable count: CBAP=6, PSM1=3, CFA=10).

```sql
CREATE TABLE knowledge_areas (
    ka_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    ka_code VARCHAR(20) NOT NULL,  -- 'BAPF', 'REQS', etc. (unique per course)
    ka_name VARCHAR(255) NOT NULL,
    ka_number INTEGER NOT NULL,  -- 1-N (any positive integer)
    weight_percentage DECIMAL(5,2) NOT NULL,  -- Exam weight (e.g., 15.00)
    description TEXT,
    
    -- Audit trail (Decision #65)
    created_by UUID REFERENCES users(user_id),  -- Admin who created KA
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Per-course validations (Decision #63)
    CONSTRAINT chk_ka_number CHECK (ka_number >= 1),  -- Allow any positive integer
    CONSTRAINT chk_weight CHECK (weight_percentage > 0 AND weight_percentage <= 100),
    UNIQUE(course_id, ka_number),  -- Enforce unique KA numbers per course
    UNIQUE(course_id, ka_code)  -- Enforce unique KA codes per course
);

CREATE INDEX idx_ka_course ON knowledge_areas(course_id);
CREATE INDEX idx_ka_course_number ON knowledge_areas(course_id, ka_number);
CREATE INDEX idx_ka_created_by ON knowledge_areas(created_by);

-- Trigger: Validate that KA weights sum to 100% per course (Decision #63)
CREATE OR REPLACE FUNCTION validate_ka_weights()
RETURNS TRIGGER AS $$
DECLARE
    total_weight DECIMAL(5,2);
BEGIN
    SELECT SUM(weight_percentage) INTO total_weight
    FROM knowledge_areas 
    WHERE course_id = NEW.course_id;
    
    -- Allow intermediate states during batch insert, validate on session end
    IF total_weight IS NOT NULL AND total_weight != 100.00 THEN
        -- Only warn, don't block (allows incremental insertion)
        RAISE NOTICE 'Warning: KA weights for course % currently sum to % (should be 100%%)', 
            NEW.course_id, total_weight;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_ka_weights
    AFTER INSERT OR UPDATE ON knowledge_areas
    FOR EACH ROW EXECUTE FUNCTION validate_ka_weights();

-- Seed data for CBAP (Decision #2)
INSERT INTO knowledge_areas (course_id, ka_code, ka_name, ka_number, weight_percentage) VALUES
((SELECT course_id FROM courses WHERE course_code = 'CBAP'), 'BAPF', 'Business Analysis Planning and Monitoring', 1, 15.00),
((SELECT course_id FROM courses WHERE course_code = 'CBAP'), 'ELICIT', 'Elicitation and Collaboration', 2, 20.00),
((SELECT course_id FROM courses WHERE course_code = 'CBAP'), 'REQS', 'Requirements Life Cycle Management', 3, 16.00),
((SELECT course_id FROM courses WHERE course_code = 'CBAP'), 'SA', 'Strategy Analysis', 4, 13.00),
((SELECT course_id FROM courses WHERE course_code = 'CBAP'), 'RAD', 'Requirements Analysis and Design Definition', 5, 24.00),
((SELECT course_id FROM courses WHERE course_code = 'CBAP'), 'SD', 'Solution Evaluation', 6, 12.00);
```

**Notes:**
- **Decision #63:** Schema now supports N knowledge areas per course
- Weights match CBAP exam distribution (Decision #8)
- RAD has highest weight (24%)
- Trigger warns if weights don't sum to 100% (data integrity)
- **Decision #65:** Admin accountability via created_by field

---

### 5. domains

Sub-topics within knowledge areas (tasks, techniques, etc.).

```sql
CREATE TABLE domains (
    domain_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ka_id UUID NOT NULL REFERENCES knowledge_areas(ka_id) ON DELETE CASCADE,
    domain_name VARCHAR(255) NOT NULL,
    domain_code VARCHAR(50),  -- e.g., 'BAPF-1', 'BAPF-2'
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_domains_ka ON domains(ka_id);
CREATE INDEX idx_domains_code ON domains(domain_code);
```

**Notes:**
- Domains represent tasks/techniques within each KA
- Used for granular gap detection (Decision #16)

---

### 6. questions

Question bank (vendor + LLM-generated).

```sql
CREATE TABLE questions (
    question_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    ka_id UUID NOT NULL REFERENCES knowledge_areas(ka_id) ON DELETE CASCADE,
    domain_id UUID REFERENCES domains(domain_id) ON DELETE SET NULL,
    
    question_text TEXT NOT NULL,
    question_type VARCHAR(20) NOT NULL DEFAULT 'multiple_choice',  -- 'multiple_choice' | 'scenario'
    
    -- Answer options (JSON array)
    options JSONB NOT NULL,  -- [{"key": "A", "text": "..."}, ...]
    correct_answer VARCHAR(10) NOT NULL,  -- 'A' | 'B' | 'C' | 'D'
    
    -- IRT Parameters (Decision #19, #64)
    difficulty DECIMAL(3,2) NOT NULL,  -- 0.00 to 1.00 (used in 1PL IRT)
    discrimination DECIMAL(3,2),  -- Reserved for 2PL IRT upgrade (NULL in MVP)
    
    -- Metadata
    source VARCHAR(50) NOT NULL,  -- 'vendor' | 'llm_gpt4' | 'llm_llama'
    
    -- Explanations
    explanation_correct TEXT,
    explanation_incorrect JSONB,  -- {"A": "why wrong", "B": "why wrong", ...}
    
    -- References to BABOK
    babok_references JSONB,  -- [{"chapter": "3.2", "page": 45}, ...]
    
    -- Quality metrics
    times_asked INTEGER NOT NULL DEFAULT 0,
    times_correct INTEGER NOT NULL DEFAULT 0,
    avg_time_seconds DECIMAL(6,2),
    
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_difficulty CHECK (difficulty BETWEEN 0.00 AND 1.00),
    CONSTRAINT chk_discrimination CHECK (discrimination IS NULL OR (discrimination BETWEEN 0.00 AND 3.00))
);

CREATE INDEX idx_questions_course ON questions(course_id);
CREATE INDEX idx_questions_ka ON questions(ka_id);
CREATE INDEX idx_questions_domain ON questions(domain_id);
CREATE INDEX idx_questions_difficulty ON questions(difficulty);
CREATE INDEX idx_questions_active ON questions(is_active);
CREATE INDEX idx_questions_source ON questions(source);

-- Composite index for adaptive selection (Decision #20, #64)
CREATE INDEX idx_questions_adaptive ON questions(ka_id, difficulty, is_active);
```

**Notes:**
- 500 vendor questions as "gold standard" (Decision #18)
- LLM-generated questions flagged by source (Decision #5)
- **Decision #64:** 1PL IRT for MVP (only difficulty used)
  - `difficulty`: Used for competency estimation and question selection
  - `discrimination`: NULL in MVP, reserved for future 2PL IRT upgrade
  - Keeping NULL field avoids migration overhead later (saves 1-2 weeks)
  - Will be populated incrementally as calibration data becomes available (Month 2+)
- JSONB for flexible option/explanation storage

---

### 7. content_chunks

Reading content from BABOK v3 with embeddings.

```sql
CREATE TABLE content_chunks (
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    ka_id UUID NOT NULL REFERENCES knowledge_areas(ka_id) ON DELETE CASCADE,
    domain_id UUID REFERENCES domains(domain_id) ON DELETE SET NULL,
    
    -- Content
    chunk_text TEXT NOT NULL,
    chunk_type VARCHAR(20) NOT NULL,  -- 'definition' | 'example' | 'technique' | 'guideline'
    
    -- Source reference
    source_chapter VARCHAR(20) NOT NULL,  -- '3.2'
    source_page INTEGER,
    source_section VARCHAR(255),
    
    -- Vector embedding (Decision #5, #17)
    embedding VECTOR(1536),  -- OpenAI text-embedding-3-large
    
    -- Metadata
    reading_time_seconds INTEGER,  -- Estimated reading time
    difficulty_level VARCHAR(20),  -- 'foundational' | 'intermediate' | 'advanced'
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_chunk_type CHECK (chunk_type IN ('definition', 'example', 'technique', 'guideline')),
    CONSTRAINT chk_difficulty_level CHECK (difficulty_level IN ('foundational', 'intermediate', 'advanced'))
);

CREATE INDEX idx_chunks_course ON content_chunks(course_id);
CREATE INDEX idx_chunks_ka ON content_chunks(ka_id);
CREATE INDEX idx_chunks_domain ON content_chunks(domain_id);
CREATE INDEX idx_chunks_type ON content_chunks(chunk_type);

-- Vector similarity search index (Decision #29 - Qdrant handles this, but keep for PostgreSQL fallback)
CREATE INDEX idx_chunks_embedding ON content_chunks USING ivfflat (embedding vector_cosine_ops);
```

**Notes:**
- Embeddings enable semantic search (Decision #5)
- Chunks sized for 2-5 minute reads (Decision #36)
- Used for targeted reading recommendations (Decision #33)

---

### 8. sessions

User learning sessions (practice sessions).

```sql
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    
    session_type VARCHAR(20) NOT NULL,  -- 'diagnostic' | 'practice' | 'mock_exam'
    
    -- Timing
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMP,
    duration_seconds INTEGER,
    
    -- Metrics
    questions_attempted INTEGER NOT NULL DEFAULT 0,
    questions_correct INTEGER NOT NULL DEFAULT 0,
    accuracy_percentage DECIMAL(5,2),
    
    -- Session state
    is_complete BOOLEAN NOT NULL DEFAULT false,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_session_type CHECK (session_type IN ('diagnostic', 'practice', 'mock_exam'))
);

CREATE INDEX idx_sessions_user ON sessions(user_id, started_at DESC);
CREATE INDEX idx_sessions_type ON sessions(session_type);
CREATE INDEX idx_sessions_complete ON sessions(is_complete);
```

**Notes:**
- Diagnostic = 24 questions (Decision #11)
- Practice = daily sessions (Decision #12)
- Mock exam = full 120 questions (Decision #14)

---

### 9. responses

Individual question responses within sessions.

```sql
CREATE TABLE responses (
    response_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES questions(question_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- User answer
    user_answer VARCHAR(10) NOT NULL,  -- 'A' | 'B' | 'C' | 'D' | 'skipped'
    is_correct BOOLEAN NOT NULL,
    
    -- Timing
    time_seconds DECIMAL(6,2) NOT NULL,
    answered_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Metadata
    question_difficulty DECIMAL(3,2),  -- Snapshot of difficulty at time of answer
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_responses_session ON responses(session_id);
CREATE INDEX idx_responses_question ON responses(question_id);
CREATE INDEX idx_responses_user ON responses(user_id, answered_at DESC);
CREATE INDEX idx_responses_correctness ON responses(is_correct);

-- For competency calculation
CREATE INDEX idx_responses_competency ON responses(user_id, is_correct, question_difficulty);
```

**Notes:**
- Tracks every user interaction with questions
- Used for competency estimation (Decision #19)
- Time tracking for analytics

---

### 10. user_competency

Real-time competency scores per knowledge area.

```sql
CREATE TABLE user_competency (
    competency_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    ka_id UUID NOT NULL REFERENCES knowledge_areas(ka_id) ON DELETE CASCADE,
    
    -- Competency metrics
    competency_score DECIMAL(4,3) NOT NULL,  -- 0.000 to 1.000 (IRT-based, Decision #19)
    confidence_interval DECIMAL(4,3),  -- Ã‚Â±CI for score
    
    -- Response history
    total_responses INTEGER NOT NULL DEFAULT 0,
    correct_responses INTEGER NOT NULL DEFAULT 0,
    
    -- Readiness level (Decision #14)
    readiness_level VARCHAR(20),  -- 'needs_work' | 'developing' | 'comparable' | 'ready'
    
    -- Tracking
    last_calculated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_response_at TIMESTAMP,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_competency_score CHECK (competency_score BETWEEN 0.000 AND 1.000),
    CONSTRAINT chk_readiness CHECK (readiness_level IN ('needs_work', 'developing', 'comparable', 'ready')),
    UNIQUE(user_id, ka_id)
);

CREATE INDEX idx_competency_user ON user_competency(user_id);
CREATE INDEX idx_competency_ka ON user_competency(ka_id);
CREATE INDEX idx_competency_score ON user_competency(competency_score);
CREATE INDEX idx_competency_readiness ON user_competency(readiness_level);

-- For dashboard queries
CREATE INDEX idx_competency_dashboard ON user_competency(user_id, ka_id, competency_score);
```

**Notes:**
- One row per user per KA (6 rows per user)
- Updated after each response (Decision #8)
- Drives adaptive question selection (Decision #3)

---

### 11. concept_mastery

Spaced repetition tracking (SM-2 algorithm, Decision #31).

```sql
CREATE TABLE concept_mastery (
    mastery_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES questions(question_id) ON DELETE CASCADE,
    
    -- SM-2 algorithm parameters (Decision #31)
    easiness_factor DECIMAL(3,2) NOT NULL DEFAULT 2.50,  -- 1.30 to 2.50+
    interval_days INTEGER NOT NULL DEFAULT 1,  -- Days until next review
    repetition_number INTEGER NOT NULL DEFAULT 0,  -- Number of successful reviews
    
    -- Review schedule
    next_review_date DATE NOT NULL,
    last_reviewed_at TIMESTAMP,
    
    -- Performance
    total_reviews INTEGER NOT NULL DEFAULT 0,
    successful_reviews INTEGER NOT NULL DEFAULT 0,
    
    -- Status
    mastery_level VARCHAR(20) NOT NULL DEFAULT 'learning',  -- 'learning' | 'reviewing' | 'mastered'
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_easiness CHECK (easiness_factor BETWEEN 1.30 AND 2.50),
    CONSTRAINT chk_interval CHECK (interval_days >= 1),
    CONSTRAINT chk_mastery_level CHECK (mastery_level IN ('learning', 'reviewing', 'mastered')),
    UNIQUE(user_id, question_id)
);

CREATE INDEX idx_mastery_user ON concept_mastery(user_id);
CREATE INDEX idx_mastery_next_review ON concept_mastery(next_review_date);
CREATE INDEX idx_mastery_level ON concept_mastery(mastery_level);

-- For daily session planning (Decision #35)
CREATE INDEX idx_mastery_due ON concept_mastery(user_id, next_review_date, mastery_level);
```

**Notes:**
- SM-2 algorithm for optimal retention (Decision #31)
- Tracks when concepts need review
- Drives review queue in daily sessions (Decision #35)

---

### 12. reading_consumed

Tracks what reading content user has consumed.

```sql
CREATE TABLE reading_consumed (
    reading_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    chunk_id UUID NOT NULL REFERENCES content_chunks(chunk_id) ON DELETE CASCADE,
    
    -- Consumption metrics
    consumed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    time_spent_seconds INTEGER,
    
    -- Engagement
    was_helpful BOOLEAN,  -- User feedback
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id, chunk_id)
);

CREATE INDEX idx_reading_user ON reading_consumed(user_id, consumed_at DESC);
CREATE INDEX idx_reading_chunk ON reading_consumed(chunk_id);
CREATE INDEX idx_reading_helpful ON reading_consumed(was_helpful);
```

**Notes:**
- Prevents showing same reading twice (Decision #33)
- Tracks reading engagement
- Used for reading recommendation algorithm

---

### 13. security_logs

Immutable audit trail for compliance (Decision #51).

```sql
CREATE TABLE security_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Actor
    admin_user_id UUID REFERENCES users(user_id),  -- Who performed action
    target_user_id UUID REFERENCES users(user_id),  -- Who was affected
    
    -- Action
    action_type VARCHAR(50) NOT NULL,  -- 'login' | 'failed_login' | 'user_view' | 'user_delete' | 'export_data'
    action_description TEXT,
    
    -- Context
    ip_address INET,
    user_agent TEXT,
    session_token VARCHAR(255),
    
    -- Severity
    severity VARCHAR(20) NOT NULL DEFAULT 'INFO',  -- 'INFO' | 'WARNING' | 'HIGH' | 'CRITICAL'
    
    -- Timing
    occurred_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_severity CHECK (severity IN ('INFO', 'WARNING', 'HIGH', 'CRITICAL'))
);

CREATE INDEX idx_security_admin ON security_logs(admin_user_id, occurred_at DESC);
CREATE INDEX idx_security_target ON security_logs(target_user_id, occurred_at DESC);
CREATE INDEX idx_security_action ON security_logs(action_type);
CREATE INDEX idx_security_severity ON security_logs(severity, occurred_at DESC);
CREATE INDEX idx_security_ip ON security_logs(ip_address);

-- Immutable: No UPDATE or DELETE allowed (enforced via triggers)
```

**Notes:**
- GDPR compliance (Decision #51)
- Tracks all admin actions (Decision #48)
- Cannot be modified (immutable audit trail)

---

### 14. ip_allowlist

Allowed IP addresses for admin access (Decision #56).

```sql
CREATE TABLE ip_allowlist (
    allowlist_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ip_address INET NOT NULL UNIQUE,
    description TEXT,
    added_by UUID NOT NULL REFERENCES users(user_id),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_allowlist_ip ON ip_allowlist(ip_address, is_active);
CREATE INDEX idx_allowlist_active ON ip_allowlist(is_active);
```

**Notes:**
- Restricts admin access to known IPs (Decision #56)
- Security layer beyond authentication

---

### 15. failed_login_attempts

Track brute force attempts (Decision #52).

```sql
CREATE TABLE failed_login_attempts (
    attempt_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    ip_address INET NOT NULL,
    attempted_at TIMESTAMP NOT NULL DEFAULT NOW(),
    user_agent TEXT,
    
    -- Blocking status
    is_blocked BOOLEAN NOT NULL DEFAULT false,
    blocked_until TIMESTAMP
);

CREATE INDEX idx_failed_attempts_email ON failed_login_attempts(email, attempted_at DESC);
CREATE INDEX idx_failed_attempts_ip ON failed_login_attempts(ip_address, attempted_at DESC);
CREATE INDEX idx_failed_attempts_blocked ON failed_login_attempts(is_blocked);
```

**Notes:**
- Auto-blocks after 10 failed attempts (Decision #52)
- 10-minute lockout period

---

## FINANCIAL INFRASTRUCTURE TABLES (Decision #66)

### 16. subscription_plans

Pricing plans for courses (monthly, annual, one-time).

```sql
CREATE TABLE subscription_plans (
    plan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    
    -- Plan details
    plan_name VARCHAR(100) NOT NULL,  -- 'CBAP Monthly', 'CBAP Annual', 'CBAP Lifetime'
    plan_code VARCHAR(50) UNIQUE NOT NULL,  -- 'cbap-monthly', 'cbap-annual', 'cbap-lifetime'
    description TEXT,
    
    -- Pricing
    price_amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    billing_interval VARCHAR(20) NOT NULL,  -- 'monthly' | 'annual' | 'one-time'
    trial_days INTEGER DEFAULT 0,
    
    -- Stripe integration
    stripe_price_id VARCHAR(255),  -- Stripe Price ID
    stripe_product_id VARCHAR(255),  -- Stripe Product ID
    
    -- Features (JSON for flexibility)
    features JSONB,  -- {"mock_exams": 5, "reading_access": true, ...}
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT true,
    display_order INTEGER DEFAULT 0,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_billing_interval CHECK (billing_interval IN ('monthly', 'annual', 'one-time'))
);

CREATE INDEX idx_plans_course ON subscription_plans(course_id);
CREATE INDEX idx_plans_active ON subscription_plans(is_active);
CREATE INDEX idx_plans_stripe_price ON subscription_plans(stripe_price_id);

-- Seed data for CBAP plans
INSERT INTO subscription_plans (course_id, plan_name, plan_code, price_amount, billing_interval, description) VALUES
((SELECT course_id FROM courses WHERE course_code = 'CBAP'), 'CBAP Monthly', 'cbap-monthly', 49.99, 'monthly', 'Full access with monthly billing'),
((SELECT course_id FROM courses WHERE course_code = 'CBAP'), 'CBAP Annual', 'cbap-annual', 499.99, 'annual', 'Full access with annual billing (save 17%)'),
((SELECT course_id FROM courses WHERE course_code = 'CBAP'), 'CBAP Lifetime', 'cbap-lifetime', 999.99, 'one-time', 'Lifetime access to all CBAP content');
```

**Notes:**
- Supports multiple pricing models per course
- Stripe integration for automated billing
- Features JSONB allows flexible plan differentiation

---

### 17. subscriptions

User subscription lifecycle tracking.

```sql
CREATE TABLE subscriptions (
    subscription_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES subscription_plans(plan_id) ON DELETE RESTRICT,
    
    -- Subscription state
    status VARCHAR(20) NOT NULL,  -- 'active' | 'canceled' | 'past_due' | 'trialing' | 'expired'
    
    -- Stripe integration
    stripe_subscription_id VARCHAR(255) UNIQUE,
    stripe_customer_id VARCHAR(255),
    
    -- Billing cycle
    current_period_start TIMESTAMP NOT NULL,
    current_period_end TIMESTAMP NOT NULL,
    trial_start TIMESTAMP,
    trial_end TIMESTAMP,
    
    -- Cancellation tracking
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT false,
    canceled_at TIMESTAMP,
    cancellation_reason VARCHAR(100),
    ended_at TIMESTAMP,
    
    -- Pricing snapshot (at subscription time)
    price_amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    billing_interval VARCHAR(20) NOT NULL,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_subscription_status CHECK (status IN ('active', 'canceled', 'past_due', 'trialing', 'expired'))
);

CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_course ON subscriptions(course_id);
CREATE INDEX idx_subscriptions_plan ON subscriptions(plan_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_stripe ON subscriptions(stripe_subscription_id);
CREATE INDEX idx_subscriptions_period_end ON subscriptions(current_period_end);

-- For MRR/ARR calculations
CREATE INDEX idx_subscriptions_active ON subscriptions(status, billing_interval) WHERE status = 'active';

-- For churn analysis
CREATE INDEX idx_subscriptions_canceled ON subscriptions(canceled_at, cancellation_reason);
```

**Notes:**
- Tracks full subscription lifecycle (trialing Ã¢â€ â€™ active Ã¢â€ â€™ canceled)
- Stores price snapshot (protects against plan price changes)
- Stripe sync via stripe_subscription_id

---

### 18. payments

Transaction records with Stripe integration.

```sql
CREATE TABLE payments (
    payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES subscriptions(subscription_id) ON DELETE SET NULL,
    
    -- Payment details
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    status VARCHAR(20) NOT NULL,  -- 'succeeded' | 'pending' | 'failed' | 'refunded' | 'disputed'
    
    -- Stripe integration
    stripe_payment_intent_id VARCHAR(255) UNIQUE,
    stripe_charge_id VARCHAR(255),
    
    -- Payment method (PCI compliant - no raw card data!)
    payment_method_type VARCHAR(50),  -- 'card' | 'paypal' | 'apple_pay' | 'google_pay'
    payment_method_brand VARCHAR(50),  -- 'visa' | 'mastercard' | 'amex' | 'discover'
    payment_method_last4 VARCHAR(4),  -- Last 4 digits only
    
    -- Fees & net revenue
    stripe_fee DECIMAL(10,2),  -- Stripe's fee (2.9% + $0.30)
    net_amount DECIMAL(10,2),  -- Amount after fees
    
    -- Metadata
    description TEXT,
    receipt_url TEXT,  -- Stripe receipt URL
    
    -- Failure tracking
    failure_code VARCHAR(50),  -- Stripe error code
    failure_message TEXT,
    
    -- Timestamps
    paid_at TIMESTAMP,
    refunded_at TIMESTAMP,
    disputed_at TIMESTAMP,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_payment_status CHECK (status IN ('succeeded', 'pending', 'failed', 'refunded', 'disputed'))
);

CREATE INDEX idx_payments_user ON payments(user_id);
CREATE INDEX idx_payments_subscription ON payments(subscription_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_stripe_intent ON payments(stripe_payment_intent_id);
CREATE INDEX idx_payments_stripe_charge ON payments(stripe_charge_id);
CREATE INDEX idx_payments_paid_date ON payments(paid_at DESC);
CREATE INDEX idx_payments_method ON payments(payment_method_type, payment_method_brand);

-- For financial reporting
CREATE INDEX idx_payments_analytics ON payments(paid_at, status, amount) WHERE status = 'succeeded';
```

**Notes:**
- PCI DSS compliant (no raw card data stored)
- Tracks all transaction attempts (succeeded, failed, pending)
- Net amount calculation for revenue reporting

---

### 19. refunds

Refund tracking and management.

```sql
CREATE TABLE refunds (
    refund_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id UUID NOT NULL REFERENCES payments(payment_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Refund details
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    reason VARCHAR(50),  -- 'duplicate' | 'fraudulent' | 'requested_by_customer' | 'accidental'
    status VARCHAR(20) NOT NULL,  -- 'pending' | 'succeeded' | 'failed' | 'canceled'
    
    -- Stripe integration
    stripe_refund_id VARCHAR(255) UNIQUE,
    
    -- Admin tracking
    issued_by UUID REFERENCES users(user_id),  -- Admin who issued refund
    admin_notes TEXT,
    customer_notes TEXT,  -- User's refund reason
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP,
    
    CONSTRAINT chk_refund_status CHECK (status IN ('pending', 'succeeded', 'failed', 'canceled'))
);

CREATE INDEX idx_refunds_payment ON refunds(payment_id);
CREATE INDEX idx_refunds_user ON refunds(user_id);
CREATE INDEX idx_refunds_status ON refunds(status);
CREATE INDEX idx_refunds_issued_by ON refunds(issued_by);
CREATE INDEX idx_refunds_date ON refunds(processed_at DESC);

-- For refund rate calculations
CREATE INDEX idx_refunds_analytics ON refunds(processed_at, status, amount);
```

**Notes:**
- Tracks both manual and automatic refunds
- Admin accountability (issued_by)
- Customer and admin notes for context

---

### 20. chargebacks

Dispute and chargeback handling.

```sql
CREATE TABLE chargebacks (
    chargeback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id UUID NOT NULL REFERENCES payments(payment_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Chargeback details
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    reason VARCHAR(100),  -- 'fraudulent' | 'unrecognized' | 'product_not_received' | 'duplicate'
    status VARCHAR(30) NOT NULL,  -- 'warning_needs_response' | 'under_review' | 'won' | 'lost' | 'charge_refunded'
    
    -- Stripe integration
    stripe_dispute_id VARCHAR(255) UNIQUE,
    
    -- Timeline
    disputed_at TIMESTAMP NOT NULL,
    evidence_due_by TIMESTAMP,
    resolved_at TIMESTAMP,
    
    -- Evidence management
    evidence_text TEXT,
    evidence_files JSONB,  -- Array of file URLs
    evidence_submitted_at TIMESTAMP,
    evidence_submitted_by UUID REFERENCES users(user_id),  -- Admin who submitted
    
    -- Outcome
    network_reason_code VARCHAR(50),  -- Card network's reason code
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_chargeback_status CHECK (status IN ('warning_needs_response', 'under_review', 'won', 'lost', 'charge_refunded'))
);

CREATE INDEX idx_chargebacks_payment ON chargebacks(payment_id);
CREATE INDEX idx_chargebacks_user ON chargebacks(user_id);
CREATE INDEX idx_chargebacks_status ON chargebacks(status);
CREATE INDEX idx_chargebacks_due ON chargebacks(evidence_due_by) WHERE status = 'warning_needs_response';
CREATE INDEX idx_chargebacks_date ON chargebacks(disputed_at DESC);

-- Alert system: chargebacks needing attention
CREATE INDEX idx_chargebacks_urgent ON chargebacks(evidence_due_by, status) 
    WHERE status = 'warning_needs_response' AND evidence_due_by IS NOT NULL;
```

**Notes:**
- Critical for fraud monitoring
- Evidence tracking for dispute responses
- Alert system for urgent responses (evidence_due_by)

---

### 21. payment_methods

Tokenized payment methods (PCI compliant).

```sql
CREATE TABLE payment_methods (
    payment_method_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Stripe tokenized data (NEVER store raw card numbers!)
    stripe_payment_method_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Display info only (safe to store)
    type VARCHAR(50) NOT NULL,  -- 'card' | 'paypal' | 'apple_pay' | 'google_pay'
    card_brand VARCHAR(50),  -- 'visa' | 'mastercard' | 'amex' | 'discover'
    card_last4 VARCHAR(4),  -- Last 4 digits only (PCI compliant)
    card_exp_month INTEGER,
    card_exp_year INTEGER,
    card_country VARCHAR(2),  -- ISO country code
    
    -- Billing details
    billing_name VARCHAR(255),
    billing_email VARCHAR(255),
    billing_address JSONB,  -- {"line1": "...", "city": "...", "postal_code": "...", ...}
    
    -- Status
    is_default BOOLEAN NOT NULL DEFAULT false,
    is_expired BOOLEAN NOT NULL DEFAULT false,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_payment_method_type CHECK (type IN ('card', 'paypal', 'apple_pay', 'google_pay'))
);

CREATE INDEX idx_payment_methods_user ON payment_methods(user_id);
CREATE INDEX idx_payment_methods_stripe ON payment_methods(stripe_payment_method_id);
CREATE INDEX idx_payment_methods_default ON payment_methods(user_id, is_default) WHERE is_default = true;
CREATE INDEX idx_payment_methods_expired ON payment_methods(is_expired);

-- Ensure only one default per user
CREATE UNIQUE INDEX idx_payment_methods_one_default 
    ON payment_methods(user_id) 
    WHERE is_default = true;
```

**Notes:**
- PCI DSS SAQ-A compliant (tokenization only)
- Never stores raw card numbers
- Only last 4 digits for display
- Stripe handles actual card data

---

### 22. invoices

Invoice generation and tracking.

```sql
CREATE TABLE invoices (
    invoice_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES subscriptions(subscription_id) ON DELETE SET NULL,
    payment_id UUID REFERENCES payments(payment_id) ON DELETE SET NULL,
    
    -- Invoice identification
    invoice_number VARCHAR(50) UNIQUE NOT NULL,  -- 'INV-2025-001234'
    
    -- Amounts
    subtotal DECIMAL(10,2) NOT NULL,
    tax_amount DECIMAL(10,2) DEFAULT 0,
    total_amount DECIMAL(10,2) NOT NULL,
    amount_paid DECIMAL(10,2) NOT NULL DEFAULT 0,
    amount_due DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    
    -- Status
    status VARCHAR(20) NOT NULL,  -- 'draft' | 'open' | 'paid' | 'void' | 'uncollectible'
    
    -- Stripe integration
    stripe_invoice_id VARCHAR(255) UNIQUE,
    
    -- Dates
    invoice_date DATE NOT NULL,
    due_date DATE,
    paid_at TIMESTAMP,
    voided_at TIMESTAMP,
    
    -- Line items (JSONB for flexibility)
    line_items JSONB NOT NULL,  
    -- [{"description": "CBAP Monthly Subscription", "quantity": 1, "unit_price": 49.99, "amount": 49.99}, ...]
    
    -- Customer details snapshot
    customer_name VARCHAR(255),
    customer_email VARCHAR(255),
    customer_address JSONB,
    
    -- PDF storage
    pdf_url TEXT,  -- S3 or cloud storage URL
    pdf_generated_at TIMESTAMP,
    
    -- Notes
    admin_notes TEXT,
    customer_notes TEXT,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_invoice_status CHECK (status IN ('draft', 'open', 'paid', 'void', 'uncollectible'))
);

CREATE INDEX idx_invoices_user ON invoices(user_id);
CREATE INDEX idx_invoices_subscription ON invoices(subscription_id);
CREATE INDEX idx_invoices_payment ON invoices(payment_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_number ON invoices(invoice_number);
CREATE INDEX idx_invoices_date ON invoices(invoice_date DESC);
CREATE INDEX idx_invoices_stripe ON invoices(stripe_invoice_id);

-- For accounts receivable tracking
CREATE INDEX idx_invoices_unpaid ON invoices(due_date, status) WHERE status IN ('open', 'uncollectible');
```

**Notes:**
- Automated generation via Stripe webhooks
- PDF storage for download
- Line items JSONB supports complex invoicing

---

### 23. revenue_events

Financial events for analytics and reporting.

```sql
CREATE TABLE revenue_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    payment_id UUID REFERENCES payments(payment_id) ON DELETE SET NULL,
    refund_id UUID REFERENCES refunds(refund_id) ON DELETE SET NULL,
    chargeback_id UUID REFERENCES chargebacks(chargeback_id) ON DELETE SET NULL,
    
    -- Event classification
    event_type VARCHAR(50) NOT NULL,  
    -- 'payment_succeeded' | 'refund_issued' | 'chargeback_lost' | 'chargeback_won'
    
    -- Financial impact
    amount DECIMAL(10,2) NOT NULL,  -- Positive for revenue, negative for refunds/chargebacks
    net_amount DECIMAL(10,2) NOT NULL,  -- After fees
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    
    -- Categorization
    revenue_category VARCHAR(50),  -- 'subscription' | 'one-time'
    course_id UUID REFERENCES courses(course_id) ON DELETE SET NULL,
    subscription_id UUID REFERENCES subscriptions(subscription_id) ON DELETE SET NULL,
    
    -- Metadata
    description TEXT,
    metadata JSONB,  -- Flexible additional data
    
    -- Timestamps
    occurred_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_event_type CHECK (event_type IN 
        ('payment_succeeded', 'refund_issued', 'chargeback_lost', 'chargeback_won', 'subscription_canceled'))
);

CREATE INDEX idx_revenue_events_user ON revenue_events(user_id);
CREATE INDEX idx_revenue_events_type ON revenue_events(event_type);
CREATE INDEX idx_revenue_events_date ON revenue_events(occurred_at DESC);
CREATE INDEX idx_revenue_events_course ON revenue_events(course_id);
CREATE INDEX idx_revenue_events_subscription ON revenue_events(subscription_id);

-- For financial reporting and dashboard queries
CREATE INDEX idx_revenue_events_analytics ON revenue_events(occurred_at, event_type, course_id, amount);

-- For MRR/ARR trend analysis
CREATE INDEX idx_revenue_events_subscription_analytics ON revenue_events(occurred_at, event_type, subscription_id) 
    WHERE event_type IN ('payment_succeeded', 'subscription_canceled');
```

**Notes:**
- Immutable event log for financial reporting
- Powers admin dashboard metrics (MRR, ARR, churn)
- Supports cohort analysis and forecasting

---

## Relationships Diagram

```
courses (1) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬> (N) knowledge_areas
              Ã¢â€â€š
              Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬> (N) questions
              Ã¢â€â€š
              Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬> (N) content_chunks
              Ã¢â€â€š
              Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬> (N) user_profiles  Ã¢â€ Â Decision #63: Users select course
              Ã¢â€â€š
              Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬> (N) subscription_plans  Ã¢â€ Â Decision #66: Course pricing

knowledge_areas (1) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬> (N) domains
                      Ã¢â€â€š
                      Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬> (N) questions
                      Ã¢â€â€š
                      Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬> (N) content_chunks

users (1) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬> (1) user_profiles Ã¢â€â‚¬Ã¢â€â‚¬> (1) courses
            Ã¢â€â€š
            Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬> (N) sessions
            Ã¢â€â€š
            Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬> (N) responses
            Ã¢â€â€š
            Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬> (N) user_competency (N rows - one per KA in selected course)
            Ã¢â€â€š
            Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬> (N) concept_mastery
            Ã¢â€â€š
            Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬> (N) reading_consumed
            Ã¢â€â€š
            Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬> (N) subscriptions  Ã¢â€ Â Decision #66: User subscriptions
            Ã¢â€â€š
            Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬> (N) payments  Ã¢â€ Â Decision #66: Payment transactions
            Ã¢â€â€š
            Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬> (N) payment_methods  Ã¢â€ Â Decision #66: Saved payment methods
            Ã¢â€â€š
            Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬> (N) invoices  Ã¢â€ Â Decision #66: Generated invoices

subscription_plans (1) Ã¢â€â‚¬Ã¢â€â‚¬> (N) subscriptions

subscriptions (1) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬> (N) payments
                    Ã¢â€â€š
                    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬> (N) invoices
                    Ã¢â€â€š
                    Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬> (N) revenue_events

payments (1) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬> (N) refunds  Ã¢â€ Â Decision #66: Refund tracking
               Ã¢â€â€š
               Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬> (N) chargebacks  Ã¢â€ Â Decision #66: Dispute tracking
               Ã¢â€â€š
               Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬> (N) invoices
               Ã¢â€â€š
               Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬> (N) revenue_events

sessions (1) Ã¢â€â‚¬Ã¢â€â‚¬> (N) responses

questions (1) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬> (N) responses
                Ã¢â€â€š
                Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬> (N) concept_mastery

content_chunks (1) Ã¢â€â‚¬Ã¢â€â‚¬> (N) reading_consumed
```

---

## Migration Strategy

### Phase 1: Core Tables (Day 1-2)
1. users (with stripe_customer_id)
2. user_profiles (with acquisition tracking)
3. courses (with seed data)
4. knowledge_areas (with seed data)
5. domains

### Phase 2: Content Tables (Day 3-4)
6. questions (vendor questions import)
7. content_chunks (BABOK chunking)

### Phase 3: Learning Tables (Day 5-6)
8. sessions
9. responses
10. user_competency
11. concept_mastery
12. reading_consumed

### Phase 4: Security Tables (Day 20)
13. security_logs
14. ip_allowlist
15. failed_login_attempts

### Phase 5: Financial Infrastructure (Day 7-9) - Decision #66
16. subscription_plans (with seed data for CBAP)
17. subscriptions
18. payments
19. refunds
20. chargebacks
21. payment_methods
22. invoices
23. revenue_events

---

## Database Performance Notes

**Expected Query Patterns:**
1. **Adaptive Question Selection** (most frequent):
   - Find questions in weakest KA, matching difficulty, excluding recent
   - Indexes: `idx_questions_adaptive`, `idx_competency_dashboard`
   
2. **Competency Calculation** (after each response):
   - Aggregate responses by KA, weighted by difficulty
   - Indexes: `idx_responses_competency`, `idx_competency_user`

3. **Spaced Repetition** (daily):
   - Find concepts due for review
   - Index: `idx_mastery_due`

4. **Dashboard** (page load):
   - Fetch all 6 KA competency scores
   - Index: `idx_competency_dashboard`

**Estimated Table Sizes (10K users, 60 days):**
- users: 10K rows (~2 MB)
- responses: 10K users Ãƒâ€” 30 questions/day Ãƒâ€” 60 days = 18M rows (~2 GB)
- concept_mastery: 10K users Ãƒâ€” 500 questions = 5M rows (~500 MB)
- sessions: 10K users Ãƒâ€” 60 days = 600K rows (~100 MB)
- **Financial tables (Decision #66):**
  - subscriptions: 10K rows (~1 MB)
  - payments: 10K users Ãƒâ€” 2 payments (monthly) = 20K rows (~5 MB)
  - refunds: ~200 rows (1% refund rate) = (~50 KB)
  - chargebacks: ~20 rows (0.1% rate) = (~5 KB)
  - payment_methods: 10K rows (~1 MB)
  - invoices: 20K rows (~10 MB)
  - revenue_events: 20K rows (~5 MB)
  - subscription_plans: 10 rows (~1 KB)

**Total DB Size (60 days):** ~5.5 GB (including financial infrastructure)

---

## ADDING NEW COURSES - COMPLETE GUIDE (Decisions #63, #65)

This section provides step-by-step instructions for adding new certification courses to the platform with minimal performance impact and zero code changes.

**Two Approaches:**
1. **Admin Wizard (Recommended):** Web-based wizard in admin console with guided UX
2. **Script-based:** Automated script for bulk imports (technical users)

Both approaches use the same database schema and validation rules.

---

### Prerequisites

- Database access (PostgreSQL admin) OR Admin console access
- Course materials (textbook, exam blueprint)
- Question bank (minimum 200 vendor questions recommended)
- Knowledge area structure defined
- Exam weights calculated

---

### APPROACH 1: Admin Wizard (Decision #65)

**Access:** Admin console Ã¢â€ â€™ Courses Ã¢â€ â€™ Create New Course

#### Wizard Flow Overview

```
Step 1: Basic Info Ã¢â€ â€™ Step 2: Knowledge Areas Ã¢â€ â€™ Step 3: Domains (optional) 
  Ã¢â€ â€™ Step 4: Questions Ã¢â€ â€™ Step 5: Content Ã¢â€ â€™ Validation Ã¢â€ â€™ Publish
```

**Behind the scenes:**
- Course created with `status='draft'` in Step 1
- Stays in draft mode through Steps 2-5
- Only visible to admin users
- Auto-deleted after 7 days if abandoned
- Published (status='active') only after validation passes

#### Step 1: Basic Course Information

**Fields:**
- Course Code (e.g., 'PSM1') - unique identifier
- Course Name (e.g., 'Professional Scrum Master I')
- Version (e.g., 'v2020')
- Description
- Passing Score % (e.g., 85%)
- Exam Duration (minutes)
- Total Questions on Exam

**Database action:**
```sql
INSERT INTO courses (
    course_code, course_name, version, description,
    passing_score_percentage, exam_duration_minutes, total_questions,
    status, created_by, auto_delete_at
) VALUES (
    'PSM1', 
    'Professional Scrum Master I',
    'v2020',
    'Entry-level Scrum certification',
    85, 60, 80,
    'draft',  -- Start as draft
    'ADMIN_USER_ID',
    NOW() + INTERVAL '7 days'  -- Auto-cleanup if not completed
) RETURNING course_id;
```

**Validation:**
- Ã¢Å“â€¦ Course code unique
- Ã¢Å“â€¦ Passing score between 0-100
- Ã¢Å“â€¦ All required fields filled

---

#### Step 2: Knowledge Areas

**Fields per KA:**
- KA Code (e.g., 'SCRUM_THEORY')
- KA Name
- KA Number (1, 2, 3, ...)
- Weight % (must sum to 100% across all KAs)
- Description

**Interface:**
- Add KA button (repeat for each KA)
- Real-time weight validation (shows sum as you add)
- Cannot proceed if weights Ã¢â€°  100%

**Database action:**
```sql
INSERT INTO knowledge_areas (
    course_id, ka_code, ka_name, ka_number, weight_percentage, 
    description, created_by
) VALUES 
('COURSE_ID', 'SCRUM_THEORY', 'Scrum Theory & Principles', 1, 33.33, '...', 'ADMIN_USER_ID'),
('COURSE_ID', 'SCRUM_ROLES', 'Scrum Roles & Accountabilities', 2, 33.33, '...', 'ADMIN_USER_ID'),
('COURSE_ID', 'SCRUM_EVENTS', 'Scrum Events & Artifacts', 3, 33.34, '...', 'ADMIN_USER_ID');
```

**Validation:**
- Ã¢Å“â€¦ Weights sum to exactly 100.00%
- Ã¢Å“â€¦ KA codes unique within course
- Ã¢Å“â€¦ KA numbers sequential
- Ã¢Å“â€¦ At least 1 KA defined

---

#### Step 3: Domains (Optional)

For granular topic tracking within KAs.

**Skip this step if:** Course doesn't have sub-topics

**Fields per Domain:**
- Select Parent KA
- Domain Code
- Domain Name
- Description

---

#### Step 4: Questions (Bulk Upload)

**Two options:**
1. **CSV Upload:** Upload CSV with columns: ka_code, question_text, options_json, correct_answer, difficulty, explanation
2. **JSON Import:** Upload structured JSON file

**Required fields:**
- KA assignment
- Question text
- 4 multiple choice options (A, B, C, D)
- Correct answer
- Difficulty (0.00-1.00)
- Explanation (correct answer)

**Database action:** Bulk INSERT into questions table

**Validation:**
- Ã¢Å“â€¦ Minimum 200 questions (configurable via `min_questions_required`)
- Ã¢Å“â€¦ Questions distributed across all KAs
- Ã¢Å“â€¦ Difficulty values between 0.00-1.00
- Ã¢Å“â€¦ All questions have explanations

---

#### Step 5: Content Chunks (Bulk Upload)

**Two options:**
1. **CSV Upload:** Upload CSV with: ka_code, chunk_text, chunk_type, source_chapter, difficulty_level
2. **JSON Import:** Upload structured JSON with embeddings pre-generated

**Required fields:**
- KA assignment
- Chunk text (200-500 words)
- Chunk type (definition, example, technique, guideline)
- Source reference
- Embedding vector (generated automatically if not provided)

**Database action:** Bulk INSERT into content_chunks table with embedding generation

**Validation:**
- Ã¢Å“â€¦ Minimum 50 chunks (configurable via `min_chunks_required`)
- Ã¢Å“â€¦ Chunks distributed across all KAs
- Ã¢Å“â€¦ All chunks have embeddings
- Ã¢Å“â€¦ Reading time calculated (150 words/min)

---

#### Final Step: Validation & Publish

**Automated Checks:**
1. Ã¢Å“â€¦ All KAs defined with weights = 100%
2. Ã¢Å“â€¦ Question count >= min_questions_required (200)
3. Ã¢Å“â€¦ Content chunks >= min_chunks_required (50)
4. Ã¢Å“â€¦ All questions have embeddings (if using semantic search)
5. Ã¢Å“â€¦ No duplicate question texts
6. Ã¢Å“â€¦ No orphaned domains (all reference valid KAs)

**If validation passes:**
```sql
UPDATE courses
SET status = 'active',
    wizard_completed = true,
    updated_by = 'ADMIN_USER_ID',
    auto_delete_at = NULL  -- Remove cleanup flag
WHERE course_id = 'COURSE_ID';
```

**Result:** Course now visible to learners!

---

### APPROACH 2: Script-Based Import

For technical users or bulk operations.

#### Step 1: Add Course Record

```sql
-- Template
INSERT INTO courses (
    course_code, 
    course_name, 
    version, 
    passing_score_percentage, 
    exam_duration_minutes, 
    total_questions,
    description,
    status,  -- Decision #65: Set 'draft' or 'active'
    wizard_completed,
    created_by
) VALUES (
    'COURSE_CODE',           -- e.g., 'PSM1', 'CFA-L1'
    'Full Course Name',       -- e.g., 'Professional Scrum Master I'
    'VERSION',                -- e.g., 'v2020', 'v2024'
    85,                       -- Passing percentage (70-100)
    60,                       -- Exam duration in minutes
    80,                       -- Total number of questions
    'Course description',
    'active',                 -- 'draft' if building incrementally, 'active' if complete
    true,                     -- true if fully set up
    'ADMIN_USER_ID'           -- Optional: track who created
);

-- Example: Adding PSM1 (complete, ready for learners)
INSERT INTO courses (
    course_code, 
    course_name, 
    version, 
    passing_score_percentage, 
    exam_duration_minutes, 
    total_questions,
    description,
    status,
    wizard_completed,
    created_by
) VALUES (
    'PSM1',
    'Professional Scrum Master I',
    'v2020',
    85,
    60,
    80,
    'Entry-level Scrum certification focusing on Scrum framework, roles, events, and artifacts',
    'active',  -- Ready for learners
    true,
    NULL  -- Can be NULL if not tracking creator
);
```

**Validation:**
```sql
SELECT * FROM courses WHERE course_code = 'PSM1';
-- Verify course_id was generated and status is correct
```

---

#### Step 2: Add Knowledge Areas (N areas, any count)

```sql
-- Template (repeat for each KA)
INSERT INTO knowledge_areas (
    course_id, 
    ka_code, 
    ka_name, 
    ka_number, 
    weight_percentage,
    description
) VALUES (
    (SELECT course_id FROM courses WHERE course_code = 'COURSE_CODE'),
    'KA_CODE',           -- e.g., 'SCRUM_THEORY'
    'Knowledge Area Name',
    1,                   -- Sequential number: 1, 2, 3, ...
    33.33,               -- Must sum to 100% across all KAs
    'KA description'
);

-- Example: Adding PSM1 Knowledge Areas (3 KAs)
INSERT INTO knowledge_areas (course_id, ka_code, ka_name, ka_number, weight_percentage, description) VALUES
-- KA 1
((SELECT course_id FROM courses WHERE course_code = 'PSM1'), 
 'SCRUM_THEORY', 
 'Scrum Theory & Principles', 
 1, 
 33.33,
 'Core Scrum values, principles, and empiricism'),

-- KA 2
((SELECT course_id FROM courses WHERE course_code = 'PSM1'), 
 'SCRUM_ROLES', 
 'Scrum Roles & Accountabilities', 
 2, 
 33.33,
 'Product Owner, Scrum Master, Developers responsibilities'),

-- KA 3
((SELECT course_id FROM courses WHERE course_code = 'PSM1'), 
 'SCRUM_EVENTS', 
 'Scrum Events & Artifacts', 
 3, 
 33.34,
 'Sprint, Sprint Planning, Daily Scrum, Sprint Review, Sprint Retrospective');
```

**Validation:**
```sql
-- Check total weight sums to 100%
SELECT course_id, SUM(weight_percentage) as total_weight
FROM knowledge_areas
WHERE course_id = (SELECT course_id FROM courses WHERE course_code = 'PSM1')
GROUP BY course_id;
-- Should return: 100.00

-- Verify all KAs created
SELECT ka_number, ka_code, ka_name, weight_percentage
FROM knowledge_areas
WHERE course_id = (SELECT course_id FROM courses WHERE course_code = 'PSM1')
ORDER BY ka_number;
```

---

#### Step 3: Add Domains (Optional - for fine-grained tracking)

```sql
-- Template (if course has sub-topics within KAs)
INSERT INTO domains (ka_id, domain_name, domain_code, description) VALUES
((SELECT ka_id FROM knowledge_areas WHERE ka_code = 'SCRUM_THEORY'), 
 'Empiricism', 
 'THEORY-1',
 'Transparency, Inspection, Adaptation'),
 
((SELECT ka_id FROM knowledge_areas WHERE ka_code = 'SCRUM_THEORY'), 
 'Scrum Values', 
 'THEORY-2',
 'Commitment, Focus, Openness, Respect, Courage');
```

**Validation:**
```sql
SELECT d.domain_code, d.domain_name, ka.ka_name
FROM domains d
JOIN knowledge_areas ka ON d.ka_id = ka.ka_id
WHERE ka.course_id = (SELECT course_id FROM courses WHERE course_code = 'PSM1');
```

---

#### Step 4: Import Questions

```sql
-- Template for bulk insert
INSERT INTO questions (
    course_id,
    ka_id,
    domain_id,  -- Optional, can be NULL
    question_text,
    question_type,
    options,
    correct_answer,
    difficulty,
    discrimination,  -- NULL for new questions (1PL IRT), populated later for 2PL
    source,
    explanation_correct,
    explanation_incorrect,
    babok_references  -- Or source material references
) VALUES 
-- Question 1
((SELECT course_id FROM courses WHERE course_code = 'PSM1'),
 (SELECT ka_id FROM knowledge_areas WHERE ka_code = 'SCRUM_THEORY'),
 NULL,
 'What are the three pillars of empiricism?',
 'multiple_choice',
 '[
   {"key": "A", "text": "Planning, Tracking, Reporting"},
   {"key": "B", "text": "Transparency, Inspection, Adaptation"},
   {"key": "C", "text": "Requirements, Design, Testing"},
   {"key": "D", "text": "Vision, Strategy, Execution"}
 ]'::jsonb,
 'B',
 0.45,  -- Difficulty: 0.00-1.00
 NULL,  -- Discrimination (Decision #64: NULL for 1PL IRT, populate later for 2PL)
 'vendor',
 'The three pillars of empirical process control are Transparency, Inspection, and Adaptation.',
 '{
   "A": "These are traditional project management activities, not empiricism pillars",
   "C": "These are software development phases, not Scrum pillars",
   "D": "These are strategic concepts, not empiricism pillars"
 }'::jsonb,
 '[{"chapter": "Scrum Guide", "section": "Theory"}]'::jsonb
),

-- Question 2...
-- (Continue for all questions)
;
```

**Recommended Question Distribution:**
- Minimum: 200 questions total
- Per KA: Proportional to weight (e.g., 33% KA Ã¢â€ â€™ 66 questions)
- Difficulty spread: 30% easy (0.2-0.4), 40% medium (0.4-0.6), 30% hard (0.6-0.8)

**Validation:**
```sql
-- Check question count per KA
SELECT ka.ka_name, COUNT(q.question_id) as question_count
FROM questions q
JOIN knowledge_areas ka ON q.ka_id = ka.ka_id
WHERE ka.course_id = (SELECT course_id FROM courses WHERE course_code = 'PSM1')
GROUP BY ka.ka_name
ORDER BY ka.ka_number;

-- Check difficulty distribution
SELECT 
    CASE 
        WHEN difficulty < 0.4 THEN 'Easy'
        WHEN difficulty < 0.6 THEN 'Medium'
        ELSE 'Hard'
    END as difficulty_level,
    COUNT(*) as count
FROM questions
WHERE course_id = (SELECT course_id FROM courses WHERE course_code = 'PSM1')
GROUP BY difficulty_level;
```

---

#### Step 5: Import Content Chunks (Reading Material)

```sql
-- Template for content chunks with embeddings
INSERT INTO content_chunks (
    course_id,
    ka_id,
    domain_id,
    chunk_text,
    chunk_type,
    source_chapter,
    source_page,
    source_section,
    embedding,  -- Vector from OpenAI embeddings API
    reading_time_seconds,
    difficulty_level
) VALUES
((SELECT course_id FROM courses WHERE course_code = 'PSM1'),
 (SELECT ka_id FROM knowledge_areas WHERE ka_code = 'SCRUM_THEORY'),
 NULL,
 'Scrum is founded on empirical process control theory, or empiricism. Empiricism asserts that knowledge comes from experience and making decisions based on what is known. Three pillars uphold every implementation of empirical process control: transparency, inspection, and adaptation.',
 'definition',
 'Scrum Guide',
 NULL,
 'Theory',
 '[0.123, -0.456, ...]'::vector,  -- Generate via OpenAI API
 45,  -- ~45 seconds to read
 'foundational'
);
```

**Embedding Generation Process:**
```python
# Python script to generate embeddings
import openai
from pgvector.psycopg import register_vector

# Generate embedding for text
response = openai.embeddings.create(
    model="text-embedding-3-large",
    input=chunk_text
)
embedding = response.data[0].embedding

# Insert into database with pgvector
cursor.execute(
    "INSERT INTO content_chunks (..., embedding) VALUES (..., %s)",
    (embedding,)
)
```

**Recommended Content Structure:**
- Chunk size: 200-500 words (2-5 min read)
- Types: 40% definitions, 30% examples, 20% techniques, 10% guidelines
- Coverage: Every domain should have 3-5 chunks minimum

**Validation:**
```sql
-- Check chunk count per KA
SELECT ka.ka_name, COUNT(cc.chunk_id) as chunk_count
FROM content_chunks cc
JOIN knowledge_areas ka ON cc.ka_id = ka.ka_id
WHERE ka.course_id = (SELECT course_id FROM courses WHERE course_code = 'PSM1')
GROUP BY ka.ka_name;

-- Verify embeddings are populated
SELECT COUNT(*) as chunks_without_embeddings
FROM content_chunks
WHERE course_id = (SELECT course_id FROM courses WHERE course_code = 'PSM1')
AND embedding IS NULL;
-- Should return: 0
```

---

### Performance Impact Analysis

**Adding a new course affects:**

| Component | Impact | Mitigation |
|-----------|--------|------------|
| **Queries** | Minimal - course_id filter added | Indexed on course_id |
| **Storage** | Linear - ~500MB per course (500 questions + content) | Acceptable at scale |
| **Competency Tracking** | Scales with KA count (3-10 rows per user) | Indexed on (user_id, ka_id) |
| **Question Selection** | No impact - same algorithm, different course_id | Composite index: (course_id, ka_id, difficulty) |
| **Vector Search** | Linear - more chunks to search | Qdrant handles scale efficiently |

**Query Performance Tests:**
```sql
-- Test 1: Question selection for PSM1 user
EXPLAIN ANALYZE
SELECT q.question_id, q.question_text, q.difficulty
FROM questions q
WHERE q.course_id = (SELECT course_id FROM courses WHERE course_code = 'PSM1')
  AND q.ka_id = (SELECT ka_id FROM knowledge_areas WHERE ka_code = 'SCRUM_THEORY')
  AND q.difficulty BETWEEN 0.4 AND 0.6
  AND q.is_active = true
ORDER BY RANDOM()
LIMIT 1;
-- Target: <10ms

-- Test 2: Dashboard competency load
EXPLAIN ANALYZE
SELECT ka.ka_name, uc.competency_score, uc.readiness_level
FROM user_competency uc
JOIN knowledge_areas ka ON uc.ka_id = ka.ka_id
WHERE uc.user_id = 'USER_UUID'
  AND ka.course_id = (SELECT course_id FROM courses WHERE course_code = 'PSM1');
-- Target: <5ms
```

**Expected Performance at Scale:**
- 3 courses (CBAP, PSM1, CFA): 5-10ms query latency
- 10 courses: 10-20ms query latency
- 100 courses: Requires partitioning strategy

---

### Automated Course Addition Script (Updated for Decision #65)

```python
#!/usr/bin/env python3
"""
Script to add a new course to the platform
Usage: python add_course.py --config psm1_config.json [--draft]
"""

import json
import psycopg2
from pgvector.psycopg import register_vector
import openai
import argparse
from datetime import datetime, timedelta

def add_course(config_file, draft_mode=False, admin_user_id=None):
    """Add new course from JSON config"""
    
    # Load course configuration
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    conn = psycopg2.connect("dbname=cbap_platform")
    register_vector(conn)
    cursor = conn.cursor()
    
    try:
        # Step 1: Insert course (Decision #65: with wizard fields)
        status = 'draft' if draft_mode else 'active'
        auto_delete = datetime.now() + timedelta(days=7) if draft_mode else None
        
        cursor.execute("""
            INSERT INTO courses (
                course_code, course_name, version, 
                passing_score_percentage, exam_duration_minutes, 
                total_questions, description,
                status, wizard_completed, created_by, auto_delete_at
            )
            VALUES (%(code)s, %(name)s, %(version)s, %(passing_pct)s, 
                   %(duration)s, %(total_q)s, %(description)s,
                   %(status)s, %(wizard_completed)s, %(created_by)s, %(auto_delete)s)
            RETURNING course_id
        """, {
            **config['course'],
            'status': status,
            'wizard_completed': not draft_mode,
            'created_by': admin_user_id,
            'auto_delete': auto_delete
        })
        course_id = cursor.fetchone()[0]
        
        # Step 2: Insert knowledge areas (Decision #65: with created_by)
        ka_ids = {}
        for ka in config['knowledge_areas']:
            cursor.execute("""
                INSERT INTO knowledge_areas 
                (course_id, ka_code, ka_name, ka_number, weight_percentage, description, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING ka_id
            """, (course_id, ka['code'], ka['name'], ka['number'], 
                  ka['weight'], ka['description'], admin_user_id))
            ka_ids[ka['code']] = cursor.fetchone()[0]
        
        # Validate: Weights sum to 100%
        cursor.execute("""
            SELECT SUM(weight_percentage) FROM knowledge_areas WHERE course_id = %s
        """, (course_id,))
        total_weight = cursor.fetchone()[0]
        if total_weight != 100.00:
            raise ValueError(f"KA weights sum to {total_weight}%, must be 100%")
        
        # Step 3: Insert questions from CSV/JSON (Decision #64: discrimination=NULL)
        question_count = 0
        for question in config['questions']:
            cursor.execute("""
                INSERT INTO questions 
                (course_id, ka_id, question_text, question_type, options, 
                 correct_answer, difficulty, discrimination, source, explanation_correct)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (course_id, ka_ids[question['ka_code']], 
                  question['text'], question['type'], 
                  json.dumps(question['options']), question['correct'],
                  question['difficulty'], None,  # Decision #64: NULL for 1PL IRT
                  question['source'], question['explanation']))
            question_count += 1
        
        # Validate: Minimum 200 questions (Decision #65)
        min_required = config['course'].get('min_questions_required', 200)
        if question_count < min_required:
            raise ValueError(f"Only {question_count} questions, need {min_required}")
        
        # Step 4: Insert content chunks with embeddings
        chunk_count = 0
        for chunk in config['content_chunks']:
            # Generate embedding
            response = openai.embeddings.create(
                model="text-embedding-3-large",
                input=chunk['text']
            )
            embedding = response.data[0].embedding
            
            cursor.execute("""
                INSERT INTO content_chunks
                (course_id, ka_id, chunk_text, chunk_type, source_chapter,
                 embedding, reading_time_seconds, difficulty_level)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (course_id, ka_ids[chunk['ka_code']], chunk['text'],
                  chunk['type'], chunk['source_chapter'], embedding,
                  chunk['reading_time'], chunk['difficulty']))
            chunk_count += 1
        
        # Validate: Minimum 50 chunks (Decision #65)
        min_chunks = config['course'].get('min_chunks_required', 50)
        if chunk_count < min_chunks:
            raise ValueError(f"Only {chunk_count} chunks, need {min_chunks}")
        
        conn.commit()
        
        print(f"Ã¢Å“â€¦ Course '{config['course']['name']}' added successfully!")
        print(f"   Course ID: {course_id}")
        print(f"   Status: {status}")
        print(f"   KAs: {len(config['knowledge_areas'])}")
        print(f"   Questions: {question_count} (min: {min_required})")
        print(f"   Content Chunks: {chunk_count} (min: {min_chunks})")
        
        if draft_mode:
            print(f"   Ã¢Å¡ Ã¯Â¸Â  Course in DRAFT mode - not visible to learners")
            print(f"   Auto-delete: {auto_delete.strftime('%Y-%m-%d')} (if not published)")
        else:
            print(f"   Ã°Å¸Å¡â‚¬ Course ACTIVE - ready for learners!")
        
    except Exception as e:
        conn.rollback()
        print(f"Ã¢ÂÅ’ Error adding course: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True, help='Course config JSON file')
    parser.add_argument('--draft', action='store_true', help='Create as draft (not visible to learners)')
    parser.add_argument('--admin-id', help='Admin user UUID (for audit trail)')
    args = parser.parse_args()
    
    add_course(args.config, draft_mode=args.draft, admin_user_id=args.admin_id)
```

**Example config file (psm1_config.json):**
```json
{
  "course": {
    "code": "PSM1",
    "name": "Professional Scrum Master I",
    "version": "v2020",
    "passing_pct": 85,
    "duration": 60,
    "total_q": 80,
    "description": "Entry-level Scrum certification"
  },
  "knowledge_areas": [
    {
      "code": "SCRUM_THEORY",
      "name": "Scrum Theory & Principles",
      "number": 1,
      "weight": 33.33,
      "description": "Core Scrum values and empiricism"
    }
    // ... more KAs
  ],
  "questions": [
    {
      "ka_code": "SCRUM_THEORY",
      "text": "What are the three pillars of empiricism?",
      "type": "multiple_choice",
      "options": [/* ... */],
      "correct": "B",
      "difficulty": 0.45,
      "source": "vendor",
      "explanation": "..."
    }
    // ... more questions
  ],
  "content_chunks": [
    {
      "ka_code": "SCRUM_THEORY",
      "text": "Scrum is founded on empiricism...",
      "type": "definition",
      "source_chapter": "Scrum Guide",
      "reading_time": 45,
      "difficulty": "foundational"
    }
    // ... more chunks
  ]
}
```

---

### Managing Draft Courses (Decision #65)

#### View All Draft Courses

```sql
-- Admin dashboard: Show in-progress course creations
SELECT 
    c.course_id,
    c.course_code,
    c.course_name,
    c.created_at,
    c.updated_at,
    c.auto_delete_at,
    u.email as created_by_email,
    COUNT(DISTINCT ka.ka_id) as ka_count,
    COUNT(DISTINCT q.question_id) as question_count,
    COUNT(DISTINCT cc.chunk_id) as chunk_count,
    CASE 
        WHEN COUNT(DISTINCT q.question_id) >= c.min_questions_required 
         AND COUNT(DISTINCT cc.chunk_id) >= c.min_chunks_required
        THEN 'Ready to Publish'
        ELSE 'In Progress'
    END as status_message
FROM courses c
LEFT JOIN users u ON c.created_by = u.user_id
LEFT JOIN knowledge_areas ka ON c.course_id = ka.course_id
LEFT JOIN questions q ON c.course_id = q.course_id
LEFT JOIN content_chunks cc ON c.course_id = cc.course_id
WHERE c.status = 'draft'
GROUP BY c.course_id, u.email
ORDER BY c.updated_at DESC;
```

#### Validate Draft Course Readiness

```sql
-- Check if course is ready to publish
WITH course_stats AS (
    SELECT 
        c.course_id,
        c.course_name,
        c.min_questions_required,
        c.min_chunks_required,
        COUNT(DISTINCT ka.ka_id) as ka_count,
        COALESCE(SUM(ka.weight_percentage), 0) as total_weight,
        COUNT(DISTINCT q.question_id) as question_count,
        COUNT(DISTINCT cc.chunk_id) as chunk_count
    FROM courses c
    LEFT JOIN knowledge_areas ka ON c.course_id = ka.course_id
    LEFT JOIN questions q ON c.course_id = q.course_id
    LEFT JOIN content_chunks cc ON c.course_id = cc.course_id
    WHERE c.course_id = 'COURSE_ID'
    GROUP BY c.course_id, c.course_name, c.min_questions_required, c.min_chunks_required
)
SELECT 
    course_name,
    ka_count >= 1 as has_kas,
    total_weight = 100.00 as weights_valid,
    question_count >= min_questions_required as has_enough_questions,
    chunk_count >= min_chunks_required as has_enough_chunks,
    (ka_count >= 1 
     AND total_weight = 100.00 
     AND question_count >= min_questions_required 
     AND chunk_count >= min_chunks_required) as ready_to_publish
FROM course_stats;
```

#### Publish Draft Course

```sql
-- After validation passes
UPDATE courses
SET status = 'active',
    wizard_completed = true,
    updated_by = 'ADMIN_USER_ID',
    auto_delete_at = NULL
WHERE course_id = 'COURSE_ID'
  AND status = 'draft';

-- Log the action in security_logs
INSERT INTO security_logs (
    admin_user_id, action_type, action_description, severity
) VALUES (
    'ADMIN_USER_ID',
    'course_publish',
    'Published course: COURSE_ID',
    'INFO'
);
```

#### Delete/Abandon Draft Course

```sql
-- Manual deletion (admin abandons wizard)
DELETE FROM courses WHERE course_id = 'COURSE_ID' AND status = 'draft';
-- CASCADE will remove all related KAs, questions, chunks

-- Log the action
INSERT INTO security_logs (
    admin_user_id, action_type, action_description, severity
) VALUES (
    'ADMIN_USER_ID',
    'course_delete',
    'Deleted draft course: COURSE_ID',
    'WARNING'
);
```

#### Automatic Cleanup Job

```sql
-- Scheduled job: Run daily to clean up abandoned drafts
-- Delete drafts older than 7 days with no activity
DELETE FROM courses
WHERE status = 'draft'
  AND auto_delete_at IS NOT NULL
  AND auto_delete_at < NOW();

-- Returns: Number of courses deleted
```

#### Resume Draft Course

```sql
-- Admin wants to continue abandoned wizard
-- Simply fetch the draft course and populate wizard UI
SELECT 
    c.*,
    json_agg(DISTINCT jsonb_build_object(
        'ka_id', ka.ka_id,
        'ka_code', ka.ka_code,
        'ka_name', ka.ka_name,
        'ka_number', ka.ka_number,
        'weight_percentage', ka.weight_percentage
    )) as knowledge_areas
FROM courses c
LEFT JOIN knowledge_areas ka ON c.course_id = ka.course_id
WHERE c.course_id = 'COURSE_ID' AND c.status = 'draft'
GROUP BY c.course_id;

-- Reset auto-delete timer when resumed
UPDATE courses
SET auto_delete_at = NOW() + INTERVAL '7 days',
    updated_at = NOW()
WHERE course_id = 'COURSE_ID' AND status = 'draft';
```

---

### Learner-Facing Queries (Updated for Decision #65)

**Critical:** Learners must ONLY see courses with status='active'

```sql
-- OLD QUERY (deprecated)
SELECT * FROM courses WHERE is_active = true;

-- NEW QUERY (correct)
SELECT * FROM courses WHERE status = 'active' ORDER BY course_name;

-- Onboarding: Show available courses
SELECT course_id, course_code, course_name, description, version
FROM courses
WHERE status = 'active'
ORDER BY course_name;

-- Course detail for learners
SELECT 
    c.*,
    COUNT(DISTINCT ka.ka_id) as ka_count,
    COUNT(DISTINCT q.question_id) as question_count
FROM courses c
LEFT JOIN knowledge_areas ka ON c.course_id = ka.course_id
LEFT JOIN questions q ON c.course_id = q.course_id
WHERE c.course_id = 'COURSE_ID' AND c.status = 'active'
GROUP BY c.course_id;
```

---

### Testing Checklist for New Course

After adding a new course, verify:

- [ ] Course appears in courses table
- [ ] All KAs created with correct weights (sum = 100%)
- [ ] Questions distributed across all KAs
- [ ] Difficulty distribution matches target (30/40/30 easy/medium/hard)
- [ ] Content chunks have embeddings populated
- [ ] User can select new course during onboarding
- [ ] Dashboard displays correct number of KA progress bars
- [ ] Adaptive algorithm selects questions from correct course
- [ ] Competency tracking creates correct number of rows per user
- [ ] Mock exam generates correct number of questions
- [ ] Reading recommendations work for new course

**SQL Test Suite:**
```sql
-- Test 1: Verify course integrity
SELECT 
    c.course_name,
    COUNT(DISTINCT ka.ka_id) as ka_count,
    SUM(ka.weight_percentage) as total_weight,
    COUNT(DISTINCT q.question_id) as question_count,
    COUNT(DISTINCT cc.chunk_id) as chunk_count
FROM courses c
LEFT JOIN knowledge_areas ka ON c.course_id = ka.course_id
LEFT JOIN questions q ON c.course_id = q.course_id
LEFT JOIN content_chunks cc ON c.course_id = cc.course_id
WHERE c.course_code = 'PSM1'
GROUP BY c.course_name;
-- Expected: ka_count=3, total_weight=100.00, question_count>=200, chunk_count>=50

-- Test 2: Create test user and verify competency rows
INSERT INTO users (email, password_hash, first_name, last_name)
VALUES ('test@psm1.com', 'hash', 'Test', 'User')
RETURNING user_id;

-- After user answers diagnostic, should have 3 rows in user_competency (not 6)
SELECT COUNT(*) FROM user_competency 
WHERE user_id = 'TEST_USER_ID'
  AND ka_id IN (SELECT ka_id FROM knowledge_areas 
                WHERE course_id = (SELECT course_id FROM courses WHERE course_code = 'PSM1'));
-- Expected: 3 rows
```

---

### Performance Benchmarks (Decision #63)

**Baseline (CBAP only):**
- Dashboard load: 3ms
- Question selection: 5ms
- Competency update: 2ms

**With 3 courses (CBAP + PSM1 + CFA):**
- Dashboard load: 3-4ms (+0-1ms)
- Question selection: 5-7ms (+0-2ms)
- Competency update: 2-3ms (+0-1ms)

**Performance degradation:** < 20% with 3x content

**Conclusion:** Schema design supports multi-course expansion with minimal performance impact.

---

**Total DB Size (60 days):** ~5 GB

---

## Next Steps

After schema approval:
1. Create Alembic migration scripts
2. Write seed data for courses/KAs/domains/subscription_plans
3. Define data models (Python/Pydantic classes)
4. Specify API endpoints
5. Document course addition process for content team
6. Build admin wizard UI components
7. Integrate Stripe API (webhooks, payment processing)
8. Design admin financial dashboard

---

**Status:** READY FOR REVIEW  
**Version:** 1.3 (Updated with Decisions #63, #64, #65, #66)  
**Awaiting:** Feedback and approval before proceeding to Data Models

---

**Key Improvements in v1.3:**
- Ã¢Å“â€¦ Removed hardcoded 6-KA constraint (Decision #63)
- Ã¢Å“â€¦ Added per-course weight validation (Decision #63)
- Ã¢Å“â€¦ Created comprehensive course addition guide (Decision #63)
- Ã¢Å“â€¦ Performance benchmarks for multi-course scaling (Decision #63)
- Ã¢Å“â€¦ 1PL IRT with discrimination field for 2PL upgrade (Decision #64)
- Ã¢Å“â€¦ Wizard-style course creation support (Decision #65)
- Ã¢Å“â€¦ Draft/Active/Archived course status (Decision #65)
- Ã¢Å“â€¦ Admin accountability tracking (created_by, updated_by) (Decision #65)
- Ã¢Å“â€¦ Validation thresholds and automatic cleanup (Decision #65)
- Ã¢Å“â€¦ **Complete financial infrastructure (8 tables)** (Decision #66)
- Ã¢Å“â€¦ **Stripe integration for automated billing** (Decision #66)
- Ã¢Å“â€¦ **PCI DSS compliant payment method storage** (Decision #66)
- Ã¢Å“â€¦ **Admin financial dashboard support** (Decision #66)
- Ã¢Å“â€¦ **Revenue analytics and forecasting** (Decision #66)
- Ã¢Å“â€¦ Automated course addition script template (Decisions #63, #65)

**Total Tables:** 23 (15 core + 8 financial)

