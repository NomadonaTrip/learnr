"""convert_datetime_to_timestamptz

Revision ID: e3f9a2b7c1d4
Revises: d58373bc5f10
Create Date: 2025-11-08 14:00:00.000000

Purpose:
    Convert all 70 DateTime columns from TIMESTAMP (timezone-naive) to
    TIMESTAMPTZ (timezone-aware) to fix timezone comparison issues
    causing 8 test hangs.

Affected Tables: 23 tables across 9 model files
Critical Fix: spaced_repetition_cards.next_review_at (primary culprit)

References:
    - docs/TIMEZONE_MIGRATION_AUDIT.md
    - docs/KNOWN_ISSUES.md
    - GitHub Issue: https://github.com/NomadonaTrip/learnr/issues/X
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3f9a2b7c1d4'
down_revision = 'd58373bc5f10'
branch_labels = None
depends_on = None


def upgrade():
    """
    Convert all DateTime columns to TIMESTAMPTZ.

    Uses 'AT TIME ZONE ''UTC''' to interpret existing naive timestamps as UTC,
    which matches our application's datetime.now(timezone.utc) usage.
    """

    # ========================================================================
    # 1. USERS TABLE (3 columns)
    # ========================================================================
    op.execute("""
        ALTER TABLE users
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE users
          ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
          USING updated_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE users
          ALTER COLUMN last_login_at TYPE TIMESTAMP WITH TIME ZONE
          USING last_login_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 2. USER_PROFILES TABLE (2 columns)
    # ========================================================================
    op.execute("""
        ALTER TABLE user_profiles
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE user_profiles
          ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
          USING updated_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 3. COURSES TABLE (3 columns)
    # ========================================================================
    op.execute("""
        ALTER TABLE courses
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE courses
          ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
          USING updated_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE courses
          ALTER COLUMN auto_delete_at TYPE TIMESTAMP WITH TIME ZONE
          USING auto_delete_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 4. KNOWLEDGE_AREAS TABLE (2 columns)
    # ========================================================================
    op.execute("""
        ALTER TABLE knowledge_areas
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE knowledge_areas
          ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
          USING updated_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 5. DOMAINS TABLE (2 columns)
    # ========================================================================
    op.execute("""
        ALTER TABLE domains
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE domains
          ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
          USING updated_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 6. QUESTIONS TABLE (2 columns)
    # ========================================================================
    op.execute("""
        ALTER TABLE questions
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE questions
          ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
          USING updated_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 7. ANSWER_CHOICES TABLE (2 columns)
    # ========================================================================
    op.execute("""
        ALTER TABLE answer_choices
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE answer_choices
          ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
          USING updated_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 8. SESSIONS TABLE (4 columns)
    # ========================================================================
    op.execute("""
        ALTER TABLE sessions
          ALTER COLUMN started_at TYPE TIMESTAMP WITH TIME ZONE
          USING started_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE sessions
          ALTER COLUMN completed_at TYPE TIMESTAMP WITH TIME ZONE
          USING completed_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE sessions
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE sessions
          ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
          USING updated_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 9. QUESTION_ATTEMPTS TABLE (1 column)
    # ========================================================================
    op.execute("""
        ALTER TABLE question_attempts
          ALTER COLUMN attempted_at TYPE TIMESTAMP WITH TIME ZONE
          USING attempted_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 10. USER_COMPETENCY TABLE (2 columns)
    # ========================================================================
    op.execute("""
        ALTER TABLE user_competency
          ALTER COLUMN last_updated_at TYPE TIMESTAMP WITH TIME ZONE
          USING last_updated_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE user_competency
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 11. READING_CONSUMED TABLE (3 columns)
    # ========================================================================
    op.execute("""
        ALTER TABLE reading_consumed
          ALTER COLUMN started_reading_at TYPE TIMESTAMP WITH TIME ZONE
          USING started_reading_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE reading_consumed
          ALTER COLUMN finished_reading_at TYPE TIMESTAMP WITH TIME ZONE
          USING finished_reading_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE reading_consumed
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 12. SPACED_REPETITION_CARDS TABLE (4 columns) ⚠️ CRITICAL
    # ========================================================================
    # PRIMARY CULPRIT: next_review_at causes 8 test hangs
    op.execute("""
        ALTER TABLE spaced_repetition_cards
          ALTER COLUMN last_reviewed_at TYPE TIMESTAMP WITH TIME ZONE
          USING last_reviewed_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE spaced_repetition_cards
          ALTER COLUMN next_review_at TYPE TIMESTAMP WITH TIME ZONE
          USING next_review_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE spaced_repetition_cards
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE spaced_repetition_cards
          ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
          USING updated_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 13. SUBSCRIPTION_PLANS TABLE (2 columns)
    # ========================================================================
    op.execute("""
        ALTER TABLE subscription_plans
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE subscription_plans
          ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
          USING updated_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 14. SUBSCRIPTIONS TABLE (9 columns)
    # ========================================================================
    op.execute("""
        ALTER TABLE subscriptions
          ALTER COLUMN current_period_start TYPE TIMESTAMP WITH TIME ZONE
          USING current_period_start AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE subscriptions
          ALTER COLUMN current_period_end TYPE TIMESTAMP WITH TIME ZONE
          USING current_period_end AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE subscriptions
          ALTER COLUMN started_at TYPE TIMESTAMP WITH TIME ZONE
          USING started_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE subscriptions
          ALTER COLUMN canceled_at TYPE TIMESTAMP WITH TIME ZONE
          USING canceled_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE subscriptions
          ALTER COLUMN ended_at TYPE TIMESTAMP WITH TIME ZONE
          USING ended_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE subscriptions
          ALTER COLUMN trial_start TYPE TIMESTAMP WITH TIME ZONE
          USING trial_start AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE subscriptions
          ALTER COLUMN trial_end TYPE TIMESTAMP WITH TIME ZONE
          USING trial_end AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE subscriptions
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE subscriptions
          ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
          USING updated_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 15. PAYMENTS TABLE (3 columns)
    # ========================================================================
    op.execute("""
        ALTER TABLE payments
          ALTER COLUMN paid_at TYPE TIMESTAMP WITH TIME ZONE
          USING paid_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE payments
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE payments
          ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
          USING updated_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 16. REFUNDS TABLE (2 columns)
    # ========================================================================
    op.execute("""
        ALTER TABLE refunds
          ALTER COLUMN refunded_at TYPE TIMESTAMP WITH TIME ZONE
          USING refunded_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE refunds
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 17. CHARGEBACKS TABLE (4 columns)
    # ========================================================================
    op.execute("""
        ALTER TABLE chargebacks
          ALTER COLUMN evidence_due_by TYPE TIMESTAMP WITH TIME ZONE
          USING evidence_due_by AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE chargebacks
          ALTER COLUMN disputed_at TYPE TIMESTAMP WITH TIME ZONE
          USING disputed_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE chargebacks
          ALTER COLUMN resolved_at TYPE TIMESTAMP WITH TIME ZONE
          USING resolved_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE chargebacks
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 18. PAYMENT_METHODS TABLE (2 columns)
    # ========================================================================
    op.execute("""
        ALTER TABLE payment_methods
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE payment_methods
          ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
          USING updated_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 19. INVOICES TABLE (4 columns)
    # ========================================================================
    op.execute("""
        ALTER TABLE invoices
          ALTER COLUMN invoice_date TYPE TIMESTAMP WITH TIME ZONE
          USING invoice_date AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE invoices
          ALTER COLUMN due_date TYPE TIMESTAMP WITH TIME ZONE
          USING due_date AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE invoices
          ALTER COLUMN paid_at TYPE TIMESTAMP WITH TIME ZONE
          USING paid_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE invoices
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 20. REVENUE_EVENTS TABLE (2 columns)
    # ========================================================================
    op.execute("""
        ALTER TABLE revenue_events
          ALTER COLUMN occurred_at TYPE TIMESTAMP WITH TIME ZONE
          USING occurred_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE revenue_events
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 21. SECURITY_LOGS TABLE (1 column)
    # ========================================================================
    op.execute("""
        ALTER TABLE security_logs
          ALTER COLUMN occurred_at TYPE TIMESTAMP WITH TIME ZONE
          USING occurred_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 22. RATE_LIMIT_ENTRIES TABLE (5 columns)
    # ========================================================================
    op.execute("""
        ALTER TABLE rate_limit_entries
          ALTER COLUMN window_start TYPE TIMESTAMP WITH TIME ZONE
          USING window_start AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE rate_limit_entries
          ALTER COLUMN window_end TYPE TIMESTAMP WITH TIME ZONE
          USING window_end AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE rate_limit_entries
          ALTER COLUMN blocked_until TYPE TIMESTAMP WITH TIME ZONE
          USING blocked_until AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE rate_limit_entries
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE rate_limit_entries
          ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
          USING updated_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 23. CONTENT_CHUNKS TABLE (2 columns)
    # ========================================================================
    op.execute("""
        ALTER TABLE content_chunks
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE content_chunks
          ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
          USING updated_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 24. CONTENT_FEEDBACK TABLE (1 column)
    # ========================================================================
    op.execute("""
        ALTER TABLE content_feedback
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    # ========================================================================
    # 25. CONTENT_EFFICACY TABLE (3 columns)
    # ========================================================================
    op.execute("""
        ALTER TABLE content_efficacy
          ALTER COLUMN read_at TYPE TIMESTAMP WITH TIME ZONE
          USING read_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE content_efficacy
          ALTER COLUMN measured_at TYPE TIMESTAMP WITH TIME ZONE
          USING measured_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE content_efficacy
          ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
          USING created_at AT TIME ZONE 'UTC';
    """)

    print("✓ Successfully converted 70 DateTime columns to TIMESTAMPTZ")


def downgrade():
    """
    Rollback: Convert TIMESTAMPTZ columns back to TIMESTAMP (timezone-naive).

    WARNING: This will lose timezone information! Only use for testing rollback.
    Production databases should keep TIMESTAMPTZ after migration.
    """

    # ========================================================================
    # ROLLBACK: Convert all columns back to TIMESTAMP WITHOUT TIME ZONE
    # ========================================================================

    # 1. USERS TABLE
    op.execute("ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE users ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE users ALTER COLUMN last_login_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 2. USER_PROFILES TABLE
    op.execute("ALTER TABLE user_profiles ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE user_profiles ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 3. COURSES TABLE
    op.execute("ALTER TABLE courses ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE courses ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE courses ALTER COLUMN auto_delete_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 4. KNOWLEDGE_AREAS TABLE
    op.execute("ALTER TABLE knowledge_areas ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE knowledge_areas ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 5. DOMAINS TABLE
    op.execute("ALTER TABLE domains ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE domains ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 6. QUESTIONS TABLE
    op.execute("ALTER TABLE questions ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE questions ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 7. ANSWER_CHOICES TABLE
    op.execute("ALTER TABLE answer_choices ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE answer_choices ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 8. SESSIONS TABLE
    op.execute("ALTER TABLE sessions ALTER COLUMN started_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE sessions ALTER COLUMN completed_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE sessions ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE sessions ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 9. QUESTION_ATTEMPTS TABLE
    op.execute("ALTER TABLE question_attempts ALTER COLUMN attempted_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 10. USER_COMPETENCY TABLE
    op.execute("ALTER TABLE user_competency ALTER COLUMN last_updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE user_competency ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 11. READING_CONSUMED TABLE
    op.execute("ALTER TABLE reading_consumed ALTER COLUMN started_reading_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE reading_consumed ALTER COLUMN finished_reading_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE reading_consumed ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 12. SPACED_REPETITION_CARDS TABLE ⚠️ CRITICAL
    op.execute("ALTER TABLE spaced_repetition_cards ALTER COLUMN last_reviewed_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE spaced_repetition_cards ALTER COLUMN next_review_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE spaced_repetition_cards ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE spaced_repetition_cards ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 13. SUBSCRIPTION_PLANS TABLE
    op.execute("ALTER TABLE subscription_plans ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE subscription_plans ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 14. SUBSCRIPTIONS TABLE
    op.execute("ALTER TABLE subscriptions ALTER COLUMN current_period_start TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE subscriptions ALTER COLUMN current_period_end TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE subscriptions ALTER COLUMN started_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE subscriptions ALTER COLUMN canceled_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE subscriptions ALTER COLUMN ended_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE subscriptions ALTER COLUMN trial_start TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE subscriptions ALTER COLUMN trial_end TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE subscriptions ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE subscriptions ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 15. PAYMENTS TABLE
    op.execute("ALTER TABLE payments ALTER COLUMN paid_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE payments ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE payments ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 16. REFUNDS TABLE
    op.execute("ALTER TABLE refunds ALTER COLUMN refunded_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE refunds ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 17. CHARGEBACKS TABLE
    op.execute("ALTER TABLE chargebacks ALTER COLUMN evidence_due_by TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE chargebacks ALTER COLUMN disputed_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE chargebacks ALTER COLUMN resolved_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE chargebacks ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 18. PAYMENT_METHODS TABLE
    op.execute("ALTER TABLE payment_methods ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE payment_methods ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 19. INVOICES TABLE
    op.execute("ALTER TABLE invoices ALTER COLUMN invoice_date TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE invoices ALTER COLUMN due_date TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE invoices ALTER COLUMN paid_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE invoices ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 20. REVENUE_EVENTS TABLE
    op.execute("ALTER TABLE revenue_events ALTER COLUMN occurred_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE revenue_events ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 21. SECURITY_LOGS TABLE
    op.execute("ALTER TABLE security_logs ALTER COLUMN occurred_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 22. RATE_LIMIT_ENTRIES TABLE
    op.execute("ALTER TABLE rate_limit_entries ALTER COLUMN window_start TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE rate_limit_entries ALTER COLUMN window_end TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE rate_limit_entries ALTER COLUMN blocked_until TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE rate_limit_entries ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE rate_limit_entries ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 23. CONTENT_CHUNKS TABLE
    op.execute("ALTER TABLE content_chunks ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE content_chunks ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 24. CONTENT_FEEDBACK TABLE
    op.execute("ALTER TABLE content_feedback ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    # 25. CONTENT_EFFICACY TABLE
    op.execute("ALTER TABLE content_efficacy ALTER COLUMN read_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE content_efficacy ALTER COLUMN measured_at TYPE TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE content_efficacy ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;")

    print("✓ Rolled back 70 DateTime columns to TIMESTAMP (timezone-naive)")
