"""
Spaced Repetition API endpoints.

Decision #31: Spaced repetition essential for MVP
Decision #32: SM-2 algorithm selected

Endpoints:
- GET /v1/reviews/due - Get cards due for review
- POST /v1/reviews/{card_id}/answer - Answer review card with SM-2 quality rating
- GET /v1/reviews/stats - Get review statistics
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from decimal import Decimal

from app.api.dependencies import get_db, get_current_active_user
from app.models.user import User
from app.models.spaced_repetition import SpacedRepetitionCard
from app.models.question import Question
from app.models.course import KnowledgeArea
from app.schemas.spaced_repetition import (
    DueCardsResponse,
    SpacedRepetitionCardResponse,
    ReviewAnswerRequest,
    ReviewAnswerResponse,
    SM2UpdatedParameters,
    ReviewStatsResponse
)
from app.services.spaced_repetition import (
    get_due_cards,
    update_card_sm2,
    get_review_statistics,
    get_feedback_message
)

router = APIRouter()


@router.get("/due", response_model=DueCardsResponse)
def get_due_reviews(
    limit: int = Query(20, ge=1, le=50, description="Max cards to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get spaced repetition cards due for review.

    Returns cards where next_review_at <= current time, ordered by:
    1. Overdue cards first (oldest first)
    2. Then by next_review_at (soonest first)

    **Decision #31:** Spaced repetition essential for MVP
    """
    # Get due cards
    due_cards = get_due_cards(db, current_user.user_id, limit)

    # Count total due and overdue
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    total_due = len(due_cards)
    total_overdue = sum(1 for card in due_cards if card.next_review_at < now)

    # Estimate time (2 minutes per card average)
    estimated_minutes = total_due * 2

    # Build response with question details
    card_responses = []
    for card in due_cards:
        # Get question details
        question = db.query(Question).filter(
            Question.question_id == card.question_id
        ).first()

        if not question:
            continue

        # Get KA details
        ka = db.query(KnowledgeArea).filter(
            KnowledgeArea.ka_id == question.ka_id
        ).first()

        # Calculate success rate
        success_rate = 0.0
        if card.total_reviews > 0:
            success_rate = (card.successful_reviews / card.total_reviews) * 100

        card_responses.append(SpacedRepetitionCardResponse(
            card_id=UUID(card.card_id),
            question_id=UUID(card.question_id),
            question_text=question.question_text,
            ka_code=ka.ka_code if ka else "UNKNOWN",
            ka_name=ka.ka_name if ka else "Unknown",
            easiness_factor=card.easiness_factor,
            interval_days=card.interval_days,
            repetition_count=card.repetition_count,
            last_reviewed_at=card.last_reviewed_at,
            next_review_at=card.next_review_at,
            is_due=card.is_due,
            total_reviews=card.total_reviews,
            successful_reviews=card.successful_reviews,
            success_rate=round(success_rate, 1)
        ))

    return DueCardsResponse(
        cards=card_responses,
        total_due=total_due,
        total_overdue=total_overdue,
        estimated_minutes=estimated_minutes
    )


@router.post("/{card_id}/answer", response_model=ReviewAnswerResponse)
def answer_review_card(
    card_id: UUID,
    answer_data: ReviewAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Answer a spaced repetition card with SM-2 quality rating.

    **SM-2 Quality Ratings:**
    - **5:** Perfect recall
    - **4:** Correct with hesitation
    - **3:** Correct with difficulty (minimum passing)
    - **2:** Incorrect but remembered on seeing answer
    - **1:** Incorrect but familiar
    - **0:** Complete blackout (no memory)

    **Decision #32:** SM-2 algorithm selected for review scheduling

    The card's easiness factor, interval, and next review date will be
    updated based on the quality rating.
    """
    # Get the card
    card = db.query(SpacedRepetitionCard).filter(
        SpacedRepetitionCard.card_id == str(card_id)
    ).first()

    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    # Verify ownership
    if card.user_id != str(current_user.user_id):
        raise HTTPException(status_code=403, detail="Not authorized to access this card")

    # Store previous state
    previous_ef = card.easiness_factor
    previous_interval = card.interval_days

    # Update card using SM-2 algorithm
    updated_card = update_card_sm2(card, answer_data.quality)
    db.commit()
    db.refresh(updated_card)

    # Determine if answer was "correct" (quality >= 3)
    is_correct = answer_data.quality >= 3

    # Generate feedback message
    feedback = get_feedback_message(answer_data.quality, updated_card.interval_days)

    return ReviewAnswerResponse(
        card_id=UUID(updated_card.card_id),
        question_id=UUID(updated_card.question_id),
        is_correct=is_correct,
        previous_ef=previous_ef,
        previous_interval=previous_interval,
        updated=SM2UpdatedParameters(
            easiness_factor=updated_card.easiness_factor,
            interval_days=updated_card.interval_days,
            repetition_count=updated_card.repetition_count,
            next_review_at=updated_card.next_review_at
        ),
        quality_rating=answer_data.quality,
        feedback_message=feedback
    )


@router.get("/stats", response_model=ReviewStatsResponse)
def get_user_review_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get overall spaced repetition statistics for current user.

    Returns metrics on:
    - Total cards and due cards
    - Mastered cards (EF >= 2.5, interval >= 30 days)
    - Average success rate
    - Current review streak
    - Daily review recommendations
    """
    stats = get_review_statistics(db, current_user.user_id)

    return ReviewStatsResponse(
        user_id=current_user.user_id,
        total_cards=stats['total_cards'],
        cards_due_today=stats['cards_due_today'],
        cards_due_this_week=stats['cards_due_this_week'],
        cards_mastered=stats['cards_mastered'],
        total_reviews_completed=stats['total_reviews_completed'],
        average_success_rate=stats['average_success_rate'],
        current_streak_days=stats['current_streak_days'],
        daily_review_target=stats['daily_review_target'],
        estimated_daily_minutes=stats['estimated_daily_minutes']
    )
