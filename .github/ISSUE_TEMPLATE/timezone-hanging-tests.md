---
name: Fix Timezone-Aware DateTime Comparison (8 Hanging Tests)
about: Database migration needed to resolve timezone mismatch causing test hangs
title: '[BUG] 8 Tests Hang Due to Timezone-Aware/Naive DateTime Mismatch'
labels: bug, database, tests, priority-medium
assignees: ''
---

## Problem Description

8 integration/e2e tests hang indefinitely (timeout after 2 minutes) due to timezone-aware Python datetimes being compared with timezone-naive PostgreSQL `TIMESTAMP` columns in SQL queries.

**Impact:** Tests hang, but production code functions correctly with smaller data volumes.

**Current Status:** Tests deferred, fully documented in `docs/KNOWN_ISSUES.md`

## Affected Tests

### Spaced Repetition Endpoints (2 tests)
- `tests/integration/test_reviews_endpoints.py::TestGetDueReviews::test_get_due_reviews_success`
- `tests/integration/test_reviews_endpoints.py::TestGetDueReviews::test_get_due_reviews_with_limit`

### Dashboard/Results Endpoints (4 tests)
- `tests/integration/test_dashboard_endpoints.py::TestGetRecentActivity::test_get_recent_activity_success`
- `tests/integration/test_diagnostic_endpoints.py::TestGetDiagnosticResults::test_get_results_success`
- `tests/integration/test_practice_endpoints.py::TestGetPracticeSession::test_get_practice_session_success`
- `tests/integration/test_practice_endpoints.py::TestCompletePracticeSession::test_complete_practice_success`

### E2E Journeys (2 tests)
- `tests/e2e/test_user_journey.py::TestDiagnosticToReviewJourney::test_diagnostic_to_review_flow`
- `tests/e2e/test_user_journey.py::TestMultiSessionProgressJourney::test_multi_session_progress`

## Root Cause

**Database Schema:**
```python
# app/models/spaced_repetition.py:37
next_review_at = Column(DateTime, nullable=False)  # PostgreSQL TIMESTAMP (naive)
```

**Application Code:**
```python
# app/services/spaced_repetition.py:198
now = datetime.now(timezone.utc)  # Timezone-aware datetime

# This comparison in SQL causes hanging:
db.query(SpacedRepetitionCard).filter(
    SpacedRepetitionCard.next_review_at <= now  # naive <= aware
)
```

When SQLAlchemy attempts to compare a timezone-naive database column with a timezone-aware Python datetime in a SQL query, PostgreSQL attempts timezone conversion which causes the query to hang indefinitely.

## Proposed Solution

Create an Alembic migration to convert all `DateTime` columns to `DateTime(timezone=True)` (PostgreSQL `TIMESTAMPTZ`):

```sql
-- Example migration for spaced_repetition_cards table
ALTER TABLE spaced_repetition_cards
  ALTER COLUMN next_review_at TYPE TIMESTAMP WITH TIME ZONE
  USING next_review_at AT TIME ZONE 'UTC';

ALTER TABLE spaced_repetition_cards
  ALTER COLUMN last_reviewed_at TYPE TIMESTAMP WITH TIME ZONE
  USING last_reviewed_at AT TIME ZONE 'UTC';
```

This needs to be repeated for all `DateTime` columns across all 23 tables.

## Migration Checklist

- [ ] Audit all `DateTime` columns across all 23 tables
- [ ] Create Alembic migration script
- [ ] Test migration on development database
- [ ] Update SQLAlchemy model definitions to use `DateTime(timezone=True)`
- [ ] Re-run affected tests to verify they no longer hang
- [ ] Deploy migration to staging
- [ ] Deploy migration to production (with backup)

## Affected Files

**Service Layer:**
- `app/services/spaced_repetition.py:198-207` - `get_due_cards()` function
- `app/services/spaced_repetition.py:71` - Card creation with `next_review_at`

**API Endpoints:**
- `app/api/v1/reviews.py:64-65` - Counting overdue cards
- `app/api/v1/dashboard.py` - Recent activity iterations
- `app/api/v1/diagnostic.py` - Results calculations
- `app/api/v1/practice.py` - Session management

**Database Models:**
- All models with `DateTime` columns (23 tables total)

## How to Reproduce

1. Run full test suite: `pytest tests/`
2. Tests will hang at the affected test cases
3. Tests timeout after 2 minutes

## Current Workaround

Tests can be skipped in CI using:
```bash
pytest tests/ \
  --deselect=tests/integration/test_reviews_endpoints.py::TestGetDueReviews \
  --deselect=tests/integration/test_dashboard_endpoints.py::TestGetRecentActivity \
  --deselect=tests/integration/test_diagnostic_endpoints.py::TestGetDiagnosticResults \
  --deselect=tests/integration/test_practice_endpoints.py::TestGetPracticeSession \
  --deselect=tests/integration/test_practice_endpoints.py::TestCompletePracticeSession \
  --deselect=tests/e2e/test_user_journey.py::TestDiagnosticToReviewJourney \
  --deselect=tests/e2e/test_user_journey.py::TestMultiSessionProgressJourney
```

## Additional Context

- **Test Statistics:** 259/267 passing (96.8% pass rate), 84.73% coverage
- **Documentation:** Full details in `docs/KNOWN_ISSUES.md`
- **Decision:** Deferred to database migration sprint (agreed in session 2025-11-07)
- **Priority:** Must be resolved before production deployment

## Benefits of Fix

- ✅ Eliminates timezone ambiguity
- ✅ Matches Python's `datetime.now(timezone.utc)` usage
- ✅ Prevents future timezone-related bugs
- ✅ Industry best practice for multi-timezone applications
- ✅ All 267 tests will pass (100% pass rate)

## References

- **Python datetime docs:** https://docs.python.org/3/library/datetime.html
- **PostgreSQL timezone handling:** https://www.postgresql.org/docs/current/datatype-datetime.html
- **SQLAlchemy DateTime types:** https://docs.sqlalchemy.org/en/20/core/type_basics.html#sqlalchemy.types.DateTime
- **Project documentation:** `docs/KNOWN_ISSUES.md`
