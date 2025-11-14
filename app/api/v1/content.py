"""
Content API endpoints.

Handles content recommendations, chunk retrieval, and semantic search.
Decision #23: Reading content essential for learning.
Decision #76: Content quality evaluation system.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.models.database import get_db
from app.models.user import User
from app.api.dependencies import get_current_active_user
from app.schemas.content import (
    ContentRecommendationRequest,
    ContentRecommendationResponse,
    ContentChunkWithMetricsResponse
)
from app.services.content_recommendation import (
    get_recommended_content,
    get_chunk_by_id,
    get_user_weakest_knowledge_areas
)


router = APIRouter()


@router.get("/recommendations", response_model=ContentRecommendationResponse)
def get_content_recommendations(
    strategy: str = Query(default="adaptive", pattern="^(adaptive|recent_mistakes|ka_specific)$"),
    ka_id: Optional[UUID] = Query(default=None),
    limit: int = Query(default=5, ge=1, le=20),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get personalized content recommendations.

    **Recommendation Strategies:**
    - `adaptive` (default): Based on user's weakest knowledge areas
    - `recent_mistakes`: Based on recent incorrect answers
    - `ka_specific`: Content from a specific KA (requires ka_id parameter)

    **How it works:**
    1. Analyzes your competency scores and recent performance
    2. Identifies areas where you need improvement
    3. Recommends expert-reviewed, approved content
    4. Prioritizes source-verified material from BABOK v3

    **Quality Assurance:**
    - Only approved, active content is recommended
    - Expert-reviewed content prioritized
    - Source-verified content from official BABOK v3

    **Usage:**
    - Start with `adaptive` to get recommendations based on your current performance
    - Use `recent_mistakes` after practice sessions to review missed topics
    - Use `ka_specific` to deep-dive into a specific knowledge area
    """
    # Validate ka_specific strategy
    if strategy == "ka_specific" and ka_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ka_id is required when using ka_specific strategy"
        )

    # Get user's course (from their profile)
    from app.models.user import UserProfile
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.user_id).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User profile not found. Please complete onboarding first."
        )

    try:
        # Get recommendations using service
        chunks = get_recommended_content(
            db=db,
            user_id=current_user.user_id,
            course_id=profile.course_id,
            strategy=strategy,
            ka_id=ka_id,
            limit=limit
        )

        # Convert to response models with metrics
        recommendations = []
        for chunk in chunks:
            chunk_data = ContentChunkWithMetricsResponse(
                chunk_id=chunk.chunk_id,
                course_id=chunk.course_id,
                ka_id=chunk.ka_id,
                domain_id=chunk.domain_id,
                content_title=chunk.content_title,
                content_text=chunk.content_text,
                content_type=chunk.content_type,
                source_document=chunk.source_document,
                source_page=chunk.source_page,
                source_section=chunk.source_section,
                token_count=chunk.token_count,
                difficulty_level=chunk.difficulty_level,
                expert_reviewed=chunk.expert_reviewed,
                review_status=chunk.review_status,
                source_verified=chunk.source_verified,
                is_active=chunk.is_active,
                helpfulness_score=chunk.helpfulness_score,
                efficacy_rate=chunk.efficacy_rate,
                created_at=chunk.created_at,
                updated_at=chunk.updated_at
            )
            recommendations.append(chunk_data)

        # Build context metadata
        context = {}
        if strategy == "adaptive":
            # Include weakest KAs in context
            weak_kas = get_user_weakest_knowledge_areas(
                db=db,
                user_id=current_user.user_id,
                course_id=profile.course_id,
                limit=3
            )
            context["weakest_knowledge_areas"] = weak_kas
            context["explanation"] = "Recommendations based on your current competency scores. Focus on these areas to improve your weakest skills."

        elif strategy == "recent_mistakes":
            context["explanation"] = "Recommendations based on topics you recently got wrong. Review these to address your knowledge gaps."

        elif strategy == "ka_specific":
            context["ka_id"] = str(ka_id)
            context["explanation"] = "All content from the selected knowledge area."

        return ContentRecommendationResponse(
            strategy_used=strategy,
            total_recommendations=len(recommendations),
            recommendations=recommendations,
            context=context if context else None
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/chunks/{chunk_id}", response_model=ContentChunkWithMetricsResponse)
def get_content_chunk(
    chunk_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific content chunk by ID.

    Returns detailed content with quality metrics:
    - Helpfulness score (% of users who found it helpful)
    - Efficacy rate (% of users who improved after reading)

    **Only active, approved content is accessible.**

    Use this endpoint to:
    1. Display full content after selecting from recommendations
    2. Access content from study plan
    3. Review material before or after practice sessions
    """
    chunk = get_chunk_by_id(db, chunk_id)

    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content chunk not found or not available"
        )

    # Log that user consumed this content (for efficacy tracking)
    from app.models.learning import ReadingConsumed
    from datetime import datetime, timezone

    # Check if already consumed recently (within last hour)
    from sqlalchemy import and_
    from datetime import timedelta
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

    existing_read = db.query(ReadingConsumed).filter(
        and_(
            ReadingConsumed.user_id == current_user.user_id,
            ReadingConsumed.chunk_id == str(chunk_id),
            ReadingConsumed.read_at >= one_hour_ago
        )
    ).first()

    if not existing_read:
        # Log new reading
        reading = ReadingConsumed(
            user_id=current_user.user_id,
            chunk_id=str(chunk_id),
            ka_id=chunk.ka_id,
            read_at=datetime.now(timezone.utc),
            time_spent_seconds=0  # Can be updated via separate endpoint
        )
        db.add(reading)
        db.commit()

    return ContentChunkWithMetricsResponse(
        chunk_id=chunk.chunk_id,
        course_id=chunk.course_id,
        ka_id=chunk.ka_id,
        domain_id=chunk.domain_id,
        content_title=chunk.content_title,
        content_text=chunk.content_text,
        content_type=chunk.content_type,
        source_document=chunk.source_document,
        source_page=chunk.source_page,
        source_section=chunk.source_section,
        token_count=chunk.token_count,
        difficulty_level=chunk.difficulty_level,
        expert_reviewed=chunk.expert_reviewed,
        review_status=chunk.review_status,
        source_verified=chunk.source_verified,
        is_active=chunk.is_active,
        helpfulness_score=chunk.helpfulness_score,
        efficacy_rate=chunk.efficacy_rate,
        created_at=chunk.created_at,
        updated_at=chunk.updated_at
    )
