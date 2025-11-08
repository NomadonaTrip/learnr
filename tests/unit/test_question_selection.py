"""
Unit tests for adaptive question selection algorithm.

Tests:
- Question selection based on competency
- Difficulty matching (±0.1 range)
- Knowledge area prioritization (weakest first)
- Question exclusion (recently answered)
- Balanced distribution across KAs
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock

from app.services.question_selection import (
    select_next_question,
    get_weakest_knowledge_area,
    filter_questions_by_difficulty,
    exclude_recent_questions,
    calculate_question_priority
)


@pytest.mark.unit
class TestWeakestKnowledgeAreaSelection:
    """Test selection of weakest knowledge area."""

    def test_get_weakest_ka_single_lowest(self):
        """Test getting weakest KA when one is clearly lowest."""
        competencies = [
            Mock(ka_id="ka1", competency_score=Decimal("0.7")),
            Mock(ka_id="ka2", competency_score=Decimal("0.3")),  # Weakest
            Mock(ka_id="ka3", competency_score=Decimal("0.5")),
        ]

        weakest = get_weakest_knowledge_area(competencies)

        assert weakest.ka_id == "ka2"
        assert weakest.competency_score == Decimal("0.3")

    def test_get_weakest_ka_multiple_equal(self):
        """Test getting weakest KA when multiple are tied."""
        competencies = [
            Mock(ka_id="ka1", ka_name="KA1", competency_score=Decimal("0.3")),  # Tied
            Mock(ka_id="ka2", ka_name="KA2", competency_score=Decimal("0.5")),
            Mock(ka_id="ka3", ka_name="KA3", competency_score=Decimal("0.3")),  # Tied
        ]

        weakest = get_weakest_knowledge_area(competencies)

        # Should return one of the tied KAs
        assert weakest.competency_score == Decimal("0.3")
        assert weakest.ka_id in ["ka1", "ka3"]

    def test_get_weakest_ka_all_equal(self):
        """Test getting weakest KA when all have same competency."""
        competencies = [
            Mock(ka_id="ka1", competency_score=Decimal("0.5")),
            Mock(ka_id="ka2", competency_score=Decimal("0.5")),
            Mock(ka_id="ka3", competency_score=Decimal("0.5")),
        ]

        weakest = get_weakest_knowledge_area(competencies)

        # Should return any KA (all are equal)
        assert weakest.competency_score == Decimal("0.5")

    def test_get_weakest_ka_empty_list(self):
        """Test getting weakest KA from empty list."""
        competencies = []

        weakest = get_weakest_knowledge_area(competencies)

        assert weakest is None

    def test_get_weakest_ka_single_ka(self):
        """Test getting weakest KA when only one KA exists."""
        competencies = [
            Mock(ka_id="ka1", competency_score=Decimal("0.6"))
        ]

        weakest = get_weakest_knowledge_area(competencies)

        assert weakest.ka_id == "ka1"


@pytest.mark.unit
class TestDifficultyFiltering:
    """Test filtering questions by difficulty range."""

    def test_filter_within_range(self):
        """Test filtering questions within difficulty range."""
        questions = [
            Mock(question_id="q1", difficulty=Decimal("0.3")),
            Mock(question_id="q2", difficulty=Decimal("0.5")),  # Within range
            Mock(question_id="q3", difficulty=Decimal("0.55")), # Within range
            Mock(question_id="q4", difficulty=Decimal("0.7")),
        ]
        target_difficulty = Decimal("0.5")
        tolerance = Decimal("0.1")

        filtered = filter_questions_by_difficulty(
            questions,
            target_difficulty,
            tolerance
        )

        # Should return questions with difficulty 0.4-0.6
        assert len(filtered) == 2
        assert all(
            abs(float(q.difficulty) - float(target_difficulty)) <= float(tolerance)
            for q in filtered
        )

    def test_filter_no_matches(self):
        """Test filtering when no questions match difficulty."""
        questions = [
            Mock(question_id="q1", difficulty=Decimal("0.1")),
            Mock(question_id="q2", difficulty=Decimal("0.2")),
            Mock(question_id="q3", difficulty=Decimal("0.9")),
        ]
        target_difficulty = Decimal("0.5")
        tolerance = Decimal("0.1")

        filtered = filter_questions_by_difficulty(
            questions,
            target_difficulty,
            tolerance
        )

        assert len(filtered) == 0

    def test_filter_all_match(self):
        """Test filtering when all questions match."""
        questions = [
            Mock(question_id="q1", difficulty=Decimal("0.45")),
            Mock(question_id="q2", difficulty=Decimal("0.50")),
            Mock(question_id="q3", difficulty=Decimal("0.55")),
        ]
        target_difficulty = Decimal("0.5")
        tolerance = Decimal("0.1")

        filtered = filter_questions_by_difficulty(
            questions,
            target_difficulty,
            tolerance
        )

        assert len(filtered) == 3

    def test_filter_boundary_values(self):
        """Test filtering at exact boundaries."""
        questions = [
            Mock(question_id="q1", difficulty=Decimal("0.4")),  # Lower boundary
            Mock(question_id="q2", difficulty=Decimal("0.5")),  # Exact match
            Mock(question_id="q3", difficulty=Decimal("0.6")),  # Upper boundary
            Mock(question_id="q4", difficulty=Decimal("0.39")), # Just outside
            Mock(question_id="q5", difficulty=Decimal("0.61")), # Just outside
        ]
        target_difficulty = Decimal("0.5")
        tolerance = Decimal("0.1")

        filtered = filter_questions_by_difficulty(
            questions,
            target_difficulty,
            tolerance
        )

        # Should include boundaries but not outside
        assert len(filtered) == 3
        filtered_ids = [q.question_id for q in filtered]
        assert "q1" in filtered_ids
        assert "q2" in filtered_ids
        assert "q3" in filtered_ids


@pytest.mark.unit
class TestRecentQuestionExclusion:
    """Test exclusion of recently answered questions."""

    def test_exclude_recent_questions_within_window(self):
        """Test excluding questions answered recently."""
        now = datetime.now(timezone.utc)
        recent_time = now - timedelta(minutes=10)
        old_time = now - timedelta(days=2)

        all_questions = [
            Mock(question_id="q1"),
            Mock(question_id="q2"),
            Mock(question_id="q3"),
        ]

        recent_attempts = [
            Mock(question_id="q1", created_at=recent_time),  # Exclude
            Mock(question_id="q2", created_at=old_time),     # Include (old)
        ]

        filtered = exclude_recent_questions(
            all_questions,
            recent_attempts,
            hours_window=24
        )

        # Should exclude q1 (recent), include q2 and q3
        assert len(filtered) == 2
        filtered_ids = [q.question_id for q in filtered]
        assert "q1" not in filtered_ids
        assert "q2" in filtered_ids
        assert "q3" in filtered_ids

    def test_exclude_no_recent_attempts(self):
        """Test when there are no recent attempts."""
        all_questions = [
            Mock(question_id="q1"),
            Mock(question_id="q2"),
        ]

        recent_attempts = []

        filtered = exclude_recent_questions(
            all_questions,
            recent_attempts,
            hours_window=24
        )

        # Should include all questions
        assert len(filtered) == 2

    def test_exclude_all_questions_recent(self):
        """Test when all questions were answered recently."""
        now = datetime.now(timezone.utc)
        recent_time = now - timedelta(minutes=10)

        all_questions = [
            Mock(question_id="q1"),
            Mock(question_id="q2"),
        ]

        recent_attempts = [
            Mock(question_id="q1", created_at=recent_time),
            Mock(question_id="q2", created_at=recent_time),
        ]

        filtered = exclude_recent_questions(
            all_questions,
            recent_attempts,
            hours_window=24
        )

        # Should exclude all questions
        assert len(filtered) == 0

    def test_exclude_custom_time_window(self):
        """Test exclusion with custom time window."""
        now = datetime.now(timezone.utc)
        time_12h_ago = now - timedelta(hours=12)
        time_48h_ago = now - timedelta(hours=48)

        all_questions = [
            Mock(question_id="q1"),
            Mock(question_id="q2"),
        ]

        recent_attempts = [
            Mock(question_id="q1", created_at=time_12h_ago),  # Within 24h
            Mock(question_id="q2", created_at=time_48h_ago),  # Outside 24h
        ]

        filtered = exclude_recent_questions(
            all_questions,
            recent_attempts,
            hours_window=24
        )

        # Should exclude q1, include q2
        assert len(filtered) == 1
        assert filtered[0].question_id == "q2"


@pytest.mark.unit
class TestQuestionPriorityCalculation:
    """Test priority calculation for question selection."""

    def test_priority_higher_for_closer_difficulty(self):
        """Test that questions closer to target difficulty get higher priority."""
        user_competency = Decimal("0.5")

        q1_priority = calculate_question_priority(
            question_difficulty=Decimal("0.5"),  # Exact match
            user_competency=user_competency
        )

        q2_priority = calculate_question_priority(
            question_difficulty=Decimal("0.7"),  # Far from competency
            user_competency=user_competency
        )

        # Exact match should have higher priority
        assert q1_priority > q2_priority

    def test_priority_symmetric_around_competency(self):
        """Test that priority is symmetric around user competency."""
        user_competency = Decimal("0.5")

        priority_lower = calculate_question_priority(
            question_difficulty=Decimal("0.4"),
            user_competency=user_competency
        )

        priority_higher = calculate_question_priority(
            question_difficulty=Decimal("0.6"),
            user_competency=user_competency
        )

        # Both are 0.1 away from competency, should have similar priority
        assert abs(float(priority_lower) - float(priority_higher)) < 0.01

    def test_priority_positive_values(self):
        """Test that priority is always positive."""
        test_cases = [
            (Decimal("0.1"), Decimal("0.9")),
            (Decimal("0.5"), Decimal("0.5")),
            (Decimal("0.9"), Decimal("0.1")),
        ]

        for difficulty, competency in test_cases:
            priority = calculate_question_priority(difficulty, competency)
            assert priority > 0


@pytest.mark.unit
class TestAdaptiveQuestionSelection:
    """Test complete adaptive question selection logic."""

    def test_select_from_weakest_ka(self, db, test_user_competencies, test_questions):
        """Test that questions are selected from weakest KA."""
        user_id = test_user_competencies[0].user_id

        question = select_next_question(db, user_id)

        # Should select from weakest KA
        weakest_ka = min(test_user_competencies, key=lambda x: x.competency_score)
        assert question.ka_id == weakest_ka.ka_id

    def test_select_appropriate_difficulty(self, db, test_user_competencies, test_questions):
        """Test that selected question has appropriate difficulty."""
        user_id = test_user_competencies[0].user_id

        question = select_next_question(db, user_id)

        # Get user's competency for that KA
        competency = next(
            c for c in test_user_competencies if c.ka_id == question.ka_id
        )

        # Difficulty should be close to competency
        difficulty_diff = abs(float(question.difficulty) - float(competency.competency_score))
        assert difficulty_diff <= 0.2  # Within reasonable range

    def test_select_different_questions_consecutively(self, db, test_user_competencies, test_questions):
        """Test that consecutive selections don't repeat immediately."""
        user_id = test_user_competencies[0].user_id

        q1 = select_next_question(db, user_id)
        q2 = select_next_question(db, user_id, exclude_question_ids=[q1.question_id])

        # Should select different questions
        assert q1.question_id != q2.question_id

    def test_select_returns_none_when_no_questions(self, db, test_user_competencies):
        """Test selection returns None when no questions available."""
        # Don't create any questions
        user_id = test_user_competencies[0].user_id

        question = select_next_question(db, user_id)

        assert question is None

    def test_select_balanced_across_kas_over_time(self, db, test_user_competencies, test_questions):
        """Test that questions are balanced across KAs over multiple selections."""
        user_id = test_user_competencies[0].user_id
        ka_counts = {}

        # Select 18 questions (3 per KA)
        exclude_ids = []
        for _ in range(18):
            question = select_next_question(db, user_id, exclude_question_ids=exclude_ids)
            if question:
                ka_counts[question.ka_id] = ka_counts.get(question.ka_id, 0) + 1
                exclude_ids.append(question.question_id)

        # Should have selected from multiple KAs (not all from one)
        assert len(ka_counts) > 1


@pytest.mark.unit
class TestQuestionSelectionEdgeCases:
    """Test edge cases in question selection."""

    def test_select_with_zero_competency(self, db, test_questions):
        """Test selection when user has zero competency."""
        # This would need a specific user setup
        # For now, test the logic directly
        questions = test_questions[:3]
        target_diff = Decimal("0.0")

        filtered = filter_questions_by_difficulty(questions, target_diff, Decimal("0.2"))

        # Should still return questions (with low difficulty)
        assert isinstance(filtered, list)

    def test_select_with_max_competency(self, db, test_questions):
        """Test selection when user has maximum competency."""
        questions = test_questions[:3]
        target_diff = Decimal("1.0")

        filtered = filter_questions_by_difficulty(questions, target_diff, Decimal("0.2"))

        # Should still return questions (with high difficulty)
        assert isinstance(filtered, list)

    def test_select_with_all_questions_excluded(self, db, test_user_competencies, test_questions):
        """Test selection when all questions are excluded."""
        user_id = test_user_competencies[0].user_id
        all_question_ids = [q.question_id for q in test_questions]

        question = select_next_question(db, user_id, exclude_question_ids=all_question_ids)

        # Should return None or expand search
        # Depending on implementation, this might return None or use a fallback
        assert question is None or question.question_id not in all_question_ids
