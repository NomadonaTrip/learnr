"""
Integration tests for session API endpoints.

Tests:
- POST /v1/sessions - Create practice session
- GET /v1/sessions/{session_id} - Get session details
- GET /v1/sessions/{session_id}/next-question - Get adaptive question
- POST /v1/sessions/{session_id}/attempt - Submit answer
- POST /v1/sessions/{session_id}/complete - Complete session
"""
import pytest
from fastapi import status


@pytest.mark.integration
class TestCreateSession:
    """Test POST /v1/sessions endpoint."""

    def test_create_practice_session_success(self, authenticated_client, test_user_competencies):
        """Test successful creation of practice session."""
        response = authenticated_client.post(
            "/v1/sessions",
            json={"session_type": "practice"}
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert "session_id" in data
        assert data["session_type"] == "practice"
        assert data["total_questions"] == 0
        assert data["correct_answers"] == 0
        assert data["is_completed"] is False

    def test_create_diagnostic_session_success(self, authenticated_client, test_user_competencies):
        """Test successful creation of diagnostic session."""
        response = authenticated_client.post(
            "/v1/sessions",
            json={"session_type": "diagnostic"}
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["session_type"] == "diagnostic"

    def test_create_mock_exam_session_success(self, authenticated_client, test_user_competencies):
        """Test successful creation of mock exam session."""
        response = authenticated_client.post(
            "/v1/sessions",
            json={"session_type": "mock_exam"}
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["session_type"] == "mock_exam"

    def test_create_session_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.post(
            "/v1/sessions",
            json={"session_type": "practice"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_session_invalid_type(self, authenticated_client):
        """Test session creation with invalid session type."""
        response = authenticated_client.post(
            "/v1/sessions",
            json={"session_type": "invalid_type"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.integration
class TestGetSession:
    """Test GET /v1/sessions/{session_id} endpoint."""

    def test_get_session_success(self, authenticated_client, test_user_competencies):
        """Test successful retrieval of session."""
        # First create a session
        create_response = authenticated_client.post(
            "/v1/sessions",
            json={"session_type": "practice"}
        )
        session_id = create_response.json()["session_id"]

        # Get the session
        response = authenticated_client.get(f"/v1/sessions/{session_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == session_id
        assert data["session_type"] == "practice"

    def test_get_session_not_found(self, authenticated_client):
        """Test getting non-existent session."""
        fake_session_id = "00000000-0000-0000-0000-000000000000"
        response = authenticated_client.get(f"/v1/sessions/{fake_session_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_session_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        fake_session_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/v1/sessions/{fake_session_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_session_other_user(self, authenticated_client, admin_authenticated_client, test_user_competencies, test_admin_with_profile):
        """Test that user cannot access another user's session."""
        # Create session as learner
        create_response = authenticated_client.post(
            "/v1/sessions",
            json={"session_type": "practice"}
        )
        session_id = create_response.json()["session_id"]

        # Try to get session as admin (different user)
        response = admin_authenticated_client.get(f"/v1/sessions/{session_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.integration
class TestGetNextQuestion:
    """Test GET /v1/sessions/{session_id}/next-question endpoint."""

    def test_get_next_question_success(self, authenticated_client, test_user_competencies, test_questions):
        """Test successful retrieval of next question."""
        # Create session
        create_response = authenticated_client.post(
            "/v1/sessions",
            json={"session_type": "practice"}
        )
        session_id = create_response.json()["session_id"]

        # Get next question
        response = authenticated_client.get(f"/v1/sessions/{session_id}/next-question")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify question structure
        assert "question_id" in data
        assert "question_text" in data
        assert "question_type" in data
        assert "answer_choices" in data
        assert isinstance(data["answer_choices"], list)
        assert len(data["answer_choices"]) >= 2

        # Verify answer choices don't reveal correct answer
        for choice in data["answer_choices"]:
            assert "choice_id" in choice
            assert "choice_text" in choice
            assert "is_correct" not in choice  # Should not be exposed

    def test_get_next_question_adaptive_selection(self, authenticated_client, test_user_competencies, test_questions, db):
        """Test that question is selected from weakest KA."""
        from app.models.learning import UserCompetency
        from decimal import Decimal

        # Set one KA to have much lower competency
        user = test_user_competencies[0]
        weakest_competency = db.query(UserCompetency).filter_by(
            user_id=user.user_id
        ).first()
        weakest_competency.competency_score = Decimal("0.20")
        db.commit()

        # Create session
        create_response = authenticated_client.post(
            "/v1/sessions",
            json={"session_type": "practice"}
        )
        session_id = create_response.json()["session_id"]

        # Get next question
        response = authenticated_client.get(f"/v1/sessions/{session_id}/next-question")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Question should be from the weakest KA
        assert data["ka_id"] == weakest_competency.ka_id

    def test_get_next_question_no_competencies(self, authenticated_client, test_user_with_profile):
        """Test that endpoint fails when user has no competencies."""
        # Create session without setting up competencies (user has profile but no competencies)
        create_response = authenticated_client.post(
            "/v1/sessions",
            json={"session_type": "practice"}
        )
        session_id = create_response.json()["session_id"]

        # Try to get question without competencies
        response = authenticated_client.get(f"/v1/sessions/{session_id}/next-question")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "competency" in response.json()["detail"].lower()

    def test_get_next_question_session_not_found(self, authenticated_client):
        """Test getting question for non-existent session."""
        fake_session_id = "00000000-0000-0000-0000-000000000000"
        response = authenticated_client.get(f"/v1/sessions/{fake_session_id}/next-question")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_next_question_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        fake_session_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/v1/sessions/{fake_session_id}/next-question")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestSubmitAnswer:
    """Test POST /v1/sessions/{session_id}/attempt endpoint."""

    def test_submit_correct_answer_success(self, authenticated_client, test_user_competencies, test_questions, db):
        """Test submitting correct answer."""
        # Create session
        create_response = authenticated_client.post(
            "/v1/sessions",
            json={"session_type": "practice"}
        )
        session_id = create_response.json()["session_id"]

        # Get a question
        question_response = authenticated_client.get(f"/v1/sessions/{session_id}/next-question")
        question_data = question_response.json()
        question_id = question_data["question_id"]

        # Find correct answer (is_correct is not exposed in API, query from database)
        from app.models.question import AnswerChoice
        correct_choice_db = db.query(AnswerChoice).filter(
            AnswerChoice.question_id == question_id,
            AnswerChoice.is_correct == True
        ).first()

        # Submit answer
        response = authenticated_client.post(
            f"/v1/sessions/{session_id}/attempt",
            json={
                "question_id": question_id,
                "selected_choice_id": correct_choice_db.choice_id,
                "time_spent_seconds": 45
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response
        assert data["is_correct"] is True
        assert "explanation" in data
        assert "correct_choice_id" in data
        assert data["time_spent_seconds"] == 45

        # Verify session was updated
        session_response = authenticated_client.get(f"/v1/sessions/{session_id}")
        session_data = session_response.json()
        assert session_data["total_questions"] == 1
        assert session_data["correct_answers"] == 1

    def test_submit_incorrect_answer(self, authenticated_client, test_user_competencies, test_questions, db):
        """Test submitting incorrect answer."""
        # Create session
        create_response = authenticated_client.post(
            "/v1/sessions",
            json={"session_type": "practice"}
        )
        session_id = create_response.json()["session_id"]

        # Get a question
        question_response = authenticated_client.get(f"/v1/sessions/{session_id}/next-question")
        question_data = question_response.json()
        question_id = question_data["question_id"]

        # Find incorrect answer
        from app.models.question import AnswerChoice
        incorrect_choice = db.query(AnswerChoice).filter(
            AnswerChoice.question_id == question_id,
            AnswerChoice.is_correct == False
        ).first()

        # Submit answer
        response = authenticated_client.post(
            f"/v1/sessions/{session_id}/attempt",
            json={
                "question_id": question_id,
                "selected_choice_id": incorrect_choice.choice_id,
                "time_spent_seconds": 30
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_correct"] is False
        assert "explanation" in data

        # Verify session stats
        session_response = authenticated_client.get(f"/v1/sessions/{session_id}")
        session_data = session_response.json()
        assert session_data["total_questions"] == 1
        assert session_data["correct_answers"] == 0

    def test_submit_answer_updates_competency(self, authenticated_client, test_user_competencies, test_questions, db):
        """Test that submitting answer updates user competency."""
        from app.models.learning import UserCompetency
        from decimal import Decimal

        # Get initial competency
        user_id = test_user_competencies[0].user_id
        initial_competency = db.query(UserCompetency).filter_by(user_id=user_id).first()
        initial_score = initial_competency.competency_score

        # Create session and get question
        create_response = authenticated_client.post(
            "/v1/sessions",
            json={"session_type": "practice"}
        )
        session_id = create_response.json()["session_id"]

        question_response = authenticated_client.get(f"/v1/sessions/{session_id}/next-question")
        question_data = question_response.json()
        question_id = question_data["question_id"]

        # Get correct answer
        from app.models.question import AnswerChoice
        correct_choice = db.query(AnswerChoice).filter(
            AnswerChoice.question_id == question_id,
            AnswerChoice.is_correct == True
        ).first()

        # Submit correct answer
        authenticated_client.post(
            f"/v1/sessions/{session_id}/attempt",
            json={
                "question_id": question_id,
                "selected_choice_id": correct_choice.choice_id,
                "time_spent_seconds": 45
            }
        )

        # Check competency was updated
        db.refresh(initial_competency)
        # Competency should have changed (either up or down depending on difficulty)
        # We just verify it was updated by checking attempt count
        assert initial_competency.attempts_count == 1
        assert initial_competency.correct_count == 1

    def test_submit_answer_invalid_choice(self, authenticated_client, test_user_competencies, test_questions):
        """Test submitting invalid answer choice."""
        create_response = authenticated_client.post(
            "/v1/sessions",
            json={"session_type": "practice"}
        )
        session_id = create_response.json()["session_id"]

        question_response = authenticated_client.get(f"/v1/sessions/{session_id}/next-question")
        question_id = question_response.json()["question_id"]

        # Submit with invalid choice ID
        response = authenticated_client.post(
            f"/v1/sessions/{session_id}/attempt",
            json={
                "question_id": question_id,
                "selected_choice_id": "00000000-0000-0000-0000-000000000000",
                "time_spent_seconds": 30
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_submit_answer_session_not_found(self, authenticated_client, test_questions, db):
        """Test submitting answer for non-existent session."""
        from app.models.question import AnswerChoice

        question = test_questions[0]
        choice = db.query(AnswerChoice).filter_by(question_id=question.question_id).first()

        response = authenticated_client.post(
            "/v1/sessions/00000000-0000-0000-0000-000000000000/attempt",
            json={
                "question_id": question.question_id,
                "selected_choice_id": choice.choice_id,
                "time_spent_seconds": 30
            }
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_submit_answer_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.post(
            "/v1/sessions/00000000-0000-0000-0000-000000000000/attempt",
            json={
                "question_id": "00000000-0000-0000-0000-000000000000",
                "selected_choice_id": "00000000-0000-0000-0000-000000000000",
                "time_spent_seconds": 30
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestCompleteSession:
    """Test POST /v1/sessions/{session_id}/complete endpoint."""

    def test_complete_session_success(self, authenticated_client, test_user_competencies):
        """Test successful session completion."""
        # Create session
        create_response = authenticated_client.post(
            "/v1/sessions",
            json={"session_type": "practice"}
        )
        session_id = create_response.json()["session_id"]

        # Complete session
        response = authenticated_client.post(
            f"/v1/sessions/{session_id}/complete",
            json={"duration_minutes": 25}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["is_completed"] is True
        assert data["completed_at"] is not None
        assert data["duration_minutes"] == 25

    def test_complete_session_without_duration(self, authenticated_client, test_user_competencies):
        """Test completing session without duration."""
        create_response = authenticated_client.post(
            "/v1/sessions",
            json={"session_type": "practice"}
        )
        session_id = create_response.json()["session_id"]

        response = authenticated_client.post(
            f"/v1/sessions/{session_id}/complete",
            json={}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_completed"] is True

    def test_complete_session_not_found(self, authenticated_client):
        """Test completing non-existent session."""
        response = authenticated_client.post(
            "/v1/sessions/00000000-0000-0000-0000-000000000000/complete",
            json={}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_complete_session_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.post(
            "/v1/sessions/00000000-0000-0000-0000-000000000000/complete",
            json={}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
