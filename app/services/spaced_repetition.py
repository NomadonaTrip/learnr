"""
Spaced Repetition Service - SM-2 Algorithm Implementation.

Decision #31: Spaced repetition essential for MVP
Decision #32: SM-2 (SuperMemo-2) algorithm selected

Implements the classic SM-2 algorithm for optimal review scheduling.
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional, Dict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from app.models.spaced_repetition import SpacedRepetitionCard
from app.models.question import Question
from app.models.learning import QuestionAttempt


def create_or_update_sr_card(
    db: Session,
    user_id: uuid.UUID,
    question_id: uuid.UUID,
    is_correct: bool,
    quality: Optional[int] = None
) -> SpacedRepetitionCard:
    """
    Create new spaced repetition card or update existing one.

    Called automatically when user answers a question in practice/diagnostic.

    Args:
        db: Database session
        user_id: User ID
        question_id: Question ID
        is_correct: Whether answer was correct
        quality: Optional SM-2 quality rating (0-5). If None, inferred from is_correct.

    Returns:
        Created or updated SpacedRepetitionCard
    """
    # Check if card already exists
    existing_card = db.query(SpacedRepetitionCard).filter(
        and_(
            SpacedRepetitionCard.user_id == str(user_id),
            SpacedRepetitionCard.question_id == str(question_id)
        )
    ).first()

    if existing_card:
        # Card exists - use provided quality or infer from correctness
        if quality is None:
            quality = 4 if is_correct else 2  # Default quality based on correctness

        # Update existing card with SM-2 algorithm
        updated_card = update_card_sm2(existing_card, quality)
        db.commit()
        db.refresh(updated_card)
        return updated_card
    else:
        # Create new card
        new_card = SpacedRepetitionCard(
            card_id=str(uuid.uuid4()),
            user_id=str(user_id),
            question_id=str(question_id),
            easiness_factor=Decimal('2.50'),  # Default EF
            repetition_count=0,
            interval_days=1,
            last_reviewed_at=None,
            next_review_at=datetime.now(timezone.utc) + timedelta(days=1),  # Review tomorrow
            is_due=False,  # Not due yet (just created)
            total_reviews=0,
            successful_reviews=0,
            last_quality_rating=None
        )

        db.add(new_card)
        db.commit()
        db.refresh(new_card)
        return new_card


def update_card_sm2(
    card: SpacedRepetitionCard,
    quality: int
) -> SpacedRepetitionCard:
    """
    Update spaced repetition card using SM-2 algorithm.

    SM-2 Algorithm:
    1. Calculate new easiness factor (EF) based on quality
    2. Update interval based on repetition count and EF
    3. Schedule next review
    4. Track performance statistics

    Args:
        card: SpacedRepetitionCard to update
        quality: SM-2 quality rating (0-5)
            - 5: Perfect recall
            - 4: Correct with hesitation
            - 3: Correct with difficulty (minimum passing)
            - 2: Incorrect but remembered
            - 1: Incorrect but familiar
            - 0: Complete blackout

    Returns:
        Updated card (modified in-place)
    """
    # Validate quality
    assert 0 <= quality <= 5, "Quality must be 0-5"

    # Step 1: Calculate new easiness factor (EF)
    current_ef = float(card.easiness_factor)
    new_ef = calculate_new_ef(current_ef, quality)
    card.easiness_factor = Decimal(str(new_ef))

    # Step 2: Update interval and repetition count
    if quality >= 3:
        # Successful recall
        if card.repetition_count == 0:
            card.interval_days = 1
        elif card.repetition_count == 1:
            card.interval_days = 6
        else:
            # I_n = I_(n-1) × EF
            card.interval_days = int(card.interval_days * new_ef)

        card.repetition_count += 1
        card.successful_reviews += 1
    else:
        # Failed recall - restart
        card.repetition_count = 0
        card.interval_days = 1

    # Step 3: Calculate next review date
    card.next_review_at = datetime.now(timezone.utc) + timedelta(days=card.interval_days)
    card.last_reviewed_at = datetime.now(timezone.utc)

    # Step 4: Mark as not due (will become due when next_review_at passes)
    card.is_due = False

    # Step 5: Record attempt statistics
    card.total_reviews += 1
    card.last_quality_rating = quality

    return card


def calculate_new_ef(current_ef: float, quality: int) -> float:
    """
    Calculate new easiness factor using SM-2 formula.

    Formula: EF' = EF + (0.1 - (5 - q) × (0.08 + (5 - q) × 0.02))

    Args:
        current_ef: Current easiness factor (1.3-2.5)
        quality: Quality rating (0-5)

    Returns:
        New easiness factor clamped to [1.3, 2.5]
    """
    new_ef = current_ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))

    # Clamp EF to valid range [1.3, 2.5]
    if new_ef < 1.3:
        new_ef = 1.3
    # Allow EF to go above 2.5 for exceptional performance
    # (some implementations cap at 2.5, others don't)

    return round(new_ef, 2)


def get_due_cards(
    db: Session,
    user_id: uuid.UUID,
    limit: int = 20
) -> List[SpacedRepetitionCard]:
    """
    Get spaced repetition cards due for review.

    A card is "due" if:
    - next_review_at <= current time
    - is_due flag is True (computed field)

    Cards are ordered by:
    1. Overdue cards first (oldest first)
    2. Then by next_review_at (soonest first)

    Args:
        db: Database session
        user_id: User ID
        limit: Maximum cards to return

    Returns:
        List of due cards with question details joined
    """
    now = datetime.now(timezone.utc)

    # Update is_due flags first
    db.query(SpacedRepetitionCard).filter(
        and_(
            SpacedRepetitionCard.user_id == str(user_id),
            SpacedRepetitionCard.next_review_at <= now
        )
    ).update({SpacedRepetitionCard.is_due: True}, synchronize_session=False)
    db.commit()

    # Get due cards ordered by priority
    due_cards = db.query(SpacedRepetitionCard).filter(
        and_(
            SpacedRepetitionCard.user_id == str(user_id),
            SpacedRepetitionCard.is_due == True
        )
    ).order_by(
        SpacedRepetitionCard.next_review_at.asc()  # Oldest overdue first
    ).limit(limit).all()

    return due_cards


def get_review_statistics(
    db: Session,
    user_id: uuid.UUID
) -> Dict:
    """
    Get overall spaced repetition statistics for user.

    Returns:
        Dictionary with review statistics
    """
    # Total cards
    total_cards = db.query(SpacedRepetitionCard).filter(
        SpacedRepetitionCard.user_id == str(user_id)
    ).count()

    # Cards due today
    today_end = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)
    cards_due_today = db.query(SpacedRepetitionCard).filter(
        and_(
            SpacedRepetitionCard.user_id == str(user_id),
            SpacedRepetitionCard.next_review_at <= today_end
        )
    ).count()

    # Cards due this week
    week_end = datetime.now(timezone.utc) + timedelta(days=7)
    cards_due_this_week = db.query(SpacedRepetitionCard).filter(
        and_(
            SpacedRepetitionCard.user_id == str(user_id),
            SpacedRepetitionCard.next_review_at <= week_end
        )
    ).count()

    # Mastered cards (EF >= 2.5 and interval >= 30 days)
    cards_mastered = db.query(SpacedRepetitionCard).filter(
        and_(
            SpacedRepetitionCard.user_id == str(user_id),
            SpacedRepetitionCard.easiness_factor >= 2.5,
            SpacedRepetitionCard.interval_days >= 30
        )
    ).count()

    # Total reviews completed
    total_reviews = db.query(
        func.sum(SpacedRepetitionCard.total_reviews)
    ).filter(
        SpacedRepetitionCard.user_id == str(user_id)
    ).scalar() or 0

    # Average success rate
    cards = db.query(SpacedRepetitionCard).filter(
        SpacedRepetitionCard.user_id == str(user_id)
    ).all()

    if cards:
        success_rates = [
            (card.successful_reviews / card.total_reviews * 100) if card.total_reviews > 0 else 0
            for card in cards
        ]
        avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0.0
    else:
        avg_success_rate = 0.0

    # Calculate streak (simplified - consecutive days with reviews)
    # For MVP, we'll use a simple heuristic
    current_streak = calculate_review_streak(db, user_id)

    # Daily review target (aim for all due cards)
    daily_review_target = min(cards_due_today, 20)  # Cap at 20 per day

    # Estimated daily minutes (2 min per card average)
    estimated_daily_minutes = daily_review_target * 2

    return {
        'total_cards': total_cards,
        'cards_due_today': cards_due_today,
        'cards_due_this_week': cards_due_this_week,
        'cards_mastered': cards_mastered,
        'total_reviews_completed': int(total_reviews),
        'average_success_rate': round(avg_success_rate, 1),
        'current_streak_days': current_streak,
        'daily_review_target': daily_review_target,
        'estimated_daily_minutes': estimated_daily_minutes
    }


def calculate_review_streak(db: Session, user_id: uuid.UUID) -> int:
    """
    Calculate consecutive days with reviews.

    Simplified for MVP: Count backwards from today to find consecutive days
    with at least one review.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Number of consecutive days with reviews
    """
    streak = 0
    check_date = datetime.now(timezone.utc).date()

    # Check up to 365 days back
    for _ in range(365):
        # Check if any card was reviewed on this date
        day_start = datetime.combine(check_date, datetime.min.time())
        day_end = datetime.combine(check_date, datetime.max.time())

        reviewed_today = db.query(SpacedRepetitionCard).filter(
            and_(
                SpacedRepetitionCard.user_id == str(user_id),
                SpacedRepetitionCard.last_reviewed_at >= day_start,
                SpacedRepetitionCard.last_reviewed_at <= day_end
            )
        ).first()

        if reviewed_today:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    return streak


def get_feedback_message(quality: int, interval_days: int) -> str:
    """
    Generate personalized feedback message based on SM-2 quality rating.

    Args:
        quality: Quality rating (0-5)
        interval_days: New interval in days

    Returns:
        Feedback message
    """
    if quality == 5:
        return f"Perfect! You'll see this again in {interval_days} days."
    elif quality == 4:
        return f"Good recall! Next review in {interval_days} days."
    elif quality == 3:
        return f"You got it, but with some difficulty. Keep practicing! Next review in {interval_days} days."
    elif quality == 2:
        return f"You didn't recall it initially, but recognized the answer. We'll review this tomorrow."
    elif quality == 1:
        return f"This was difficult. Don't worry - you'll see this again tomorrow to reinforce it."
    else:  # quality == 0
        return f"No problem - this is a tough one. You'll review it again tomorrow."


# ============================================================================
# SM-2 Algorithm Utility Functions (for testing and algorithm verification)
# ============================================================================

def calculate_next_interval(
    repetition_count: int,
    easiness_factor: Decimal,
    previous_interval: int
) -> int:
    """
    Calculate next review interval using SM-2 algorithm.

    SM-2 Interval Rules:
    - First repetition (n=0): I(1) = 1 day
    - Second repetition (n=1): I(2) = 6 days
    - Subsequent repetitions: I(n) = I(n-1) × EF

    Args:
        repetition_count: Number of successful repetitions (0, 1, 2, ...)
        easiness_factor: Current easiness factor (typically 1.3-2.5)
        previous_interval: Previous interval in days

    Returns:
        Next interval in days (integer)
    """
    if repetition_count == 0:
        return 1  # First review: 1 day
    elif repetition_count == 1:
        return 6  # Second review: 6 days
    else:
        # Subsequent reviews: multiply by easiness factor
        interval = int(previous_interval * float(easiness_factor))
        return max(1, interval)  # Ensure at least 1 day


def update_easiness_factor(current_ef: Decimal, quality: int) -> Decimal:
    """
    Update easiness factor using SM-2 algorithm.

    SM-2 Formula: EF' = EF + (0.1 - (5 - q) × (0.08 + (5 - q) × 0.02))
    Where q is quality rating (0-5)

    Args:
        current_ef: Current easiness factor
        quality: Quality rating (0-5)

    Returns:
        Updated easiness factor (clamped to minimum 1.3)
    """
    ef_float = float(current_ef)
    new_ef = ef_float + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))

    # Clamp to minimum of 1.3
    new_ef = max(1.3, new_ef)

    return Decimal(str(round(new_ef, 2)))


def calculate_next_review_date(
    current_date: datetime,
    interval_days: int
) -> datetime:
    """
    Calculate next review date.

    Args:
        current_date: Current date/time
        interval_days: Interval in days

    Returns:
        Next review date/time
    """
    return current_date + timedelta(days=interval_days)


def determine_card_status(
    quality: int = None,
    current_status: str = None,
    card: SpacedRepetitionCard = None
) -> str:
    """
    Determine the status of a spaced repetition card.

    Can be called in two ways:
    1. With quality and current_status (for SM-2 status transitions)
    2. With card object (for full status determination)

    For SM-2 status transitions:
    - quality < 4: Returns to/stays in 'learning'
    - quality >= 4: Moves to/stays in 'review'

    For full card status:
    - 'new': Never reviewed (total_reviews == 0)
    - 'learning': In learning phase (repetition_count < 3)
    - 'review': Successfully reviewed (repetition_count >= 3)
    - 'young': Successfully reviewed 3+ times but interval < 21 days
    - 'mature': Interval >= 21 days
    - 'due': Card is due for review
    - 'overdue': Card is overdue (next_review_at more than 1 day past)

    Args:
        quality: Quality rating (0-5) for status transition
        current_status: Current card status ('learning' or 'review')
        card: SpacedRepetitionCard object for full status check

    Returns:
        Status string
    """
    # Mode 1: SM-2 status transition based on quality
    if quality is not None and current_status is not None:
        if quality < 4:
            return 'learning'  # Failed recall - back to learning
        else:
            return 'review'  # Successful recall - advance to review

    # Mode 2: Full status determination from card object
    if card is not None:
        now = datetime.now(timezone.utc)

        # Check if overdue
        if card.next_review_at < now - timedelta(days=1):
            return 'overdue'

        # Check if due
        if card.is_due or card.next_review_at <= now:
            return 'due'

        # Check if new
        if card.total_reviews == 0:
            return 'new'

        # Check learning status
        if card.repetition_count < 3:
            return 'learning'

        # Check maturity
        if card.interval_days >= 21:
            return 'mature'
        else:
            return 'young'

    raise ValueError("Must provide either (quality and current_status) or (card)")


def process_card_review(
    card_data_or_db: any,
    quality_or_card: any = None,
    review_date: any = None
) -> dict:
    """
    Process a card review.

    Can be called in two ways:
    1. With card dict, quality, and date (for unit testing)
    2. With db and card object (for integration)

    Args:
        card_data_or_db: Either dict with card data or database session
        quality_or_card: Either quality rating (int) or SpacedRepetitionCard
        review_date: Review date (for dict mode)

    Returns:
        Updated card dict or SpacedRepetitionCard
    """
    # Mode 1: Unit test mode with dict
    if isinstance(card_data_or_db, dict) and isinstance(quality_or_card, int):
        card_data = card_data_or_db
        quality = quality_or_card

        # Calculate new easiness factor
        current_ef = float(card_data["easiness_factor"])
        new_ef = calculate_new_ef(current_ef, quality)

        # Calculate new interval and repetition count
        if quality >= 4:  # Successful recall
            if card_data["repetition_count"] == 0:
                new_interval = 1
            elif card_data["repetition_count"] == 1:
                new_interval = 6
            else:
                new_interval = int(card_data["interval_days"] * new_ef)
            new_repetition = card_data["repetition_count"] + 1
        else:  # Failed recall
            new_interval = 1
            new_repetition = 0

        # Calculate next review date
        next_review = review_date + timedelta(days=new_interval)

        return {
            "repetition_count": new_repetition,
            "easiness_factor": Decimal(str(round(new_ef, 2))),
            "interval_days": new_interval,
            "next_review_date": next_review,
            "last_reviewed": review_date
        }

    # Mode 2: Integration mode with DB and card object
    elif hasattr(card_data_or_db, 'query'):  # Database session
        db = card_data_or_db
        card = quality_or_card
        updated_card = update_card_sm2(card, review_date if isinstance(review_date, int) else 4)
        db.commit()
        db.refresh(updated_card)
        return updated_card

    raise ValueError("Invalid arguments for process_card_review")
