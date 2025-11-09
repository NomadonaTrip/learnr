"""
Admin Dashboard API endpoints.

**Decision #66:** Admin-only endpoints for platform management.

All endpoints require admin or super_admin role.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID
import math

from app.api.dependencies import get_db, get_current_admin_user
from app.models.user import User
from app.models.course import Course, KnowledgeArea
from app.models.question import Question
from app.models.content import ContentChunk
from app.models.financial import Subscription, SubscriptionPlan, Payment
from app.schemas.admin import (
    AdminUserListResponse,
    AdminUserListItem,
    AdminMetricsOverviewResponse,
    MetricsUsers,
    MetricsRevenue,
    MetricsEngagement,
    MetricsCourses,
    AdminCourseListResponse,
    AdminCourseListItem,
    CreateCourseRequest,
    CreateCourseResponse,
    CreateKnowledgeAreasRequest,
    CreateKnowledgeAreasResponse,
    KnowledgeAreaResponse,
    PublishCourseResponse,
    PublishCourseValidation
)

router = APIRouter()


# ============================================================================
# User Management
# ============================================================================

@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by email or name"),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """
    List all users (admin only).

    **Permissions:** admin or super_admin

    **Features:**
    - Pagination
    - Search by email or name
    - Filter by role and active status
    """
    # Build query
    query = db.query(User)

    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.email.ilike(search_term)) |
            (User.first_name.ilike(search_term)) |
            (User.last_name.ilike(search_term))
        )

    if role:
        query = query.filter(User.role == role)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    # Get total count
    total = query.count()

    # Calculate pagination
    total_pages = math.ceil(total / per_page)
    offset = (page - 1) * per_page

    # Get paginated users
    users = query.order_by(User.created_at.desc()).offset(offset).limit(per_page).all()

    return AdminUserListResponse(
        users=[AdminUserListItem.model_validate(user) for user in users],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )


# ============================================================================
# Metrics & Analytics
# ============================================================================

@router.get("/metrics/overview", response_model=AdminMetricsOverviewResponse)
def get_metrics_overview(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Get admin dashboard overview metrics.

    **Permissions:** admin or super_admin

    **Metrics:**
    - User statistics (total, active, new this month)
    - Revenue metrics (MRR, ARR, monthly revenue)
    - Engagement (DAU, avg session duration, questions answered)
    - Course statistics
    """
    # User metrics
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()

    # New users this month
    start_of_month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_this_month = db.query(User).filter(User.created_at >= start_of_month).count()

    # Revenue metrics (basic implementation)
    # MRR = sum of all monthly subscription amounts + (annual amounts / 12)
    active_subscriptions = db.query(Subscription, SubscriptionPlan).join(
        SubscriptionPlan, Subscription.plan_id == SubscriptionPlan.plan_id
    ).filter(
        Subscription.status == 'active'
    ).all()

    mrr = Decimal('0.00')
    for subscription, plan in active_subscriptions:
        if plan.billing_interval == 'monthly':
            mrr += plan.price_amount
        elif plan.billing_interval == 'annual':
            mrr += plan.price_amount / 12

    arr = mrr * 12

    # Total revenue this month
    total_revenue_this_month = db.query(
        func.sum(Payment.amount)
    ).filter(
        and_(
            Payment.payment_status == 'succeeded',
            Payment.created_at >= start_of_month
        )
    ).scalar() or Decimal('0.00')

    # Engagement metrics (simplified)
    # For MVP, using basic counts - can be enhanced with time-series data
    from app.models.learning import QuestionAttempt

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    questions_answered_today = db.query(QuestionAttempt).filter(
        QuestionAttempt.attempted_at >= today_start
    ).count()

    # DAU: users who answered at least 1 question today
    daily_active_users = db.query(QuestionAttempt.user_id).filter(
        QuestionAttempt.attempted_at >= today_start
    ).distinct().count()

    # Avg session duration (simplified - using avg time per question attempt)
    # In production, this would be calculated from Session model
    avg_session_duration_minutes = 18  # Placeholder for MVP

    # Course metrics
    total_courses = db.query(Course).count()
    active_courses = db.query(Course).filter(Course.status == 'active').count()
    total_questions = db.query(Question).filter(Question.is_active == True).count()

    return AdminMetricsOverviewResponse(
        users=MetricsUsers(
            total=total_users,
            active=active_users,
            new_this_month=new_this_month
        ),
        revenue=MetricsRevenue(
            mrr=mrr,
            arr=arr,
            total_revenue_this_month=total_revenue_this_month
        ),
        engagement=MetricsEngagement(
            daily_active_users=daily_active_users,
            avg_session_duration_minutes=avg_session_duration_minutes,
            questions_answered_today=questions_answered_today
        ),
        courses=MetricsCourses(
            total_courses=total_courses,
            active_courses=active_courses,
            total_questions=total_questions
        )
    )


# ============================================================================
# Course Management
# ============================================================================

@router.get("/courses", response_model=AdminCourseListResponse)
def list_courses(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """
    List all courses (admin only).

    **Permissions:** admin or super_admin

    Shows courses in all statuses (draft, active, archived).
    """
    courses = db.query(Course).order_by(Course.created_at.desc()).all()

    # Enrich with counts
    course_items = []
    for course in courses:
        # Count questions
        total_questions = db.query(Question).filter(
            Question.course_id == course.course_id
        ).count()

        # Count content chunks
        total_chunks = db.query(ContentChunk).filter(
            ContentChunk.course_id == course.course_id
        ).count()

        course_item = AdminCourseListItem(
            course_id=UUID(course.course_id),
            course_code=course.course_code,
            course_name=course.course_name,
            status=course.status,
            wizard_completed=course.wizard_completed,
            total_questions=total_questions,
            total_chunks=total_chunks,
            created_at=course.created_at
        )
        course_items.append(course_item)

    return AdminCourseListResponse(courses=course_items)


@router.post("/courses", response_model=CreateCourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    course_data: CreateCourseRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Create new course (wizard step 1).

    **Permissions:** admin or super_admin

    **Decision #65:** Course creation wizard
    - Creates course with status='draft'
    - Sets auto_delete_at to 7 days from now (abandoned draft cleanup)
    - Wizard must be completed to make course visible to learners
    """
    # Check if course code already exists
    existing = db.query(Course).filter(Course.course_code == course_data.course_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Course with code '{course_data.course_code}' already exists"
        )

    # Create course
    new_course = Course(
        course_code=course_data.course_code,
        course_name=course_data.course_name,
        version=course_data.version,
        description=course_data.description,
        status='draft',
        wizard_completed=False,
        passing_score_percentage=course_data.passing_score_percentage,
        exam_duration_minutes=course_data.exam_duration_minutes,
        total_questions=course_data.total_questions,
        min_questions_required=course_data.min_questions_required,
        min_chunks_required=course_data.min_chunks_required,
        created_by=admin_user.user_id,
        auto_delete_at=datetime.now(timezone.utc) + timedelta(days=7),  # Auto-delete abandoned drafts
        is_active=False  # Not visible to learners yet
    )

    db.add(new_course)
    db.commit()
    db.refresh(new_course)

    return CreateCourseResponse(
        course_id=UUID(new_course.course_id),
        course_code=new_course.course_code,
        status=new_course.status,
        wizard_completed=new_course.wizard_completed,
        auto_delete_at=new_course.auto_delete_at
    )


@router.post("/courses/{course_id}/knowledge-areas", response_model=CreateKnowledgeAreasResponse, status_code=status.HTTP_201_CREATED)
def create_knowledge_areas(
    course_id: UUID,
    ka_data: CreateKnowledgeAreasRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Add knowledge areas to course (wizard step 2).

    **Permissions:** admin or super_admin

    **Validation:**
    - Weights must sum to 100.00% (±0.01 tolerance)
    - Course must exist and be in draft status

    **Decision #63:** Variable KA counts per course
    - CBAP: 6 KAs
    - PSM1: 3 KAs
    - CFA: 10 KAs
    """
    # Get course
    course = db.query(Course).filter(Course.course_id == str(course_id)).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if course.status != 'draft':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only add knowledge areas to draft courses"
        )

    # Delete existing KAs if any (allow re-configuration)
    db.query(KnowledgeArea).filter(KnowledgeArea.course_id == str(course_id)).delete()

    # Create new KAs
    created_kas = []
    for ka in ka_data.knowledge_areas:
        new_ka = KnowledgeArea(
            course_id=str(course_id),
            ka_code=ka.ka_code,
            ka_name=ka.ka_name,
            ka_number=ka.ka_number,
            weight_percentage=ka.weight_percentage,
            description=ka.description
        )
        db.add(new_ka)
        created_kas.append(new_ka)

    db.commit()

    # Refresh to get generated IDs
    for ka in created_kas:
        db.refresh(ka)

    # Calculate total weight
    total_weight = sum(ka.weight_percentage for ka in ka_data.knowledge_areas)

    return CreateKnowledgeAreasResponse(
        course_id=course_id,
        knowledge_areas=[KnowledgeAreaResponse.model_validate(ka) for ka in created_kas],
        total_weight=total_weight,
        validation_passed=True  # Pydantic validator already checked this
    )


@router.post("/courses/{course_id}/publish", response_model=PublishCourseResponse)
def publish_course(
    course_id: UUID,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Publish course (wizard final step).

    **Permissions:** admin or super_admin

    **Validation:**
    - Must have >= min_questions_required (default: 200)
    - Must have >= min_chunks_required (default: 50)
    - All KA weights must sum to 100%

    **Side Effects:**
    - Sets status='active'
    - Sets wizard_completed=True
    - Clears auto_delete_at
    - Makes course visible to learners
    """
    # Get course
    course = db.query(Course).filter(Course.course_id == str(course_id)).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if course.status == 'active':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course is already published"
        )

    # Validation checks
    question_count = db.query(Question).filter(Question.course_id == str(course_id)).count()
    chunk_count = db.query(ContentChunk).filter(ContentChunk.course_id == str(course_id)).count()

    min_questions_met = question_count >= course.min_questions_required
    min_chunks_met = chunk_count >= course.min_chunks_required

    # Check KA weights
    kas = db.query(KnowledgeArea).filter(KnowledgeArea.course_id == str(course_id)).all()
    if not kas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course must have at least one knowledge area"
        )

    total_weight = sum(ka.weight_percentage for ka in kas)
    ka_weights_valid = 99.99 <= total_weight <= 100.01  # 0.01% tolerance

    ready_for_learners = min_questions_met and min_chunks_met and ka_weights_valid

    if not ready_for_learners:
        validation = PublishCourseValidation(
            min_questions_met=min_questions_met,
            min_chunks_met=min_chunks_met,
            ka_weights_valid=ka_weights_valid,
            ready_for_learners=False
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Course does not meet publishing requirements: {validation.model_dump()}"
        )

    # Publish course
    course.status = 'active'
    course.wizard_completed = True
    course.auto_delete_at = None
    course.is_active = True
    course.updated_by = admin_user.user_id

    db.commit()
    db.refresh(course)

    return PublishCourseResponse(
        course_id=UUID(course.course_id),
        status=course.status,
        wizard_completed=course.wizard_completed,
        validation=PublishCourseValidation(
            min_questions_met=True,
            min_chunks_met=True,
            ka_weights_valid=True,
            ready_for_learners=True
        )
    )
