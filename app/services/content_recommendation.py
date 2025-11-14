"""
Content Recommendation Service.

Provides personalized content recommendations using:
1. User competency scores (weakest KAs prioritized)
2. Vector similarity search (semantic matching)
3. Content quality scores (expert-reviewed, helpfulness)

Decision #23: Reading content essential for learning.
Decision #76: Quality evaluation system.
"""
from typing import List, Optional, Dict
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text
from app.models.content import ContentChunk
from app.models.learning import UserCompetency, QuestionAttempt
from app.models.user import User


def get_user_weakest_knowledge_areas(
    db: Session,
    user_id: UUID,
    course_id: UUID,
    limit: int = 3
) -> List[Dict[str, any]]:
    """
    Get user's weakest knowledge areas based on competency scores.

    Args:
        db: Database session
        user_id: User ID
        course_id: Course ID
        limit: Number of weakest KAs to return

    Returns:
        List of dicts with ka_id and competency_score
    """
    competencies = db.query(UserCompetency).filter(
        UserCompetency.user_id == user_id,
        UserCompetency.course_id == course_id
    ).order_by(UserCompetency.competency_score.asc()).limit(limit).all()

    return [
        {
            "ka_id": c.ka_id,
            "competency_score": float(c.competency_score),
            "ka_code": c.knowledge_area.ka_code if c.knowledge_area else None,
            "ka_name": c.knowledge_area.ka_name if c.knowledge_area else None
        }
        for c in competencies
    ]


def get_content_recommendations_by_competency(
    db: Session,
    user_id: UUID,
    course_id: UUID,
    limit: int = 5
) -> List[ContentChunk]:
    """
    Get content recommendations based on user's weakest KAs.

    Strategy:
    1. Identify user's 3 weakest knowledge areas
    2. Retrieve active, approved content from those KAs
    3. Prioritize expert-reviewed content
    4. Return most relevant chunks

    Args:
        db: Database session
        user_id: User ID
        course_id: Course ID
        limit: Number of recommendations to return

    Returns:
        List of ContentChunk objects
    """
    # Get weakest KAs
    weak_kas = get_user_weakest_knowledge_areas(db, user_id, course_id, limit=3)

    if not weak_kas:
        # No competency data yet - return general introductory content
        chunks = db.query(ContentChunk).filter(
            ContentChunk.course_id == course_id,
            ContentChunk.is_active == True,
            ContentChunk.review_status == 'approved',
            ContentChunk.difficulty_level == 'basic'
        ).order_by(
            ContentChunk.expert_reviewed.desc(),
            ContentChunk.created_at.desc()
        ).limit(limit).all()
        return chunks

    # Get KA IDs
    ka_ids = [ka["ka_id"] for ka in weak_kas]

    # Query active, approved content from weakest KAs
    chunks = db.query(ContentChunk).filter(
        ContentChunk.course_id == course_id,
        ContentChunk.ka_id.in_(ka_ids),
        ContentChunk.is_active == True,
        ContentChunk.review_status == 'approved'
    ).order_by(
        ContentChunk.expert_reviewed.desc(),  # Prioritize expert-reviewed
        ContentChunk.source_verified.desc(),  # Then source-verified
        ContentChunk.created_at.desc()  # Then newest
    ).limit(limit).all()

    return chunks


def get_content_by_semantic_search(
    db: Session,
    query_embedding: List[float],
    course_id: UUID,
    ka_id: Optional[UUID] = None,
    limit: int = 5
) -> List[ContentChunk]:
    """
    Perform vector similarity search for content chunks.

    Uses cosine similarity (via pgvector's <=> operator).

    Args:
        db: Database session
        query_embedding: Query vector (3072 dimensions from OpenAI)
        course_id: Course ID to filter by
        ka_id: Optional KA ID to filter by
        limit: Number of results to return

    Returns:
        List of ContentChunk objects ordered by similarity
    """
    from sqlalchemy import text

    # Build query filters
    filters = [
        ContentChunk.course_id == course_id,
        ContentChunk.is_active == True,
        ContentChunk.review_status == 'approved',
        ContentChunk.embedding.isnot(None)  # Ensure embedding exists
    ]

    if ka_id:
        filters.append(ContentChunk.ka_id == ka_id)

    # Perform vector similarity search
    # pgvector's <=> operator calculates cosine distance (lower = more similar)
    chunks = db.query(ContentChunk).filter(
        and_(*filters)
    ).order_by(
        ContentChunk.embedding.cosine_distance(query_embedding)
    ).limit(limit).all()

    return chunks


def get_content_for_recent_mistakes(
    db: Session,
    user_id: UUID,
    course_id: UUID,
    limit: int = 5
) -> List[ContentChunk]:
    """
    Get content recommendations based on recent incorrect answers.

    Strategy:
    1. Find recent questions user got wrong
    2. Identify KAs/domains from those questions
    3. Recommend content from those areas

    Args:
        db: Database session
        user_id: User ID
        course_id: Course ID
        limit: Number of recommendations

    Returns:
        List of ContentChunk objects
    """
    # Get last 20 incorrect attempts
    recent_incorrect = db.query(QuestionAttempt).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.is_correct == False
    ).order_by(
        QuestionAttempt.created_at.desc()
    ).limit(20).all()

    if not recent_incorrect:
        # No recent mistakes - use competency-based recommendations
        return get_content_recommendations_by_competency(db, user_id, course_id, limit)

    # Extract KA and domain IDs from incorrect attempts
    ka_ids = set()
    domain_ids = set()

    for attempt in recent_incorrect:
        if attempt.question:
            ka_ids.add(attempt.question.ka_id)
            if attempt.question.domain_id:
                domain_ids.add(attempt.question.domain_id)

    # Build query for content from these areas
    filters = [
        ContentChunk.course_id == course_id,
        ContentChunk.is_active == True,
        ContentChunk.review_status == 'approved'
    ]

    if domain_ids:
        # Prioritize content from specific domains where mistakes occurred
        filters.append(
            or_(
                ContentChunk.domain_id.in_(domain_ids),
                ContentChunk.ka_id.in_(ka_ids)
            )
        )
    elif ka_ids:
        filters.append(ContentChunk.ka_id.in_(ka_ids))

    chunks = db.query(ContentChunk).filter(
        and_(*filters)
    ).order_by(
        ContentChunk.domain_id.in_(domain_ids).desc() if domain_ids else text('1'),  # Domain-specific first
        ContentChunk.expert_reviewed.desc(),
        ContentChunk.source_verified.desc(),
        ContentChunk.created_at.desc()
    ).limit(limit).all()

    return chunks


def get_recommended_content(
    db: Session,
    user_id: UUID,
    course_id: UUID,
    strategy: str = "adaptive",
    ka_id: Optional[UUID] = None,
    query_embedding: Optional[List[float]] = None,
    limit: int = 5
) -> List[ContentChunk]:
    """
    Get personalized content recommendations.

    Supports multiple recommendation strategies:
    - "adaptive": Based on competency scores (default)
    - "recent_mistakes": Based on recent incorrect answers
    - "semantic": Based on vector similarity (requires query_embedding)
    - "ka_specific": Content from specific KA (requires ka_id)

    Args:
        db: Database session
        user_id: User ID
        course_id: Course ID
        strategy: Recommendation strategy
        ka_id: Optional KA ID for KA-specific recommendations
        query_embedding: Optional query vector for semantic search
        limit: Number of recommendations

    Returns:
        List of ContentChunk objects

    Raises:
        ValueError: If strategy is invalid or required params missing
    """
    if strategy == "adaptive":
        return get_content_recommendations_by_competency(db, user_id, course_id, limit)

    elif strategy == "recent_mistakes":
        return get_content_for_recent_mistakes(db, user_id, course_id, limit)

    elif strategy == "semantic":
        if query_embedding is None:
            raise ValueError("query_embedding required for semantic search strategy")
        return get_content_by_semantic_search(db, query_embedding, course_id, ka_id, limit)

    elif strategy == "ka_specific":
        if ka_id is None:
            raise ValueError("ka_id required for KA-specific strategy")
        chunks = db.query(ContentChunk).filter(
            ContentChunk.course_id == course_id,
            ContentChunk.ka_id == ka_id,
            ContentChunk.is_active == True,
            ContentChunk.review_status == 'approved'
        ).order_by(
            ContentChunk.expert_reviewed.desc(),
            ContentChunk.difficulty_level.desc(),  # Advanced first
            ContentChunk.created_at.desc()
        ).limit(limit).all()
        return chunks

    else:
        raise ValueError(f"Invalid strategy: {strategy}. Choose from: adaptive, recent_mistakes, semantic, ka_specific")


def get_chunk_by_id(db: Session, chunk_id: UUID) -> Optional[ContentChunk]:
    """
    Get a specific content chunk by ID.

    Only returns active, approved content.

    Args:
        db: Database session
        chunk_id: Content chunk ID

    Returns:
        ContentChunk object or None if not found/not active
    """
    chunk = db.query(ContentChunk).filter(
        ContentChunk.chunk_id == str(chunk_id),
        ContentChunk.is_active == True,
        ContentChunk.review_status == 'approved'
    ).first()

    return chunk
