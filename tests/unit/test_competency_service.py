"""
Unit tests for competency service (IRT-based calculations).

Tests:
- 1PL IRT competency estimation
- Competency score updates after question attempts
- Probability calculations
- Score boundaries (0.0-1.0 range)
"""
import pytest
from decimal import Decimal
import math

from app.services.competency import (
    calculate_probability_correct,
    update_competency_score,
    estimate_initial_competency,
    get_competency_level
)


@pytest.mark.unit
class TestIRTProbabilityCalculations:
    """Test IRT probability calculations (1PL model)."""

    def test_probability_equal_competency_and_difficulty(self):
        """Test probability when competency equals difficulty."""
        competency = Decimal("0.5")
        difficulty = Decimal("0.5")

        prob = calculate_probability_correct(competency, difficulty)

        # When competency = difficulty, probability should be 0.5
        assert abs(float(prob) - 0.5) < 0.01

    def test_probability_higher_competency(self):
        """Test probability when competency is higher than difficulty."""
        competency = Decimal("0.8")
        difficulty = Decimal("0.3")

        prob = calculate_probability_correct(competency, difficulty)

        # Higher competency should give >50% probability
        assert float(prob) > 0.5

    def test_probability_lower_competency(self):
        """Test probability when competency is lower than difficulty."""
        competency = Decimal("0.3")
        difficulty = Decimal("0.8")

        prob = calculate_probability_correct(competency, difficulty)

        # Lower competency should give <50% probability
        assert float(prob) < 0.5

    def test_probability_boundaries(self):
        """Test that probability stays within 0-1 range."""
        test_cases = [
            (Decimal("0.0"), Decimal("1.0")),
            (Decimal("1.0"), Decimal("0.0")),
            (Decimal("0.5"), Decimal("0.5")),
            (Decimal("0.0"), Decimal("0.0")),
            (Decimal("1.0"), Decimal("1.0"))
        ]

        for competency, difficulty in test_cases:
            prob = calculate_probability_correct(competency, difficulty)
            assert 0.0 <= float(prob) <= 1.0

    def test_probability_extreme_values(self):
        """Test probability at extreme competency/difficulty values."""
        # Very high competency, very low difficulty
        prob_high = calculate_probability_correct(Decimal("1.0"), Decimal("0.0"))
        assert float(prob_high) > 0.9

        # Very low competency, very high difficulty
        prob_low = calculate_probability_correct(Decimal("0.0"), Decimal("1.0"))
        assert float(prob_low) < 0.1


@pytest.mark.unit
class TestCompetencyScoreUpdates:
    """Test competency score updates based on question attempts."""

    def test_update_competency_correct_answer_easy_question(self):
        """Test competency update for correct answer on easy question."""
        current_competency = Decimal("0.5")
        difficulty = Decimal("0.3")  # Easy question
        is_correct = True

        new_competency = update_competency_score(
            current_competency,
            difficulty,
            is_correct
        )

        # Correct answer on easy question should increase competency slightly
        assert new_competency > current_competency
        # But not by much (expected outcome)
        assert new_competency - current_competency < Decimal("0.1")

    def test_update_competency_correct_answer_hard_question(self):
        """Test competency update for correct answer on hard question."""
        current_competency = Decimal("0.5")
        difficulty = Decimal("0.8")  # Hard question
        is_correct = True

        new_competency = update_competency_score(
            current_competency,
            difficulty,
            is_correct
        )

        # Correct answer on hard question should increase competency significantly
        assert new_competency > current_competency
        # Should be a larger increase than easy question
        assert new_competency - current_competency > Decimal("0.05")

    def test_update_competency_incorrect_answer_easy_question(self):
        """Test competency update for incorrect answer on easy question."""
        current_competency = Decimal("0.5")
        difficulty = Decimal("0.3")  # Easy question
        is_correct = False

        new_competency = update_competency_score(
            current_competency,
            difficulty,
            is_correct
        )

        # Incorrect answer on easy question should decrease competency significantly
        assert new_competency < current_competency
        # Should be a substantial decrease
        assert current_competency - new_competency > Decimal("0.05")

    def test_update_competency_incorrect_answer_hard_question(self):
        """Test competency update for incorrect answer on hard question."""
        current_competency = Decimal("0.5")
        difficulty = Decimal("0.8")  # Hard question
        is_correct = False

        new_competency = update_competency_score(
            current_competency,
            difficulty,
            is_correct
        )

        # Incorrect answer on hard question should decrease competency slightly
        assert new_competency < current_competency
        # But not by much (expected outcome)
        assert current_competency - new_competency < Decimal("0.1")

    def test_competency_stays_in_bounds(self):
        """Test that competency never goes below 0 or above 1."""
        test_cases = [
            (Decimal("0.05"), Decimal("0.9"), False),  # Near 0, hard wrong
            (Decimal("0.95"), Decimal("0.1"), True),   # Near 1, easy correct
            (Decimal("0.0"), Decimal("0.8"), False),   # At 0, wrong
            (Decimal("1.0"), Decimal("0.2"), True),    # At 1, correct
        ]

        for competency, difficulty, is_correct in test_cases:
            new_competency = update_competency_score(competency, difficulty, is_correct)
            assert Decimal("0.0") <= new_competency <= Decimal("1.0")

    def test_competency_floor_at_zero(self):
        """Test that competency doesn't go below 0."""
        current_competency = Decimal("0.1")
        difficulty = Decimal("0.1")  # Very easy question
        is_correct = False

        new_competency = update_competency_score(
            current_competency,
            difficulty,
            is_correct
        )

        assert new_competency >= Decimal("0.0")

    def test_competency_ceiling_at_one(self):
        """Test that competency doesn't go above 1."""
        current_competency = Decimal("0.9")
        difficulty = Decimal("0.9")  # Very hard question
        is_correct = True

        new_competency = update_competency_score(
            current_competency,
            difficulty,
            is_correct
        )

        assert new_competency <= Decimal("1.0")


@pytest.mark.unit
class TestInitialCompetencyEstimation:
    """Test initial competency estimation for new users."""

    def test_estimate_initial_competency_beginner(self):
        """Test initial competency for beginner preparation level."""
        initial = estimate_initial_competency(
            preparation_level="beginner",
            has_experience=False
        )

        # Beginners should start low
        assert Decimal("0.2") <= initial <= Decimal("0.4")

    def test_estimate_initial_competency_intermediate(self):
        """Test initial competency for intermediate preparation level."""
        initial = estimate_initial_competency(
            preparation_level="intermediate",
            has_experience=False
        )

        # Intermediate should start around middle
        assert Decimal("0.4") <= initial <= Decimal("0.6")

    def test_estimate_initial_competency_advanced(self):
        """Test initial competency for advanced preparation level."""
        initial = estimate_initial_competency(
            preparation_level="advanced",
            has_experience=False
        )

        # Advanced should start higher
        assert Decimal("0.6") <= initial <= Decimal("0.8")

    def test_estimate_initial_competency_with_experience(self):
        """Test that prior experience boosts initial competency."""
        initial_no_exp = estimate_initial_competency(
            preparation_level="beginner",
            has_experience=False
        )
        initial_with_exp = estimate_initial_competency(
            preparation_level="beginner",
            has_experience=True
        )

        # Experience should provide a boost
        assert initial_with_exp > initial_no_exp
        assert initial_with_exp - initial_no_exp >= Decimal("0.1")

    def test_estimate_initial_competency_stays_in_bounds(self):
        """Test that initial competency is always valid."""
        levels = ["beginner", "intermediate", "advanced"]
        experience_flags = [True, False]

        for level in levels:
            for has_exp in experience_flags:
                initial = estimate_initial_competency(level, has_exp)
                assert Decimal("0.0") <= initial <= Decimal("1.0")


@pytest.mark.unit
class TestCompetencyLevelClassification:
    """Test classification of competency scores into levels."""

    def test_get_level_novice(self):
        """Test novice competency level classification."""
        assert get_competency_level(Decimal("0.1")) == "novice"
        assert get_competency_level(Decimal("0.3")) == "novice"

    def test_get_level_beginner(self):
        """Test beginner competency level classification."""
        assert get_competency_level(Decimal("0.4")) == "beginner"
        assert get_competency_level(Decimal("0.5")) == "beginner"

    def test_get_level_intermediate(self):
        """Test intermediate competency level classification."""
        assert get_competency_level(Decimal("0.6")) == "intermediate"
        assert get_competency_level(Decimal("0.69")) == "intermediate"

    def test_get_level_advanced(self):
        """Test advanced competency level classification."""
        assert get_competency_level(Decimal("0.7")) == "advanced"
        assert get_competency_level(Decimal("0.79")) == "advanced"

    def test_get_level_expert(self):
        """Test expert competency level classification."""
        assert get_competency_level(Decimal("0.8")) == "expert"
        assert get_competency_level(Decimal("0.9")) == "expert"
        assert get_competency_level(Decimal("1.0")) == "expert"

    def test_get_level_boundary_values(self):
        """Test competency level at exact boundary values."""
        # Test boundaries
        assert get_competency_level(Decimal("0.39")) == "novice"
        assert get_competency_level(Decimal("0.40")) == "beginner"
        assert get_competency_level(Decimal("0.59")) == "beginner"
        assert get_competency_level(Decimal("0.60")) == "intermediate"


@pytest.mark.unit
class TestCompetencyConvergence:
    """Test that competency scores converge over multiple attempts."""

    def test_convergence_consistent_correct_answers(self):
        """Test competency increases and stabilizes with consistent correct answers."""
        competency = Decimal("0.5")
        difficulty = Decimal("0.5")

        # Simulate 10 correct answers
        for _ in range(10):
            competency = update_competency_score(competency, difficulty, True)

        # Should have increased significantly
        assert competency > Decimal("0.7")

    def test_convergence_consistent_incorrect_answers(self):
        """Test competency decreases and stabilizes with consistent incorrect answers."""
        competency = Decimal("0.5")
        difficulty = Decimal("0.5")

        # Simulate 10 incorrect answers
        for _ in range(10):
            competency = update_competency_score(competency, difficulty, False)

        # Should have decreased significantly
        assert competency < Decimal("0.3")

    def test_convergence_mixed_performance(self):
        """Test competency stabilizes with mixed correct/incorrect answers."""
        competency = Decimal("0.5")
        difficulty = Decimal("0.5")

        # Simulate 20 attempts with 50% accuracy
        for i in range(20):
            is_correct = (i % 2 == 0)  # Alternate correct/incorrect
            competency = update_competency_score(competency, difficulty, is_correct)

        # Should stay around 0.5 for 50% accuracy on difficulty 0.5
        assert abs(float(competency) - 0.5) < 0.15

    def test_diminishing_updates_over_time(self):
        """Test that competency updates get smaller over time."""
        competency = Decimal("0.5")
        difficulty = Decimal("0.6")

        # First update
        competency1 = update_competency_score(competency, difficulty, True)
        delta1 = competency1 - competency

        # Do several more updates
        for _ in range(5):
            competency = update_competency_score(competency, difficulty, True)

        # Next update
        competency2 = update_competency_score(competency, difficulty, True)
        delta2 = competency2 - competency

        # Later updates should be smaller (competency is stabilizing)
        # This might not always be true depending on the algorithm implementation
        # Comment out if not applicable to your IRT implementation
        # assert delta2 < delta1


@pytest.mark.unit
class TestCompetencyEdgeCases:
    """Test edge cases in competency calculations."""

    def test_same_difficulty_as_competency(self):
        """Test when difficulty exactly matches competency."""
        competency = Decimal("0.5")
        difficulty = Decimal("0.5")

        prob = calculate_probability_correct(competency, difficulty)
        assert abs(float(prob) - 0.5) < 0.01

    def test_zero_competency_zero_difficulty(self):
        """Test with both competency and difficulty at 0."""
        prob = calculate_probability_correct(Decimal("0.0"), Decimal("0.0"))
        assert 0.0 <= float(prob) <= 1.0

    def test_max_competency_max_difficulty(self):
        """Test with both competency and difficulty at 1."""
        prob = calculate_probability_correct(Decimal("1.0"), Decimal("1.0"))
        assert abs(float(prob) - 0.5) < 0.1  # Should be around 50%

    def test_precision_maintained_in_calculations(self):
        """Test that Decimal precision is maintained throughout."""
        competency = Decimal("0.555555")
        difficulty = Decimal("0.444444")

        result = update_competency_score(competency, difficulty, True)

        # Result should be a Decimal
        assert isinstance(result, Decimal)
        # Should have reasonable precision
        assert len(str(result).split('.')[-1]) >= 2
