"""
Competency service.

Handles IRT-based competency tracking and updates.
Decision #3: Adaptive learning with IRT.
Decision #18: Competency estimation.
Decision #22: Simplified IRT approach for MVP (correct/total per KA).
"""
from typing import List, Dict
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.learning import UserCompetency, QuestionAttempt
from app.models.course import KnowledgeArea
import uuid


def initialize_user_competencies(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID
) -> List[UserCompetency]:
    """
    Initialize competency tracking for all KAs in a course.
    
    Decision #18: Start all users at 0.50 competency (50% - neutral starting point).
    
    Args:
        db: Database session
        user_id: User ID
        course_id: Course ID
        
    Returns:
        List of created UserCompetency records
    """
    # Get all KAs for the course
    knowledge_areas = db.query(KnowledgeArea).filter(
        KnowledgeArea.course_id == course_id
    ).all()
    
    competencies = []
    for ka in knowledge_areas:
        competency = UserCompetency(
            user_id=user_id,
            ka_id=ka.ka_id,
            competency_score=Decimal('0.50'),  # Start at neutral 50%
            standard_error=None,
            attempts_count=0,
            correct_count=0,
            incorrect_count=0
        )
        db.add(competency)
        competencies.append(competency)
    
    db.commit()
    
    # Refresh all competencies
    for comp in competencies:
        db.refresh(comp)
    
    return competencies


def get_user_competencies(
    db: Session,
    user_id: uuid.UUID
) -> List[UserCompetency]:
    """
    Get all competencies for a user.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        List of UserCompetency records
    """
    return db.query(UserCompetency).filter(
        UserCompetency.user_id == user_id
    ).all()


def get_weakest_ka(
    db: Session,
    user_id: uuid.UUID
) -> UserCompetency:
    """
    Get user's weakest knowledge area (lowest competency score).
    
    Used for adaptive question selection.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        UserCompetency with lowest score
    """
    return db.query(UserCompetency).filter(
        UserCompetency.user_id == user_id
    ).order_by(UserCompetency.competency_score.asc()).first()


def update_competency_after_attempt(
    db: Session,
    user_id: uuid.UUID,
    ka_id: uuid.UUID,
    is_correct: bool,
    question_difficulty: Decimal
) -> UserCompetency:
    """
    Update user competency after question attempt.
    
    Decision #18: Simple IRT update for MVP.
    Future: Full 1PL IRT implementation with maximum likelihood estimation.
    
    Current implementation: Simple weighted average based on difficulty.
    
    Args:
        db: Database session
        user_id: User ID
        ka_id: KA ID
        is_correct: Whether answer was correct
        question_difficulty: Question difficulty (0-1)
        
    Returns:
        Updated UserCompetency
    """
    competency = db.query(UserCompetency).filter(
        UserCompetency.user_id == user_id,
        UserCompetency.ka_id == ka_id
    ).first()
    
    if not competency:
        # Create if doesn't exist
        competency = UserCompetency(
            user_id=user_id,
            ka_id=ka_id,
            competency_score=Decimal('0.50'),
            attempts_count=0,
            correct_count=0,
            incorrect_count=0
        )
        db.add(competency)

    # Update attempt counts
    competency.attempts_count += 1
    if is_correct:
        competency.correct_count += 1
    else:
        competency.incorrect_count += 1
    
    # Simple competency update (MVP version)
    # If correct: increase score slightly, weighted by difficulty
    # If incorrect: decrease score slightly, weighted by difficulty
    learning_rate = Decimal('0.1')  # How much to adjust per question
    
    if is_correct:
        # Correct answer: move competency toward question difficulty
        # If question was harder than competency, increase more
        adjustment = (question_difficulty - competency.competency_score) * learning_rate
        competency.competency_score += adjustment
    else:
        # Incorrect answer: move competency downward
        # If question was easier than competency, decrease more
        adjustment = (competency.competency_score - question_difficulty) * learning_rate
        competency.competency_score -= adjustment
    
    # Clamp competency score to [0, 1]
    competency.competency_score = max(Decimal('0.00'), min(Decimal('1.00'), competency.competency_score))
    
    # Note: last_updated_at is automatically updated by onupdate=func.now()

    db.commit()
    db.refresh(competency)

    return competency


def calculate_diagnostic_competencies(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID
) -> List[UserCompetency]:
    """
    Calculate and store initial competencies after diagnostic assessment.

    Decision #22: Simplified IRT approach - correct/total ratio per KA.
    Formula: competency_score = correct_count / total_count

    Args:
        db: Database session
        user_id: User ID
        session_id: Diagnostic session ID

    Returns:
        List of updated UserCompetency records
    """
    # Get all question attempts from this diagnostic session
    attempts = db.query(QuestionAttempt).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.session_id == session_id
    ).all()

    # Group attempts by KA
    ka_stats: Dict[str, Dict] = {}
    for attempt in attempts:
        # Get question to find KA
        ka_id = str(attempt.question.ka_id)

        if ka_id not in ka_stats:
            ka_stats[ka_id] = {
                'total': 0,
                'correct': 0,
                'incorrect': 0
            }

        ka_stats[ka_id]['total'] += 1
        if attempt.is_correct:
            ka_stats[ka_id]['correct'] += 1
        else:
            ka_stats[ka_id]['incorrect'] += 1

    # Update or create competency records
    updated_competencies = []
    for ka_id_str, stats in ka_stats.items():
        # Calculate competency score (simple ratio)
        # Decision #22: competency = correct / total
        competency_score = Decimal(stats['correct']) / Decimal(stats['total'])

        # Get or create competency record
        competency = db.query(UserCompetency).filter(
            UserCompetency.user_id == user_id,
            UserCompetency.ka_id == ka_id_str
        ).first()

        if not competency:
            competency = UserCompetency(
                user_id=user_id,
                ka_id=ka_id_str,
                competency_score=competency_score,
                attempts_count=stats['total'],
                correct_count=stats['correct'],
                incorrect_count=stats['incorrect']
            )
            db.add(competency)
        else:
            competency.competency_score = competency_score
            competency.attempts_count = stats['total']
            competency.correct_count = stats['correct']
            competency.incorrect_count = stats['incorrect']

        updated_competencies.append(competency)

    db.commit()

    # Refresh all competencies
    for comp in updated_competencies:
        db.refresh(comp)

    return updated_competencies


def calculate_weighted_competency(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID
) -> Decimal:
    """
    Calculate overall weighted competency across all KAs.

    Uses KA weight percentages to compute weighted average.

    Args:
        db: Database session
        user_id: User ID
        course_id: Course ID

    Returns:
        Weighted average competency (0.00-1.00)
    """
    # Get all competencies for user
    competencies = db.query(UserCompetency).filter(
        UserCompetency.user_id == user_id
    ).all()

    if not competencies:
        return Decimal('0.00')

    # Calculate weighted average
    weighted_sum = Decimal('0.00')
    total_weight = Decimal('0.00')

    for comp in competencies:
        ka = db.query(KnowledgeArea).filter(
            KnowledgeArea.ka_id == comp.ka_id,
            KnowledgeArea.course_id == course_id
        ).first()

        if ka:
            weight = ka.weight_percentage / Decimal('100.0')
            weighted_sum += comp.competency_score * weight
            total_weight += weight

    if total_weight == Decimal('0.00'):
        return Decimal('0.00')

    return weighted_sum / total_weight


def determine_competency_status(competency_score: Decimal) -> str:
    """
    Determine competency status based on score.

    Thresholds:
    - below_target: < 0.60 (60%)
    - on_track: 0.60 - 0.79 (60-79%)
    - above_target: >= 0.80 (80%+)

    Args:
        competency_score: Score from 0.00 to 1.00

    Returns:
        Status string: 'below_target', 'on_track', or 'above_target'
    """
    if competency_score < Decimal('0.60'):
        return 'below_target'
    elif competency_score < Decimal('0.80'):
        return 'on_track'
    else:
        return 'above_target'


# ============================================================================
# IRT Calculation Utility Functions (for testing and algorithm verification)
# ============================================================================

def calculate_probability_correct(competency: Decimal, difficulty: Decimal) -> Decimal:
    """
    Calculate probability of correct answer using 1PL IRT model.

    1PL IRT Formula: P(correct) = 1 / (1 + exp(-(competency - difficulty)))

    Args:
        competency: User's competency score (0.0-1.0)
        difficulty: Question difficulty (0.0-1.0)

    Returns:
        Probability of correct answer (0.0-1.0)
    """
    import math

    # Scale to IRT logit scale (typically -3 to +3)
    # Map 0-1 range to approximately -3 to +3
    competency_logit = (float(competency) - 0.5) * 6
    difficulty_logit = (float(difficulty) - 0.5) * 6

    # 1PL IRT: P = 1 / (1 + exp(-(theta - beta)))
    exponent = -(competency_logit - difficulty_logit)

    try:
        probability = 1.0 / (1.0 + math.exp(exponent))
    except OverflowError:
        # Handle extreme values
        probability = 0.0 if exponent > 0 else 1.0

    # Clamp to valid probability range
    probability = max(0.0, min(1.0, probability))

    return Decimal(str(round(probability, 4)))


def update_competency_score(
    current_competency: Decimal,
    question_difficulty: Decimal,
    is_correct: bool
) -> Decimal:
    """
    Update competency score after a question attempt.

    Simplified IRT-inspired update for MVP.
    - Correct answer: always increases competency (weighted by difficulty)
    - Incorrect answer: always decreases competency (weighted by difficulty)
    - Harder questions cause bigger changes

    Args:
        current_competency: Current competency score (0.0-1.0)
        question_difficulty: Question difficulty (0.0-1.0)
        is_correct: Whether the answer was correct

    Returns:
        Updated competency score (0.0-1.0)
    """
    base_learning_rate = Decimal('0.1')  # Base adjustment per question

    if is_correct:
        # Correct answer: always increase competency
        # Harder questions (higher difficulty) → larger increase
        # Learning rate scales with difficulty (0.5 to 1.5x)
        scale_factor = Decimal('0.5') + question_difficulty
        adjustment = base_learning_rate * scale_factor
        new_competency = current_competency + adjustment
    else:
        # Incorrect answer: always decrease competency
        # Easier questions (lower difficulty) → larger decrease (indicates bigger problem)
        # Harder questions → smaller decrease (more forgivable)
        scale_factor = Decimal('1.5') - question_difficulty
        adjustment = base_learning_rate * scale_factor
        new_competency = current_competency - adjustment

    # Clamp to valid range [0.0, 1.0]
    new_competency = max(Decimal('0.00'), min(Decimal('1.00'), new_competency))

    return new_competency


def estimate_initial_competency(
    preparation_level: str,
    has_experience: bool
) -> Decimal:
    """
    Estimate initial competency based on user's self-reported preparation level.

    Used during onboarding to set starting competency scores.

    Args:
        preparation_level: 'beginner', 'intermediate', or 'advanced'
        has_experience: Whether user has prior experience in the field

    Returns:
        Initial competency score (0.0-1.0)
    """
    base_competency = {
        'beginner': Decimal('0.30'),
        'intermediate': Decimal('0.50'),
        'advanced': Decimal('0.70')
    }

    # Default to intermediate if unknown level
    competency = base_competency.get(preparation_level, Decimal('0.50'))

    # Add bonus for prior experience
    if has_experience:
        competency += Decimal('0.10')

    # Clamp to valid range
    competency = max(Decimal('0.00'), min(Decimal('1.00'), competency))

    return competency


def get_competency_level(competency_score: Decimal) -> str:
    """
    Classify competency score into a descriptive level.

    Levels:
    - novice: 0.00-0.39 (0-39%)
    - beginner: 0.40-0.59 (40-59%)
    - intermediate: 0.60-0.69 (60-69%)
    - advanced: 0.70-0.79 (70-79%)
    - expert: 0.80-1.00 (80-100%)

    Args:
        competency_score: Score from 0.00 to 1.00

    Returns:
        Level string: 'novice', 'beginner', 'intermediate', 'advanced', or 'expert'
    """
    if competency_score < Decimal('0.40'):
        return 'novice'
    elif competency_score < Decimal('0.60'):
        return 'beginner'
    elif competency_score < Decimal('0.70'):
        return 'intermediate'
    elif competency_score < Decimal('0.80'):
        return 'advanced'
    else:
        return 'expert'
