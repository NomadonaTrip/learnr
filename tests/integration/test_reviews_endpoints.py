"""
Integration tests for spaced repetition review API endpoints.

Tests:
- GET /v1/reviews/due - Get due review cards
- POST /v1/reviews/{card_id}/answer - Answer review card
- GET /v1/reviews/stats - Get review statistics
"""
import pytest
from fastapi import status
from datetime import datetime, timedelta, timezone
from decimal import Decimal


@pytest.mark.integration
class TestGetDueReviews:
    """Test GET /v1/reviews/due endpoint."""

    def test_get_due_reviews_success(self, authenticated_client, test_user_competencies, test_questions, db):
        """Test successful retrieval of due review cards."""
        from app.models.spaced_repetition import SpacedRepetitionCard

        user_id = test_user_competencies[0].user_id

        # Create due review cards
        for i, question in enumerate(test_questions[:3]):
            card = SpacedRepetitionCard(
                user_id=user_id,
                question_id=question.question_id,
                easiness_factor=Decimal("2.5"),
                interval_days=1,
                repetition_count=i,
                next_review_at=datetime.now(timezone.utc) - timedelta(hours=1),  # Due now
                is_due=True,
                total_reviews=i,
                successful_reviews=i
            )
            db.add(card)

        db.commit()

        response = authenticated_client.get("/v1/reviews/due")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify structure
        assert "total_due" in data
        assert "total_overdue" in data
        assert "estimated_minutes" in data
        assert "cards" in data

        # Verify we got the due cards
        assert data["total_due"] >= 3
        assert isinstance(data["cards"], list)
        assert len(data["cards"]) >= 3

        # Check card structure
        card = data["cards"][0]
        assert "card_id" in card
        assert "question_id" in card
        assert "question_text" in card
        assert "ka_code" in card
        assert "ka_name" in card
        assert "easiness_factor" in card
        assert "interval_days" in card
        assert "repetition_count" in card

    def test_get_due_reviews_with_limit(self, authenticated_client, test_user_competencies, test_questions, db):
        """Test retrieval with limit parameter."""
        from app.models.spaced_repetition import SpacedRepetitionCard

        user_id = test_user_competencies[0].user_id

        # Create 10 due review cards
        for question in test_questions[:10]:
            card = SpacedRepetitionCard(
                user_id=user_id,
                question_id=question.question_id,
                easiness_factor=Decimal("2.5"),
                interval_days=1,
                repetition_count=0,
                next_review_at=datetime.now(timezone.utc) - timedelta(hours=1),
                is_due=True,
                total_reviews=0,
                successful_reviews=0
            )
            db.add(card)

        db.commit()

        # Request only 5 cards
        response = authenticated_client.get("/v1/reviews/due?limit=5")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should return max 5 cards
        assert len(data["cards"]) <= 5

    def test_get_due_reviews_no_cards(self, authenticated_client, test_user_competencies):
        """Test when user has no due review cards."""
        response = authenticated_client.get("/v1/reviews/due")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should return empty list
        assert data["total_due"] == 0
        assert data["cards"] == []
        assert data["estimated_minutes"] == 0

    def test_get_due_reviews_only_future_cards(self, authenticated_client, test_user_competencies, test_questions, db):
        """Test that only cards with next_review_at <= now are returned."""
        from app.models.spaced_repetition import SpacedRepetitionCard

        user_id = test_user_competencies[0].user_id

        # Create cards due in the future
        for question in test_questions[:3]:
            card = SpacedRepetitionCard(
                user_id=user_id,
                question_id=question.question_id,
                easiness_factor=Decimal("2.5"),
                interval_days=1,
                repetition_count=0,
                next_review_at=datetime.now(timezone.utc) + timedelta(days=2),  # Future
                is_due=False,
                total_reviews=0,
                successful_reviews=0
            )
            db.add(card)

        db.commit()

        response = authenticated_client.get("/v1/reviews/due")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should not return future cards
        assert data["total_due"] == 0

    def test_get_due_reviews_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.get("/v1/reviews/due")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestAnswerReviewCard:
    """Test POST /v1/reviews/{card_id}/answer endpoint."""

    def test_answer_review_perfect_recall(self, authenticated_client, test_user_competencies, test_questions, db):
        """Test answering review card with perfect recall (quality=5)."""
        from app.models.spaced_repetition import SpacedRepetitionCard

        user_id = test_user_competencies[0].user_id
        question = test_questions[0]

        # Create review card
        card = SpacedRepetitionCard(
            user_id=user_id,
            question_id=question.question_id,
            easiness_factor=Decimal("2.5"),
            interval_days=1,
            repetition_count=0,
            next_review_at=datetime.now(timezone.utc) - timedelta(hours=1),
            is_due=True,
            total_reviews=0,
            successful_reviews=0
        )
        db.add(card)
        db.commit()
        db.refresh(card)

        # Answer with perfect recall
        response = authenticated_client.post(
            f"/v1/reviews/{card.card_id}/answer",
            json={
                "quality": 5,  # Perfect recall
                "time_spent_seconds": 30
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify SM-2 parameters updated
        assert "updated" in data
        updated = data["updated"]
        assert float(updated["easiness_factor"]) >= 2.5  # Should increase or stay same
        assert updated["interval_days"] >= 1  # First successful repetition: interval is 1
        assert updated["repetition_count"] == 1
        assert "next_review_at" in updated

        # Verify feedback message
        assert "feedback_message" in data

    def test_answer_review_complete_failure(self, authenticated_client, test_user_competencies, test_questions, db):
        """Test answering review card with complete failure (quality=0)."""
        from app.models.spaced_repetition import SpacedRepetitionCard

        user_id = test_user_competencies[0].user_id
        question = test_questions[0]

        # Create review card
        card = SpacedRepetitionCard(
            user_id=user_id,
            question_id=question.question_id,
            easiness_factor=Decimal("2.5"),
            interval_days=5,
            repetition_count=2,
            next_review_at=datetime.now(timezone.utc) - timedelta(hours=1),
            is_due=True,
            total_reviews=2,
            successful_reviews=2
        )
        db.add(card)
        db.commit()
        db.refresh(card)

        # Answer with complete failure
        response = authenticated_client.post(
            f"/v1/reviews/{card.card_id}/answer",
            json={
                "quality": 0,  # Complete failure
                "time_spent_seconds": 60
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify SM-2 reset
        updated = data["updated"]
        assert updated["interval_days"] == 1  # Should reset to 1
        assert updated["repetition_count"] == 0  # Should reset

    def test_answer_review_moderate_recall(self, authenticated_client, test_user_competencies, test_questions, db):
        """Test answering review card with moderate recall (quality=3)."""
        from app.models.spaced_repetition import SpacedRepetitionCard

        user_id = test_user_competencies[0].user_id
        question = test_questions[0]

        card = SpacedRepetitionCard(
            user_id=user_id,
            question_id=question.question_id,
            easiness_factor=Decimal("2.5"),
            interval_days=1,
            repetition_count=0,
            next_review_at=datetime.now(timezone.utc) - timedelta(hours=1),
            is_due=True,
            total_reviews=0,
            successful_reviews=0
        )
        db.add(card)
        db.commit()
        db.refresh(card)

        # Answer with moderate recall
        response = authenticated_client.post(
            f"/v1/reviews/{card.card_id}/answer",
            json={
                "quality": 3,
                "time_spent_seconds": 45
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Quality 3 is passing, first repetition results in interval_days=1
        assert data["updated"]["interval_days"] >= 1

    def test_answer_review_invalid_quality(self, authenticated_client, test_user_competencies, test_questions, db):
        """Test answering with invalid quality rating."""
        from app.models.spaced_repetition import SpacedRepetitionCard

        user_id = test_user_competencies[0].user_id
        question = test_questions[0]

        card = SpacedRepetitionCard(
            user_id=user_id,
            question_id=question.question_id,
            easiness_factor=Decimal("2.5"),
            interval_days=1,
            repetition_count=0,
            next_review_at=datetime.now(timezone.utc) - timedelta(hours=1),
            is_due=True,
            total_reviews=0,
            successful_reviews=0
        )
        db.add(card)
        db.commit()
        db.refresh(card)

        # Answer with invalid quality (must be 0-5)
        response = authenticated_client.post(
            f"/v1/reviews/{card.card_id}/answer",
            json={
                "quality": 10,  # Invalid
                "time_spent_seconds": 30
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_answer_review_card_not_found(self, authenticated_client):
        """Test answering non-existent card."""
        response = authenticated_client.post(
            "/v1/reviews/00000000-0000-0000-0000-000000000000/answer",
            json={
                "quality": 4,
                "time_spent_seconds": 30
            }
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_answer_review_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.post(
            "/v1/reviews/00000000-0000-0000-0000-000000000000/answer",
            json={
                "quality": 4,
                "time_spent_seconds": 30
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestGetReviewStats:
    """Test GET /v1/reviews/stats endpoint."""

    def test_get_review_stats_success(self, authenticated_client, test_user_competencies, test_questions, db):
        """Test successful retrieval of review statistics."""
        from app.models.spaced_repetition import SpacedRepetitionCard

        user_id = test_user_competencies[0].user_id

        # Create review cards with different statuses
        # 5 cards due today
        for question in test_questions[:5]:
            card = SpacedRepetitionCard(
                user_id=user_id,
                question_id=question.question_id,
                easiness_factor=Decimal("2.5"),
                interval_days=1,
                repetition_count=1,
                next_review_at=datetime.now(timezone.utc) - timedelta(hours=1),
                is_due=True,
                total_reviews=3,
                successful_reviews=2
            )
            db.add(card)

        # 3 cards due in future
        for question in test_questions[5:8]:
            card = SpacedRepetitionCard(
                user_id=user_id,
                question_id=question.question_id,
                easiness_factor=Decimal("2.5"),
                interval_days=5,
                repetition_count=2,
                next_review_at=datetime.now(timezone.utc) + timedelta(days=2),
                is_due=False,
                total_reviews=2,
                successful_reviews=2
            )
            db.add(card)

        db.commit()

        response = authenticated_client.get("/v1/reviews/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify statistics structure
        assert "total_cards" in data
        assert "cards_due_today" in data
        assert "cards_due_this_week" in data
        assert "total_reviews_completed" in data
        assert "average_success_rate" in data
        assert "cards_mastered" in data

        # Verify counts
        assert data["total_cards"] >= 8
        assert data["cards_due_today"] >= 5

    def test_get_review_stats_no_cards(self, authenticated_client):
        """Test statistics when user has no review cards."""
        response = authenticated_client.get("/v1/reviews/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should return zeros
        assert data["total_cards"] == 0
        assert data["cards_due_today"] == 0
        assert data["total_reviews_completed"] == 0
        assert data["average_success_rate"] == 0.0

    def test_get_review_stats_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.get("/v1/reviews/stats")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_review_stats_success_rate_calculation(self, authenticated_client, test_user_competencies, test_questions, db):
        """Test that success rate is calculated correctly."""
        from app.models.spaced_repetition import SpacedRepetitionCard

        user_id = test_user_competencies[0].user_id

        # Create cards with known success rates
        # Card 1: 3/5 success (60%)
        card1 = SpacedRepetitionCard(
            user_id=user_id,
            question_id=test_questions[0].question_id,
            easiness_factor=Decimal("2.5"),
            interval_days=1,
            repetition_count=1,
            next_review_at=datetime.now(timezone.utc),
            is_due=True,
            total_reviews=5,
            successful_reviews=3
        )
        db.add(card1)

        # Card 2: 4/4 success (100%)
        card2 = SpacedRepetitionCard(
            user_id=user_id,
            question_id=test_questions[1].question_id,
            easiness_factor=Decimal("2.5"),
            interval_days=1,
            repetition_count=1,
            next_review_at=datetime.now(timezone.utc),
            is_due=True,
            total_reviews=4,
            successful_reviews=4
        )
        db.add(card2)

        db.commit()

        response = authenticated_client.get("/v1/reviews/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Overall success rate should be reasonable (between 60-90% for these cards)
        assert data["total_reviews_completed"] == 9
        # API calculates average success rate per card: (60% + 100%) / 2 = 80%
        assert 70.0 <= data["average_success_rate"] <= 90.0
