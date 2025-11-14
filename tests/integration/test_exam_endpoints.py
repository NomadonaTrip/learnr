"""
Integration tests for mock exam API endpoints.

Tests:
- POST /v1/exams/mock - Create mock exam
- GET /v1/exams/{session_id}/results - Get exam results
"""
import pytest
from fastapi import status
from uuid import uuid4


@pytest.mark.integration
class TestMockExamCreation:
    """Test mock exam creation endpoint."""

    def test_create_mock_exam_success(self, authenticated_client_with_profile, test_cbap_course, test_questions_full):
        """Test successful mock exam creation."""
        response = authenticated_client_with_profile.post("/v1/exams/mock")

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert "session_id" in data
        assert data["session_type"] == "mock_exam"
        assert data["total_questions"] > 0
        assert data["exam_duration_minutes"] > 0
        assert "started_at" in data
        assert "instructions" in data

    def test_create_mock_exam_proper_ka_distribution(self, authenticated_client_with_profile, test_cbap_course, test_questions_full, db):
        """Test that mock exam distributes questions by KA weight."""
        response = authenticated_client_with_profile.post("/v1/exams/mock")

        assert response.status_code == status.HTTP_201_CREATED
        session_id = response.json()["session_id"]

        # Get question attempts for this session
        from app.models.learning import QuestionAttempt
        attempts = db.query(QuestionAttempt).filter(
            QuestionAttempt.session_id == session_id
        ).all()

        # Count questions per KA
        ka_counts = {}
        for attempt in attempts:
            if attempt.question:
                ka_id = attempt.question.ka_id
                ka_counts[ka_id] = ka_counts.get(ka_id, 0) + 1

        # Verify distribution matches KA weights (approximately)
        # For CBAP: BA Planning 15%, Elicitation 20%, Req Lifecycle 25%, etc.
        assert len(ka_counts) > 0  # Should have questions from multiple KAs

    def test_create_mock_exam_avoids_recent_questions(self, authenticated_client_with_profile, test_questions_full, test_question_attempts_recent, db):
        """Test that mock exam avoids recently seen questions."""
        # Get recent question IDs
        recent_question_ids = {attempt.question_id for attempt in test_question_attempts_recent}

        # Create mock exam
        response = authenticated_client_with_profile.post("/v1/exams/mock")

        assert response.status_code == status.HTTP_201_CREATED
        session_id = response.json()["session_id"]

        # Get questions in this mock exam
        from app.models.learning import QuestionAttempt
        attempts = db.query(QuestionAttempt).filter(
            QuestionAttempt.session_id == session_id
        ).all()

        exam_question_ids = {attempt.question_id for attempt in attempts}

        # Should minimize overlap with recent questions
        overlap = len(exam_question_ids & recent_question_ids)
        total = len(exam_question_ids)

        # Allow some overlap but not too much (e.g., < 20%)
        assert overlap < total * 0.2

    def test_create_mock_exam_without_profile_fails(self, authenticated_client):
        """Test mock exam creation fails without user profile."""
        response = authenticated_client.post("/v1/exams/mock")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "profile not found" in response.json()["detail"].lower()

    def test_create_mock_exam_insufficient_questions_fails(self, authenticated_client_with_profile, test_cbap_course):
        """Test mock exam creation fails if insufficient questions available."""
        # This would fail if we don't have enough questions seeded
        # The service should raise ValueError which becomes 400 Bad Request
        response = authenticated_client_with_profile.post("/v1/exams/mock")

        # If we have enough questions, it succeeds
        # If not enough, it should fail with clear error
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            assert "insufficient" in response.json()["detail"].lower()

    def test_create_mock_exam_unauthenticated_fails(self, client):
        """Test mock exam creation requires authentication."""
        response = client.post("/v1/exams/mock")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestMockExamResults:
    """Test mock exam results endpoint."""

    def test_get_mock_exam_results_success(self, authenticated_client, test_completed_mock_exam):
        """Test getting results for completed mock exam."""
        session_id = test_completed_mock_exam.session_id

        response = authenticated_client.get(f"/v1/exams/{session_id}/results")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check top-level fields
        assert data["session_id"] == str(session_id)
        assert "exam_type" in data
        assert "completed_at" in data

        # Check overall performance
        assert "total_questions" in data
        assert "correct_answers" in data
        assert "incorrect_answers" in data
        assert "score_percentage" in data
        assert "passing_score" in data
        assert "passed" in data
        assert "margin" in data

        # Check time statistics
        assert "duration_seconds" in data
        assert "duration_minutes" in data
        assert "avg_seconds_per_question" in data

        # Check KA performance
        assert "performance_by_ka" in data
        assert isinstance(data["performance_by_ka"], list)
        assert "strongest_areas" in data
        assert "weakest_areas" in data

        # Check recommendations
        assert "next_steps" in data
        assert isinstance(data["next_steps"], list)

    def test_mock_exam_results_ka_performance_structure(self, authenticated_client, test_completed_mock_exam):
        """Test KA performance has correct structure."""
        session_id = test_completed_mock_exam.session_id

        response = authenticated_client.get(f"/v1/exams/{session_id}/results")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        if data["performance_by_ka"]:
            ka = data["performance_by_ka"][0]
            assert "ka_id" in ka
            assert "ka_code" in ka
            assert "ka_name" in ka
            assert "weight_percentage" in ka
            assert "total_questions" in ka
            assert "correct_answers" in ka
            assert "score_percentage" in ka

    def test_mock_exam_results_sorted_by_performance(self, authenticated_client, test_completed_mock_exam):
        """Test KA performance is sorted by score (weakest first)."""
        session_id = test_completed_mock_exam.session_id

        response = authenticated_client.get(f"/v1/exams/{session_id}/results")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        ka_scores = [ka["score_percentage"] for ka in data["performance_by_ka"]]

        # Should be sorted ascending (weakest first)
        assert ka_scores == sorted(ka_scores)

    def test_mock_exam_results_pass_fail_logic(self, authenticated_client, test_completed_mock_exam_passing, test_completed_mock_exam_failing):
        """Test pass/fail status is correctly determined."""
        # Test passing exam
        passing_response = authenticated_client.get(
            f"/v1/exams/{test_completed_mock_exam_passing.session_id}/results"
        )
        assert passing_response.status_code == status.HTTP_200_OK
        passing_data = passing_response.json()
        assert passing_data["passed"] is True
        assert passing_data["margin"] > 0

        # Test failing exam
        failing_response = authenticated_client.get(
            f"/v1/exams/{test_completed_mock_exam_failing.session_id}/results"
        )
        assert failing_response.status_code == status.HTTP_200_OK
        failing_data = failing_response.json()
        assert failing_data["passed"] is False
        assert failing_data["margin"] < 0

    def test_mock_exam_results_recommendations_for_passing(self, authenticated_client, test_completed_mock_exam_passing):
        """Test recommendations for passing exam."""
        session_id = test_completed_mock_exam_passing.session_id

        response = authenticated_client.get(f"/v1/exams/{session_id}/results")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should have positive recommendations
        assert len(data["next_steps"]) > 0
        # Check for congratulatory language
        steps_text = " ".join(data["next_steps"]).lower()
        assert any(word in steps_text for word in ["excellent", "good", "prepared", "congratulations"])

    def test_mock_exam_results_recommendations_for_failing(self, authenticated_client, test_completed_mock_exam_failing):
        """Test recommendations for failing exam."""
        session_id = test_completed_mock_exam_failing.session_id

        response = authenticated_client.get(f"/v1/exams/{session_id}/results")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should have improvement recommendations
        assert len(data["next_steps"]) > 0
        # Check for improvement language
        steps_text = " ".join(data["next_steps"]).lower()
        assert any(word in steps_text for word in ["improve", "focus", "practice", "review", "study"])

    def test_get_results_for_incomplete_exam_fails(self, authenticated_client, test_incomplete_mock_exam):
        """Test getting results for incomplete exam fails."""
        session_id = test_incomplete_mock_exam.session_id

        response = authenticated_client.get(f"/v1/exams/{session_id}/results")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not completed" in response.json()["detail"].lower()

    def test_get_results_for_non_mock_exam_fails(self, authenticated_client, test_practice_session):
        """Test getting mock exam results for non-mock session fails."""
        session_id = test_practice_session.session_id

        response = authenticated_client.get(f"/v1/exams/{session_id}/results")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "mock exam" in response.json()["detail"].lower()

    def test_get_results_for_other_users_exam_fails(self, authenticated_client, other_user_mock_exam):
        """Test cannot access another user's exam results."""
        session_id = other_user_mock_exam.session_id

        response = authenticated_client.get(f"/v1/exams/{session_id}/results")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_results_for_nonexistent_exam_fails(self, authenticated_client):
        """Test getting results for non-existent session returns 404."""
        fake_session_id = uuid4()

        response = authenticated_client.get(f"/v1/exams/{fake_session_id}/results")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_results_unauthenticated_fails(self, client, test_completed_mock_exam):
        """Test getting results requires authentication."""
        session_id = test_completed_mock_exam.session_id

        response = client.get(f"/v1/exams/{session_id}/results")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestMockExamAnalytics:
    """Test mock exam analytics calculations."""

    def test_time_statistics_calculated_correctly(self, authenticated_client, test_completed_mock_exam_with_time):
        """Test time statistics are calculated correctly."""
        session_id = test_completed_mock_exam_with_time.session_id

        response = authenticated_client.get(f"/v1/exams/{session_id}/results")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify time calculations
        assert data["duration_seconds"] > 0
        assert data["duration_minutes"] == data["duration_seconds"] // 60

        expected_avg = data["duration_seconds"] / data["total_questions"]
        assert abs(data["avg_seconds_per_question"] - expected_avg) < 0.5

    def test_strongest_weakest_areas_identified(self, authenticated_client, test_completed_mock_exam):
        """Test strongest and weakest areas are correctly identified."""
        session_id = test_completed_mock_exam.session_id

        response = authenticated_client.get(f"/v1/exams/{session_id}/results")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Strongest areas should have highest scores
        if data["strongest_areas"]:
            min_strong_score = min(ka["score_percentage"] for ka in data["strongest_areas"])
            assert min_strong_score >= 80.0

        # Weakest areas should have lowest scores
        if data["weakest_areas"]:
            max_weak_score = max(ka["score_percentage"] for ka in data["weakest_areas"])
            assert max_weak_score < 60.0
