"""
Dashboard API endpoints.

Decision #13: Progress dashboard with competency tracking.
User Flow #4: Dashboard showing overall progress and recommendations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List
from datetime import datetime, timedelta, date, timezone
from decimal import Decimal

from app.models.database import get_db
from app.models.user import User
from app.models.course import Course, KnowledgeArea
from app.models.learning import Session as LearningSession, QuestionAttempt, UserCompetency
from app.models.spaced_repetition import SpacedRepetitionCard
from app.api.dependencies import get_current_active_user
from app.schemas.dashboard import (
    DashboardOverviewResponse,
    CompetencyStatusResponse,
    CompetenciesDetailResponse,
    CompetencyDetailResponse,
    CompetencyTrendPoint,
    RecentActivityResponse,
    RecentSessionSummary,
    FocusAreaRecommendation,
    ExamReadinessResponse
)
from app.services.competency import (
    calculate_weighted_competency,
    get_user_competencies,
    determine_competency_status
)

router = APIRouter()


@router.get("", response_model=DashboardOverviewResponse)
def get_dashboard_overview(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get main dashboard overview.

    Decision #13: Comprehensive progress dashboard showing:
    - Overall competency and exam readiness
    - Per-KA competency status
    - Performance metrics
    - Spaced repetition reviews due
    - Personalized recommendations

    Returns complete snapshot of user's learning progress.
    """
    # Get user's current course (assume first active course for now)
    # In production, track user's selected course in user_profile
    user_sessions = db.query(LearningSession).filter(
        LearningSession.user_id == str(current_user.user_id)
    ).first()

    if not user_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No learning activity found. Complete diagnostic assessment first."
        )

    course = db.query(Course).filter(
        Course.course_id == user_sessions.course_id
    ).first()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Get all competencies for user
    competencies = get_user_competencies(db, current_user.user_id)

    if not competencies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No competency data. Complete diagnostic assessment first."
        )

    # Calculate overall weighted competency
    overall_competency = calculate_weighted_competency(db, current_user.user_id, course.course_id)
    overall_status = determine_competency_status(overall_competency)

    # Calculate exam readiness (% of KAs at target >= 0.80)
    kas_at_target = sum(1 for c in competencies if c.competency_score >= Decimal('0.80'))
    total_kas = len(competencies)
    exam_readiness_pct = (kas_at_target / total_kas * 100) if total_kas > 0 else 0.0

    # Get total questions attempted and accuracy
    all_attempts = db.query(QuestionAttempt).filter(
        QuestionAttempt.user_id == str(current_user.user_id)
    ).all()

    total_questions = len(all_attempts)
    total_correct = sum(1 for a in all_attempts if a.is_correct)
    overall_accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0.0

    # Get session stats
    all_sessions = db.query(LearningSession).filter(
        LearningSession.user_id == str(current_user.user_id)
    ).all()

    total_sessions = sum(1 for s in all_sessions if s.is_completed)
    diagnostic_completed = any(s.session_type == 'diagnostic' and s.is_completed for s in all_sessions)

    # Get last practice date
    last_practice = db.query(LearningSession).filter(
        LearningSession.user_id == str(current_user.user_id),
        LearningSession.is_completed == True
    ).order_by(LearningSession.completed_at.desc()).first()

    last_practice_date = last_practice.completed_at.date() if last_practice and last_practice.completed_at else None

    # Get spaced repetition reviews due
    today = datetime.now(timezone.utc)
    reviews_due = db.query(SpacedRepetitionCard).filter(
        SpacedRepetitionCard.user_id == str(current_user.user_id),
        SpacedRepetitionCard.is_due == True,
        SpacedRepetitionCard.next_review_at <= today
    ).count()

    reviews_overdue = db.query(SpacedRepetitionCard).filter(
        SpacedRepetitionCard.user_id == str(current_user.user_id),
        SpacedRepetitionCard.is_due == True,
        SpacedRepetitionCard.next_review_at < today - timedelta(days=1)
    ).count()

    # Build per-KA competency summaries (sorted by competency - weakest first)
    competency_summaries = []
    for comp in sorted(competencies, key=lambda x: x.competency_score):
        ka = db.query(KnowledgeArea).filter(
            KnowledgeArea.ka_id == comp.ka_id
        ).first()

        if ka:
            accuracy_pct = (comp.correct_count / comp.attempts_count * 100) if comp.attempts_count > 0 else 0.0

            competency_summaries.append(CompetencyStatusResponse(
                ka_id=comp.ka_id,
                ka_code=ka.ka_code,
                ka_name=ka.ka_name,
                ka_weight_percentage=ka.weight_percentage,
                competency_score=comp.competency_score,
                status=determine_competency_status(comp.competency_score),
                attempts_count=comp.attempts_count,
                correct_count=comp.correct_count,
                incorrect_count=comp.incorrect_count,
                accuracy_percentage=accuracy_pct,
                last_practiced_at=comp.last_updated_at
            ))

    # Generate focus area recommendations (weakest 2-3 KAs)
    focus_areas = []
    target_competency = Decimal('0.80')

    for comp_summary in competency_summaries[:3]:  # Top 3 weakest
        if comp_summary.competency_score < target_competency:
            gap = target_competency - comp_summary.competency_score

            # Determine priority based on gap and weight
            if gap >= Decimal('0.30'):
                priority = 'high'
                reason = f"Critical gap of {float(gap):.2f} from exam readiness target"
            elif gap >= Decimal('0.15'):
                priority = 'medium'
                reason = f"Moderate gap of {float(gap):.2f} needs attention"
            else:
                priority = 'low'
                reason = f"Small gap of {float(gap):.2f}, almost at target"

            focus_areas.append(FocusAreaRecommendation(
                ka_id=comp_summary.ka_id,
                ka_name=comp_summary.ka_name,
                ka_code=comp_summary.ka_code,
                current_competency=comp_summary.competency_score,
                target_competency=target_competency,
                gap=gap,
                priority=priority,
                reason=reason
            ))

    # Calculate streak (consecutive days with completed sessions)
    # Simple implementation - can be enhanced with dedicated streak tracking
    streak_days = 0
    if last_practice_date:
        current_date = date.today()
        if last_practice_date == current_date:
            # Count backwards to find streak
            check_date = current_date
            while True:
                sessions_on_date = db.query(LearningSession).filter(
                    LearningSession.user_id == str(current_user.user_id),
                    LearningSession.is_completed == True,
                    func.date(LearningSession.completed_at) == check_date
                ).count()

                if sessions_on_date > 0:
                    streak_days += 1
                    check_date = check_date - timedelta(days=1)
                else:
                    break

    daily_goal_met = last_practice_date == date.today() if last_practice_date else False

    return DashboardOverviewResponse(
        user_id=current_user.user_id,
        course_id=course.course_id,
        course_name=course.course_name,
        overall_competency=overall_competency,
        overall_competency_status=overall_status,
        exam_readiness_percentage=exam_readiness_pct,
        total_questions_attempted=total_questions,
        total_correct=total_correct,
        overall_accuracy=overall_accuracy,
        total_sessions_completed=total_sessions,
        diagnostic_completed=diagnostic_completed,
        last_practice_date=last_practice_date,
        reviews_due_today=reviews_due,
        reviews_overdue=reviews_overdue,
        competencies=competency_summaries,
        focus_areas=focus_areas,
        daily_goal_met=daily_goal_met,
        streak_days=streak_days
    )


@router.get("/competencies", response_model=CompetenciesDetailResponse)
def get_competencies_detail(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed competency breakdown with trends.

    Shows historical competency data and practice recommendations per KA.
    Includes 30-day trend data for visualizations.
    """
    # Get user's course
    user_sessions = db.query(LearningSession).filter(
        LearningSession.user_id == str(current_user.user_id)
    ).first()

    if not user_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No learning activity found"
        )

    course_id = user_sessions.course_id

    # Get all competencies
    competencies = get_user_competencies(db, current_user.user_id)

    if not competencies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No competency data available"
        )

    # Calculate overall competency
    overall_competency = calculate_weighted_competency(db, current_user.user_id, course_id)

    # Build detailed competency data
    competency_details = []
    kas_below = 0
    kas_on_track = 0
    kas_above = 0

    # Sort by competency score (weakest first)
    for comp in sorted(competencies, key=lambda x: x.competency_score):
        ka = db.query(KnowledgeArea).filter(
            KnowledgeArea.ka_id == comp.ka_id
        ).first()

        if not ka:
            continue

        status_label = determine_competency_status(comp.competency_score)

        # Count by status
        if status_label == 'below_target':
            kas_below += 1
        elif status_label == 'on_track':
            kas_on_track += 1
        else:
            kas_above += 1

        accuracy_pct = (comp.correct_count / comp.attempts_count * 100) if comp.attempts_count > 0 else 0.0

        # Generate trend data (last 30 days)
        # For MVP, we'll create a simple trend based on current data
        # In production, track daily snapshots of competency scores
        trend_points = []
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

        # Get attempts in last 30 days grouped by date
        attempts_by_date = db.query(
            func.date(QuestionAttempt.attempted_at).label('attempt_date'),
            func.count(QuestionAttempt.attempt_id).label('count')
        ).join(
            LearningSession,
            QuestionAttempt.session_id == LearningSession.session_id
        ).filter(
            QuestionAttempt.user_id == str(current_user.user_id),
            QuestionAttempt.attempted_at >= thirty_days_ago
        ).group_by(func.date(QuestionAttempt.attempted_at)).all()

        # Simple trend: show current competency for dates with activity
        # In production, calculate actual historical competency
        for attempt_date, count in attempts_by_date:
            trend_points.append(CompetencyTrendPoint(
                date=attempt_date,
                competency_score=comp.competency_score,  # Simplified - use current
                attempts_count=count
            ))

        # Recommended difficulty range based on current competency
        current_comp_float = float(comp.competency_score)
        recommended_range = {
            "min": max(0.0, current_comp_float - 0.1),
            "max": min(1.0, current_comp_float + 0.1)
        }

        # Needs practice if below target or low accuracy
        needs_practice = comp.competency_score < Decimal('0.70') or accuracy_pct < 60.0

        competency_details.append(CompetencyDetailResponse(
            ka_id=comp.ka_id,
            ka_code=ka.ka_code,
            ka_name=ka.ka_name,
            ka_weight_percentage=ka.weight_percentage,
            current_competency=comp.competency_score,
            status=status_label,
            total_attempts=comp.attempts_count,
            correct_count=comp.correct_count,
            incorrect_count=comp.incorrect_count,
            accuracy_percentage=accuracy_pct,
            trend=trend_points,
            recommended_difficulty_range=recommended_range,
            needs_practice=needs_practice,
            last_practiced_at=comp.last_updated_at
        ))

    # Determine overall trend direction
    # Simple heuristic: if more KAs improving than declining, trend is "improving"
    if kas_above > kas_below:
        trend_direction = "improving"
    elif kas_below > kas_above:
        trend_direction = "declining"
    else:
        trend_direction = "stable"

    return CompetenciesDetailResponse(
        user_id=current_user.user_id,
        course_id=course_id,
        overall_competency=overall_competency,
        competencies=competency_details,
        kas_below_target=kas_below,
        kas_on_track=kas_on_track,
        kas_above_target=kas_above,
        overall_trend_direction=trend_direction,
        last_updated_at=datetime.now(timezone.utc)
    )


@router.get("/recent", response_model=RecentActivityResponse)
def get_recent_activity(
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get recent user activity and engagement metrics.

    Shows practice history, streaks, and activity patterns.
    """
    # Get recent sessions (last N)
    recent_sessions_records = db.query(LearningSession).filter(
        LearningSession.user_id == str(current_user.user_id)
    ).order_by(LearningSession.started_at.desc()).limit(limit).all()

    recent_sessions = []
    for session in recent_sessions_records:
        duration_minutes = None
        if session.completed_at and session.started_at:
            duration_seconds = int((session.completed_at - session.started_at).total_seconds())
            duration_minutes = duration_seconds // 60

        # Calculate accuracy
        attempts = db.query(QuestionAttempt).filter(
            QuestionAttempt.session_id == session.session_id
        ).all()

        questions_answered = len(attempts)
        correct = sum(1 for a in attempts if a.is_correct)
        accuracy = (correct / questions_answered * 100) if questions_answered > 0 else 0.0

        recent_sessions.append(RecentSessionSummary(
            session_id=session.session_id,
            session_type=session.session_type,
            started_at=session.started_at,
            completed_at=session.completed_at,
            duration_minutes=duration_minutes,
            total_questions=session.total_questions,
            correct_answers=session.correct_answers,
            accuracy_percentage=accuracy,
            is_completed=session.is_completed
        ))

    # Calculate weekly metrics
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    sessions_this_week = db.query(LearningSession).filter(
        LearningSession.user_id == str(current_user.user_id),
        LearningSession.started_at >= week_ago,
        LearningSession.is_completed == True
    ).all()

    week_sessions_count = len(sessions_this_week)
    week_questions = sum(s.total_questions for s in sessions_this_week)
    week_correct = sum(s.correct_answers for s in sessions_this_week)
    week_accuracy = (week_correct / week_questions * 100) if week_questions > 0 else 0.0

    # Calculate monthly metrics
    month_ago = datetime.now(timezone.utc) - timedelta(days=30)
    sessions_this_month = db.query(LearningSession).filter(
        LearningSession.user_id == str(current_user.user_id),
        LearningSession.started_at >= month_ago,
        LearningSession.is_completed == True
    ).all()

    month_sessions_count = len(sessions_this_month)
    month_questions = sum(s.total_questions for s in sessions_this_month)
    month_correct = sum(s.correct_answers for s in sessions_this_month)
    month_accuracy = (month_correct / month_questions * 100) if month_questions > 0 else 0.0

    # Calculate streaks
    all_completed_sessions = db.query(LearningSession).filter(
        LearningSession.user_id == str(current_user.user_id),
        LearningSession.is_completed == True
    ).order_by(LearningSession.completed_at.desc()).all()

    current_streak = 0
    longest_streak = 0

    if all_completed_sessions:
        # Current streak
        today = date.today()
        last_session_date = all_completed_sessions[0].completed_at.date() if all_completed_sessions[0].completed_at else None

        if last_session_date:
            if last_session_date == today or last_session_date == today - timedelta(days=1):
                # Build streak backwards
                check_date = last_session_date
                for session in all_completed_sessions:
                    if session.completed_at:
                        session_date = session.completed_at.date()
                        if session_date == check_date:
                            current_streak += 1
                            check_date = check_date - timedelta(days=1)
                        elif session_date < check_date:
                            break

        # Longest streak (simplified - just use current for now)
        longest_streak = max(current_streak, longest_streak)

    # Calculate total study time
    total_minutes = 0
    for session in all_completed_sessions:
        if session.duration_seconds:
            total_minutes += session.duration_seconds // 60

    # Last activity
    last_session = all_completed_sessions[0] if all_completed_sessions else None
    last_session_date = last_session.completed_at if last_session else None

    days_since_last = None
    if last_session_date:
        days_since_last = (datetime.now(timezone.utc) - last_session_date).days

    return RecentActivityResponse(
        user_id=current_user.user_id,
        recent_sessions=recent_sessions,
        sessions_this_week=week_sessions_count,
        questions_this_week=week_questions,
        accuracy_this_week=week_accuracy,
        sessions_this_month=month_sessions_count,
        questions_this_month=month_questions,
        accuracy_this_month=month_accuracy,
        current_streak_days=current_streak,
        longest_streak_days=longest_streak,
        total_study_minutes=total_minutes,
        last_session_date=last_session_date,
        days_since_last_practice=days_since_last
    )


@router.get("/exam-readiness", response_model=ExamReadinessResponse)
def get_exam_readiness(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed exam readiness assessment.

    Decision #8: Competency-based success criteria.
    Target: All KAs >= 0.80 for exam readiness.

    Provides actionable recommendations for reaching exam readiness.
    """
    # Get user's course
    user_sessions = db.query(LearningSession).filter(
        LearningSession.user_id == str(current_user.user_id)
    ).first()

    if not user_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No learning activity found"
        )

    course_id = user_sessions.course_id

    # Get all competencies
    competencies = get_user_competencies(db, current_user.user_id)

    if not competencies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No competency data available"
        )

    # Count KAs at target
    target_threshold = Decimal('0.80')
    kas_ready = sum(1 for c in competencies if c.competency_score >= target_threshold)
    kas_not_ready = len(competencies) - kas_ready

    exam_ready = kas_not_ready == 0
    readiness_pct = (kas_ready / len(competencies) * 100) if competencies else 0.0

    # Get weakest 3 KAs
    weakest_comps = sorted(competencies, key=lambda x: x.competency_score)[:3]
    weakest_kas = []

    for comp in weakest_comps:
        ka = db.query(KnowledgeArea).filter(
            KnowledgeArea.ka_id == comp.ka_id
        ).first()

        if ka:
            accuracy = (comp.correct_count / comp.attempts_count * 100) if comp.attempts_count > 0 else 0.0

            weakest_kas.append(CompetencyStatusResponse(
                ka_id=comp.ka_id,
                ka_code=ka.ka_code,
                ka_name=ka.ka_name,
                ka_weight_percentage=ka.weight_percentage,
                competency_score=comp.competency_score,
                status=determine_competency_status(comp.competency_score),
                attempts_count=comp.attempts_count,
                correct_count=comp.correct_count,
                incorrect_count=comp.incorrect_count,
                accuracy_percentage=accuracy,
                last_practiced_at=comp.last_updated_at
            ))

    # Estimate questions remaining
    # Simple heuristic: for each KA below target, estimate questions needed
    estimated_questions = 0
    for comp in competencies:
        if comp.competency_score < target_threshold:
            gap = float(target_threshold - comp.competency_score)
            # Rough estimate: 10 questions per 0.10 gap
            estimated_questions += int(gap * 100)

    # Estimate days remaining (assuming 20 questions per day)
    estimated_days = (estimated_questions // 20) if estimated_questions > 0 else 0

    # Generate recommendation
    if exam_ready:
        recommendation = "🎉 You're exam ready! All knowledge areas are at target competency (≥0.80). Consider taking a mock exam to validate readiness."
    elif readiness_pct >= 75:
        recommendation = f"Almost ready! Focus on final improvements in {weakest_kas[0].ka_name if weakest_kas else 'weak areas'}. Estimated {estimated_days} days of practice remaining."
    elif readiness_pct >= 50:
        recommendation = f"Good progress. Continue focused practice on {kas_not_ready} knowledge areas still below target. Estimated {estimated_days} days of practice remaining."
    else:
        recommendation = f"Significant preparation needed. Focus on foundational knowledge in {kas_not_ready} knowledge areas. Estimated {estimated_days} days of practice remaining."

    # Generate next steps
    next_steps = []
    if not exam_ready:
        if weakest_kas:
            next_steps.append(f"Practice {weakest_kas[0].ka_name} (current: {float(weakest_kas[0].competency_score):.2f}, target: 0.80)")

        if kas_not_ready > 2:
            next_steps.append(f"Focus on {kas_not_ready} knowledge areas below target")

        next_steps.append(f"Complete approximately {estimated_questions} more questions")

        if estimated_days > 0:
            next_steps.append(f"Practice daily for {estimated_days} more days")
    else:
        next_steps.append("Take a full mock exam to validate readiness")
        next_steps.append("Review any weak spots from mock exam")
        next_steps.append("Schedule your certification exam")

    return ExamReadinessResponse(
        user_id=current_user.user_id,
        course_id=course_id,
        exam_ready=exam_ready,
        readiness_percentage=readiness_pct,
        kas_ready=kas_ready,
        kas_not_ready=kas_not_ready,
        weakest_kas=weakest_kas,
        estimated_questions_remaining=estimated_questions,
        estimated_days_remaining=estimated_days if estimated_days > 0 else None,
        recommendation=recommendation,
        next_steps=next_steps
    )
