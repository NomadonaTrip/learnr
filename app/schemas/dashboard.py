"""
Dashboard Pydantic schemas.

Decision #13: Progress dashboard with competency tracking.
User Flow #4: Dashboard showing progress and recommendations.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from app.schemas import BaseSchema


class CompetencyStatusResponse(BaseModel):
    """
    Single KA competency with status.
    """
    ka_id: UUID
    ka_code: str
    ka_name: str
    ka_weight_percentage: Decimal
    competency_score: Decimal  # 0.00-1.00
    status: str  # 'below_target', 'on_track', 'above_target'
    attempts_count: int
    correct_count: int
    incorrect_count: int
    accuracy_percentage: float  # 0-100
    last_practiced_at: Optional[datetime]


class CompetencyTrendPoint(BaseModel):
    """
    Competency score at a specific point in time.
    """
    date: date
    competency_score: Decimal
    attempts_count: int


class CompetencyDetailResponse(BaseModel):
    """
    Detailed KA competency with historical trend.
    """
    ka_id: UUID
    ka_code: str
    ka_name: str
    ka_weight_percentage: Decimal
    current_competency: Decimal
    status: str

    # Performance stats
    total_attempts: int
    correct_count: int
    incorrect_count: int
    accuracy_percentage: float

    # Trend data (last 30 days)
    trend: List[CompetencyTrendPoint]

    # Practice recommendations
    recommended_difficulty_range: dict  # {"min": 0.4, "max": 0.6}
    needs_practice: bool
    last_practiced_at: Optional[datetime]


class RecentSessionSummary(BaseModel):
    """
    Summary of a recent practice/diagnostic session.
    """
    session_id: UUID
    session_type: str  # 'diagnostic', 'practice', 'review', 'mock_exam'
    started_at: datetime
    completed_at: Optional[datetime]
    duration_minutes: Optional[int]
    total_questions: int
    correct_answers: int
    accuracy_percentage: float
    is_completed: bool


class FocusAreaRecommendation(BaseModel):
    """
    Recommended area to focus on.
    """
    ka_id: UUID
    ka_name: str
    ka_code: str
    current_competency: Decimal
    target_competency: Decimal  # 0.80 for exam readiness
    gap: Decimal  # How far from target
    priority: str  # 'high', 'medium', 'low'
    reason: str  # Why this is recommended


class DashboardOverviewResponse(BaseModel):
    """
    Main dashboard overview.

    Decision #13: Comprehensive progress dashboard.
    Shows overall metrics, competency status, and recommendations.
    """
    # User and course info
    user_id: UUID
    course_id: UUID
    course_name: str

    # Overall competency
    overall_competency: Decimal  # Weighted average across all KAs
    overall_competency_status: str  # 'below_target', 'on_track', 'above_target'
    exam_readiness_percentage: float  # 0-100, based on KAs at target

    # Performance metrics
    total_questions_attempted: int
    total_correct: int
    overall_accuracy: float  # 0-100

    # Session stats
    total_sessions_completed: int
    diagnostic_completed: bool
    last_practice_date: Optional[date]

    # Spaced repetition
    reviews_due_today: int
    reviews_overdue: int

    # Per-KA summary (sorted by competency - weakest first)
    competencies: List[CompetencyStatusResponse]

    # Recommendations
    focus_areas: List[FocusAreaRecommendation]
    daily_goal_met: bool  # If practiced today
    streak_days: int  # Consecutive days with practice


class CompetenciesDetailResponse(BaseModel):
    """
    Detailed competency breakdown with trends.

    Shows historical data and practice recommendations per KA.
    """
    user_id: UUID
    course_id: UUID
    overall_competency: Decimal

    # Detailed per-KA data with trends
    competencies: List[CompetencyDetailResponse]

    # Summary stats
    kas_below_target: int  # Count of KAs < 0.60
    kas_on_track: int  # Count of KAs 0.60-0.79
    kas_above_target: int  # Count of KAs >= 0.80

    # Overall trend
    overall_trend_direction: str  # 'improving', 'stable', 'declining'
    last_updated_at: datetime


class RecentActivityResponse(BaseModel):
    """
    Recent user activity and sessions.

    Shows practice history and engagement metrics.
    """
    user_id: UUID

    # Recent sessions (last 10)
    recent_sessions: List[RecentSessionSummary]

    # Activity metrics
    sessions_this_week: int
    questions_this_week: int
    accuracy_this_week: float

    sessions_this_month: int
    questions_this_month: int
    accuracy_this_month: float

    # Streaks and engagement
    current_streak_days: int
    longest_streak_days: int
    total_study_minutes: int

    # Last activity
    last_session_date: Optional[datetime]
    days_since_last_practice: Optional[int]


class ExamReadinessResponse(BaseModel):
    """
    Detailed exam readiness assessment.

    Decision #8: Competency-based success criteria.
    Target: All KAs >= 0.80 for exam readiness.
    """
    user_id: UUID
    course_id: UUID

    # Overall readiness
    exam_ready: bool  # True if all KAs >= 0.80
    readiness_percentage: float  # 0-100

    # Per-KA readiness
    kas_ready: int  # Count >= 0.80
    kas_not_ready: int  # Count < 0.80

    # Weakest areas
    weakest_kas: List[CompetencyStatusResponse]  # Bottom 3 KAs

    # Estimated time to readiness
    estimated_questions_remaining: int  # Based on current progress rate
    estimated_days_remaining: Optional[int]  # If daily goal is met

    # Recommendations
    recommendation: str
    next_steps: List[str]  # Action items for user
