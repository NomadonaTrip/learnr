"""
Unit tests for SM-2 spaced repetition algorithm.

Tests:
- SM-2 interval calculation
- Easiness factor updates
- Repetition count tracking
- Due date calculation
- Quality rating (0-5) effects
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta, date

from app.services.spaced_repetition import (
    calculate_next_interval,
    update_easiness_factor,
    calculate_next_review_date,
    determine_card_status,
    process_card_review
)


@pytest.mark.unit
class TestEasinessFactorCalculation:
    """Test SM-2 easiness factor (EF) calculation."""

    def test_ef_stays_same_quality_4(self):
        """Test EF stays approximately same with quality rating 4."""
        current_ef = Decimal("2.5")
        quality = 4  # "Easy" - recall with hesitation

        new_ef = update_easiness_factor(current_ef, quality)

        # Quality 4 should keep EF relatively stable
        assert abs(float(new_ef) - float(current_ef)) < 0.1

    def test_ef_increases_quality_5(self):
        """Test EF increases with quality rating 5 (perfect recall)."""
        current_ef = Decimal("2.5")
        quality = 5  # Perfect recall

        new_ef = update_easiness_factor(current_ef, quality)

        # Quality 5 should increase EF
        assert new_ef > current_ef

    def test_ef_decreases_quality_3(self):
        """Test EF decreases with quality rating 3."""
        current_ef = Decimal("2.5")
        quality = 3  # Correct with difficulty

        new_ef = update_easiness_factor(current_ef, quality)

        # Quality 3 should decrease EF slightly
        assert new_ef < current_ef

    def test_ef_decreases_significantly_quality_0(self):
        """Test EF decreases significantly with quality rating 0."""
        current_ef = Decimal("2.5")
        quality = 0  # Complete blackout

        new_ef = update_easiness_factor(current_ef, quality)

        # Quality 0 should decrease EF significantly
        assert new_ef < current_ef
        assert current_ef - new_ef > Decimal("0.5")

    def test_ef_minimum_threshold(self):
        """Test EF doesn't go below minimum (1.3)."""
        current_ef = Decimal("1.3")  # Already at minimum
        quality = 0  # Worst performance

        new_ef = update_easiness_factor(current_ef, quality)

        # Should not go below 1.3
        assert new_ef >= Decimal("1.3")

    def test_ef_all_quality_ratings(self):
        """Test EF behavior across all quality ratings (0-5)."""
        current_ef = Decimal("2.5")

        for quality in range(6):
            new_ef = update_easiness_factor(current_ef, quality)

            # All should produce valid EF
            assert new_ef >= Decimal("1.3")
            assert isinstance(new_ef, Decimal)

    def test_ef_formula_sm2(self):
        """Test SM-2 formula: EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))."""
        current_ef = Decimal("2.5")
        quality = 4

        new_ef = update_easiness_factor(current_ef, quality)

        # Calculate expected value manually
        q = quality
        expected = current_ef + Decimal("0.1") - Decimal(str((5 - q))) * (
            Decimal("0.08") + Decimal(str((5 - q))) * Decimal("0.02")
        )
        expected = max(expected, Decimal("1.3"))  # Floor at 1.3

        assert abs(float(new_ef) - float(expected)) < 0.01


@pytest.mark.unit
class TestIntervalCalculation:
    """Test SM-2 interval calculation."""

    def test_interval_first_repetition(self):
        """Test interval for first repetition (should be 1 day)."""
        repetition_count = 0
        easiness_factor = Decimal("2.5")
        previous_interval = 0

        interval = calculate_next_interval(
            repetition_count,
            easiness_factor,
            previous_interval
        )

        assert interval == 1  # First interval is 1 day

    def test_interval_second_repetition(self):
        """Test interval for second repetition (should be 6 days)."""
        repetition_count = 1
        easiness_factor = Decimal("2.5")
        previous_interval = 1

        interval = calculate_next_interval(
            repetition_count,
            easiness_factor,
            previous_interval
        )

        assert interval == 6  # Second interval is 6 days

    def test_interval_subsequent_repetitions(self):
        """Test interval for subsequent repetitions (I(n) = I(n-1) * EF)."""
        repetition_count = 2
        easiness_factor = Decimal("2.5")
        previous_interval = 6

        interval = calculate_next_interval(
            repetition_count,
            easiness_factor,
            previous_interval
        )

        # Should be previous_interval * EF = 6 * 2.5 = 15
        expected = int(6 * float(easiness_factor))
        assert interval == expected

    def test_interval_increases_over_time(self):
        """Test that intervals increase over successful repetitions."""
        easiness_factor = Decimal("2.5")
        intervals = []

        current_interval = 0
        for rep_count in range(5):
            interval = calculate_next_interval(
                rep_count,
                easiness_factor,
                current_interval
            )
            intervals.append(interval)
            current_interval = interval

        # Each interval should be larger than the previous
        for i in range(1, len(intervals)):
            assert intervals[i] > intervals[i-1]

    def test_interval_different_easiness_factors(self):
        """Test intervals with different easiness factors."""
        repetition_count = 2
        previous_interval = 6

        interval_low_ef = calculate_next_interval(
            repetition_count,
            Decimal("1.5"),  # Low EF
            previous_interval
        )

        interval_high_ef = calculate_next_interval(
            repetition_count,
            Decimal("2.8"),  # High EF
            previous_interval
        )

        # Higher EF should produce longer interval
        assert interval_high_ef > interval_low_ef


@pytest.mark.unit
class TestNextReviewDateCalculation:
    """Test calculation of next review date."""

    def test_review_date_adds_interval(self):
        """Test that review date is current date + interval."""
        current_date = date(2025, 1, 1)
        interval_days = 7

        next_date = calculate_next_review_date(current_date, interval_days)

        expected = current_date + timedelta(days=interval_days)
        assert next_date == expected

    def test_review_date_one_day_interval(self):
        """Test review date with 1-day interval."""
        current_date = date(2025, 1, 15)
        interval_days = 1

        next_date = calculate_next_review_date(current_date, interval_days)

        assert next_date == date(2025, 1, 16)

    def test_review_date_long_interval(self):
        """Test review date with long interval."""
        current_date = date(2025, 1, 1)
        interval_days = 365

        next_date = calculate_next_review_date(current_date, interval_days)

        assert next_date == date(2026, 1, 1)

    def test_review_date_zero_interval(self):
        """Test review date with zero interval (review today)."""
        current_date = date(2025, 1, 1)
        interval_days = 0

        next_date = calculate_next_review_date(current_date, interval_days)

        assert next_date == current_date


@pytest.mark.unit
class TestCardStatusDetermination:
    """Test determination of card status based on review."""

    def test_status_learning_quality_below_4(self):
        """Test card stays in learning status for quality < 4."""
        for quality in [0, 1, 2, 3]:
            status = determine_card_status(quality, current_status="learning")
            assert status == "learning"

    def test_status_review_quality_4_or_5(self):
        """Test card moves to review status for quality >= 4."""
        for quality in [4, 5]:
            status = determine_card_status(quality, current_status="learning")
            assert status == "review"

    def test_status_review_stays_review_quality_4_5(self):
        """Test card in review stays in review for quality >= 4."""
        for quality in [4, 5]:
            status = determine_card_status(quality, current_status="review")
            assert status == "review"

    def test_status_review_returns_learning_quality_below_4(self):
        """Test card returns to learning for quality < 4."""
        for quality in [0, 1, 2, 3]:
            status = determine_card_status(quality, current_status="review")
            assert status == "learning"


@pytest.mark.unit
class TestCompleteCardReviewProcess:
    """Test complete card review processing (SM-2 algorithm)."""

    def test_process_first_review_quality_5(self):
        """Test processing first review with perfect recall."""
        card_data = {
            "repetition_count": 0,
            "easiness_factor": Decimal("2.5"),
            "interval_days": 0,
            "last_reviewed": date(2025, 1, 1)
        }
        quality = 5

        result = process_card_review(card_data, quality, date(2025, 1, 1))

        assert result["repetition_count"] == 1
        assert result["interval_days"] == 1
        assert result["easiness_factor"] > Decimal("2.5")  # Should increase
        assert result["next_review_date"] == date(2025, 1, 2)

    def test_process_second_review_quality_4(self):
        """Test processing second review."""
        card_data = {
            "repetition_count": 1,
            "easiness_factor": Decimal("2.5"),
            "interval_days": 1,
            "last_reviewed": date(2025, 1, 2)
        }
        quality = 4

        result = process_card_review(card_data, quality, date(2025, 1, 2))

        assert result["repetition_count"] == 2
        assert result["interval_days"] == 6
        assert result["next_review_date"] == date(2025, 1, 8)

    def test_process_review_failed_recall(self):
        """Test processing review with failed recall (quality < 4)."""
        card_data = {
            "repetition_count": 3,
            "easiness_factor": Decimal("2.5"),
            "interval_days": 15,
            "last_reviewed": date(2025, 1, 1)
        }
        quality = 2  # Incorrect recall

        result = process_card_review(card_data, quality, date(2025, 1, 1))

        # Should reset to beginning
        assert result["repetition_count"] == 0
        assert result["interval_days"] == 1
        assert result["easiness_factor"] < Decimal("2.5")  # Should decrease

    def test_process_review_maintains_ef_floor(self):
        """Test that EF doesn't go below 1.3 even with poor performance."""
        card_data = {
            "repetition_count": 0,
            "easiness_factor": Decimal("1.3"),
            "interval_days": 0,
            "last_reviewed": date(2025, 1, 1)
        }
        quality = 0  # Complete blackout

        result = process_card_review(card_data, quality, date(2025, 1, 1))

        assert result["easiness_factor"] >= Decimal("1.3")

    def test_process_review_progression_success(self):
        """Test card progression through successful reviews."""
        card_data = {
            "repetition_count": 0,
            "easiness_factor": Decimal("2.5"),
            "interval_days": 0,
            "last_reviewed": date(2025, 1, 1)
        }

        review_dates = [date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 8)]
        qualities = [5, 5, 5]

        for review_date, quality in zip(review_dates, qualities):
            result = process_card_review(card_data, quality, review_date)
            card_data = result

        # After 3 successful reviews
        assert card_data["repetition_count"] == 3
        assert card_data["interval_days"] > 10  # Should have long interval
        assert card_data["easiness_factor"] >= Decimal("2.5")  # Should have increased


@pytest.mark.unit
class TestSM2EdgeCases:
    """Test edge cases in SM-2 algorithm."""

    def test_quality_rating_boundaries(self):
        """Test behavior at quality rating boundaries."""
        ef = Decimal("2.5")

        # Test all valid quality ratings
        for quality in range(6):
            new_ef = update_easiness_factor(ef, quality)
            assert new_ef >= Decimal("1.3")

    def test_very_high_repetition_count(self):
        """Test interval calculation with very high repetition count."""
        repetition_count = 20
        easiness_factor = Decimal("2.5")
        previous_interval = 1000

        interval = calculate_next_interval(
            repetition_count,
            easiness_factor,
            previous_interval
        )

        # Should still produce valid interval
        assert interval > previous_interval
        assert isinstance(interval, int)

    def test_ef_at_minimum_with_good_performance(self):
        """Test EF can recover from minimum with good performance."""
        current_ef = Decimal("1.3")
        quality = 5  # Perfect

        new_ef = update_easiness_factor(current_ef, quality)

        # Should increase even from minimum
        assert new_ef > current_ef

    def test_interval_consistency_same_inputs(self):
        """Test that same inputs always produce same interval."""
        repetition_count = 3
        easiness_factor = Decimal("2.5")
        previous_interval = 15

        interval1 = calculate_next_interval(repetition_count, easiness_factor, previous_interval)
        interval2 = calculate_next_interval(repetition_count, easiness_factor, previous_interval)

        assert interval1 == interval2

    def test_review_date_month_boundaries(self):
        """Test review date calculation across month boundaries."""
        current_date = date(2025, 1, 30)
        interval_days = 5

        next_date = calculate_next_review_date(current_date, interval_days)

        # Should correctly handle month boundary
        assert next_date == date(2025, 2, 4)

    def test_review_date_year_boundaries(self):
        """Test review date calculation across year boundaries."""
        current_date = date(2025, 12, 30)
        interval_days = 5

        next_date = calculate_next_review_date(current_date, interval_days)

        # Should correctly handle year boundary
        assert next_date == date(2026, 1, 4)
