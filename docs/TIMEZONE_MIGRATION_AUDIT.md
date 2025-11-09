# Database Timezone Migration - Comprehensive Audit

**Date:** 2025-11-08
**Migration Goal:** Convert all `DateTime` columns from PostgreSQL `TIMESTAMP` (timezone-naive) to `TIMESTAMPTZ` (timezone-aware)
**Root Cause:** Timezone-aware Python datetimes (`datetime.now(timezone.utc)`) causing SQL query hangs when compared with naive database columns

---

## Executive Summary

- **Total DateTime Columns:** 70 across 25 tables
- **Model Files Affected:** 9 files in `app/models/`
- **Critical Columns:** 2 columns directly causing test hangs
- **Migration Scope:** All 70 columns must be migrated for consistency

---

## Critical Columns (Causing Test Hangs)

### 🔴 HIGH PRIORITY - Direct Cause of 8 Hanging Tests

| Table | Column | Line | File | Issue |
|-------|--------|------|------|-------|
| `spaced_repetition_cards` | `next_review_at` | 37 | `spaced_repetition.py` | **PRIMARY CULPRIT** - Queried with `<= now()` in service layer |
| `spaced_repetition_cards` | `last_reviewed_at` | 36 | `spaced_repetition.py` | Used in SR algorithm calculations |

**Impact:** These 2 columns are directly referenced in:
- `app/services/spaced_repetition.py:198-207` - `get_due_cards()` function
- `app/api/v1/reviews.py:64-65` - Counting overdue cards

---

## Complete Column Inventory by File

### 1. app/models/user.py (5 columns, 2 tables)

#### Table: `users`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 1 | `created_at` | 53 | DateTime | NOT NULL | `func.now()` | Audit timestamp |
| 2 | `updated_at` | 54 | DateTime | NOT NULL | `func.now()` | Auto-update on change |
| 3 | `last_login_at` | 55 | DateTime | NULL | - | Last login tracking |

#### Table: `user_profiles`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 4 | `created_at` | 156 | DateTime | NOT NULL | `func.now()` | Audit timestamp |
| 5 | `updated_at` | 157 | DateTime | NOT NULL | `func.now()` | Auto-update on change |

---

### 2. app/models/course.py (6 columns, 3 tables)

#### Table: `courses`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 6 | `created_at` | 48 | DateTime | NOT NULL | `func.now()` | Audit timestamp |
| 7 | `updated_at` | 49 | DateTime | NOT NULL | `func.now()` | Auto-update on change |
| 8 | `auto_delete_at` | 52 | DateTime | NULL | - | Draft cleanup (7 days) |

#### Table: `knowledge_areas`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 9 | `created_at` | 98 | DateTime | NOT NULL | `func.now()` | Audit timestamp |
| 10 | `updated_at` | 99 | DateTime | NOT NULL | `func.now()` | Auto-update on change |

#### Table: `domains`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 11 | `created_at` | 138 | DateTime | NOT NULL | `func.now()` | Audit timestamp |
| 12 | `updated_at` | 139 | DateTime | NOT NULL | `func.now()` | Auto-update on change |

---

### 3. app/models/question.py (4 columns, 2 tables)

#### Table: `questions`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 13 | `created_at` | 42 | DateTime | NOT NULL | `func.now()` | Audit timestamp |
| 14 | `updated_at` | 43 | DateTime | NOT NULL | `func.now()` | Auto-update on change |

#### Table: `answer_choices`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 15 | `created_at` | 86 | DateTime | NOT NULL | `func.now()` | Audit timestamp |
| 16 | `updated_at` | 87 | DateTime | NOT NULL | `func.now()` | Auto-update on change |

---

### 4. app/models/learning.py (10 columns, 4 tables)

#### Table: `sessions`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 17 | `started_at` | 32 | DateTime | NOT NULL | `func.now()` | Session start time |
| 18 | `completed_at` | 33 | DateTime | NULL | - | Session completion time |
| 19 | `created_at` | 45 | DateTime | NOT NULL | `func.now()` | Audit timestamp |
| 20 | `updated_at` | 46 | DateTime | NOT NULL | `func.now()` | Auto-update on change |

#### Table: `question_attempts`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 21 | `attempted_at` | 103 | DateTime | NOT NULL | `func.now()` | Question attempt time |

#### Table: `user_competency`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 22 | `last_updated_at` | 148 | DateTime | NOT NULL | `func.now()` | Competency update time |
| 23 | `created_at` | 149 | DateTime | NOT NULL | `func.now()` | Audit timestamp |

#### Table: `reading_consumed`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 24 | `started_reading_at` | 181 | DateTime | NOT NULL | `func.now()` | Reading start time |
| 25 | `finished_reading_at` | 182 | DateTime | NULL | - | Reading completion time |
| 26 | `created_at` | 190 | DateTime | NOT NULL | `func.now()` | Audit timestamp |

---

### 5. app/models/spaced_repetition.py (4 columns, 1 table) ⚠️ CRITICAL

#### Table: `spaced_repetition_cards`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 27 | `last_reviewed_at` | 36 | DateTime | NULL | - | 🔴 **SR algorithm** |
| 28 | `next_review_at` | 37 | DateTime | NOT NULL | - | 🔴 **PRIMARY CULPRIT** - Causes hangs |
| 29 | `created_at` | 46 | DateTime | NOT NULL | `func.now()` | Audit timestamp |
| 30 | `updated_at` | 47 | DateTime | NOT NULL | `func.now()` | Auto-update on change |

---

### 6. app/models/financial.py (28 columns, 8 tables)

#### Table: `subscription_plans`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 31 | `created_at` | 44 | DateTime | NOT NULL | `func.now()` | Audit timestamp |
| 32 | `updated_at` | 45 | DateTime | NOT NULL | `func.now()` | Auto-update on change |

#### Table: `subscriptions`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 33 | `current_period_start` | 80 | DateTime | NOT NULL | - | Billing period start |
| 34 | `current_period_end` | 81 | DateTime | NOT NULL | - | Billing period end |
| 35 | `started_at` | 85 | DateTime | NOT NULL | `func.now()` | Subscription start |
| 36 | `canceled_at` | 86 | DateTime | NULL | - | Cancellation timestamp |
| 37 | `ended_at` | 87 | DateTime | NULL | - | Subscription end |
| 38 | `trial_start` | 88 | DateTime | NULL | - | Trial period start |
| 39 | `trial_end` | 89 | DateTime | NULL | - | Trial period end |
| 40 | `created_at` | 91 | DateTime | NOT NULL | `func.now()` | Audit timestamp |
| 41 | `updated_at` | 92 | DateTime | NOT NULL | `func.now()` | Auto-update on change |

#### Table: `payments`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 42 | `paid_at` | 144 | DateTime | NULL | - | Payment timestamp |
| 43 | `created_at` | 145 | DateTime | NOT NULL | `func.now()` | Audit timestamp |
| 44 | `updated_at` | 146 | DateTime | NOT NULL | `func.now()` | Auto-update on change |

#### Table: `refunds`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 45 | `refunded_at` | 186 | DateTime | NULL | - | Refund timestamp |
| 46 | `created_at` | 187 | DateTime | NOT NULL | `func.now()` | Audit timestamp |

#### Table: `chargebacks`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 47 | `evidence_due_by` | 223 | DateTime | NULL | - | Dispute deadline |
| 48 | `disputed_at` | 227 | DateTime | NOT NULL | - | Dispute timestamp |
| 49 | `resolved_at` | 228 | DateTime | NULL | - | Resolution timestamp |
| 50 | `created_at` | 229 | DateTime | NOT NULL | `func.now()` | Audit timestamp |

#### Table: `payment_methods`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 51 | `created_at` | 266 | DateTime | NOT NULL | `func.now()` | Audit timestamp |
| 52 | `updated_at` | 267 | DateTime | NOT NULL | `func.now()` | Auto-update on change |

#### Table: `invoices`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 53 | `invoice_date` | 300 | DateTime | NOT NULL | `func.now()` | Invoice creation |
| 54 | `due_date` | 301 | DateTime | NULL | - | Payment due date |
| 55 | `paid_at` | 302 | DateTime | NULL | - | Payment timestamp |
| 56 | `created_at` | 303 | DateTime | NOT NULL | `func.now()` | Audit timestamp |

#### Table: `revenue_events`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 57 | `occurred_at` | 347 | DateTime | NOT NULL | `func.now()` | Event timestamp |
| 58 | `created_at` | 348 | DateTime | NOT NULL | `func.now()` | Audit timestamp (immutable) |

---

### 7. app/models/security.py (6 columns, 2 tables)

#### Table: `security_logs`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 59 | `occurred_at` | 46 | DateTime | NOT NULL | `func.now()` | Event timestamp (immutable) |

#### Table: `rate_limit_entries`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 60 | `window_start` | 82 | DateTime | NOT NULL | `func.now()` | Rate limit window start |
| 61 | `window_end` | 83 | DateTime | NOT NULL | - | Rate limit window end |
| 62 | `blocked_until` | 87 | DateTime | NULL | - | Block expiration |
| 63 | `created_at` | 90 | DateTime | NOT NULL | `func.now()` | Audit timestamp |
| 64 | `updated_at` | 91 | DateTime | NOT NULL | `func.now()` | Auto-update on change |

---

### 8. app/models/content.py (6 columns, 3 tables)

#### Table: `content_chunks`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 65 | `created_at` | 56 | DateTime | NOT NULL | `func.now()` | Audit timestamp |
| 66 | `updated_at` | 57 | DateTime | NOT NULL | `func.now()` | Auto-update on change |

#### Table: `content_feedback`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 67 | `created_at` | 116 | DateTime | NOT NULL | `func.now()` | Audit timestamp |

#### Table: `content_efficacy`
| # | Column | Line | Type | Nullable | Default | Notes |
|---|--------|------|------|----------|---------|-------|
| 68 | `read_at` | 143 | DateTime | NOT NULL | - | Content read timestamp |
| 69 | `measured_at` | 146 | DateTime | NULL | - | Competency measurement time |
| 70 | `created_at` | 153 | DateTime | NOT NULL | `func.now()` | Audit timestamp |

---

## Migration Statistics

### By Category
| Category | Tables | DateTime Columns |
|----------|--------|------------------|
| Core (Users, Courses) | 5 | 12 |
| Content | 3 | 6 |
| Learning | 4 | 10 |
| Spaced Repetition | 1 | 4 ⚠️ |
| Financial | 8 | 28 |
| Security | 2 | 6 |
| **TOTAL** | **23** | **70** |

### By Pattern
| Pattern | Count | Examples |
|---------|-------|----------|
| Audit timestamps (`created_at`, `updated_at`) | 46 | Standard audit trail |
| Business logic timestamps | 24 | `next_review_at`, `completed_at`, `paid_at` |
| **TOTAL** | **70** | - |

---

## SQL Migration Pattern

All 70 columns will be migrated using this pattern:

```sql
-- Example: Migrating spaced_repetition_cards.next_review_at
ALTER TABLE spaced_repetition_cards
  ALTER COLUMN next_review_at TYPE TIMESTAMP WITH TIME ZONE
  USING next_review_at AT TIME ZONE 'UTC';

ALTER TABLE spaced_repetition_cards
  ALTER COLUMN last_reviewed_at TYPE TIMESTAMP WITH TIME ZONE
  USING last_reviewed_at AT TIME ZONE 'UTC';
```

**Explanation:**
- `TYPE TIMESTAMP WITH TIME ZONE` - Changes from naive TIMESTAMP to timezone-aware TIMESTAMPTZ
- `USING ... AT TIME ZONE 'UTC'` - Interprets existing naive timestamps as UTC (our application standard)

---

## SQLAlchemy Model Update Pattern

All 70 columns will be updated in model definitions:

```python
# BEFORE:
next_review_at = Column(DateTime, nullable=False)

# AFTER:
next_review_at = Column(DateTime(timezone=True), nullable=False)
```

**Files to Update:**
1. `app/models/user.py` - 5 columns
2. `app/models/course.py` - 6 columns
3. `app/models/question.py` - 4 columns
4. `app/models/learning.py` - 10 columns
5. `app/models/spaced_repetition.py` - 4 columns ⚠️
6. `app/models/financial.py` - 28 columns
7. `app/models/security.py` - 6 columns
8. `app/models/content.py` - 6 columns

---

## Verification Checklist

- [x] All 9 model files scanned
- [x] 70 DateTime columns identified
- [x] Critical columns flagged (`next_review_at`, `last_reviewed_at`)
- [x] Migration pattern documented
- [ ] Alembic migration script created (Phase 3)
- [ ] Test migration on development database (Phase 5)
- [ ] Verify 8 hanging tests pass after migration (Phase 5)

---

## Next Steps

1. **Phase 2:** Create database backups (full, schema-only, data-only)
2. **Phase 3:** Generate Alembic migration script for all 69 columns
3. **Phase 4:** Update SQLAlchemy model definitions
4. **Phase 5:** Run tests to verify fix (expect 267/267 passing)
5. **Phase 6:** Test rollback procedures
6. **Phase 7:** Update documentation

---

**Audit Completed:** 2025-11-08
**Total DateTime Columns:** 70 across 23 tables in 9 model files
**Critical Columns:** 2 (spaced_repetition_cards.next_review_at, last_reviewed_at)
**Migration Ready:** ✅ Yes
