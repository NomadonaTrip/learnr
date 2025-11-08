"""
Integration tests for practice session API endpoints.

Tests:
- POST /v1/practice/start - Start practice session
- GET /v1/practice/next-question - Get next adaptive question
- POST /v1/practice/submit-answer - Submit practice answer
- GET /v1/practice/session/{session_id} - Get practice session details
- POST /v1/practice/complete - Complete practice session
- GET /v1/practice/history - Get practice history
"""
import pytest
from fastapi import status


@pytest.mark.integration
class TestStartPracticeSession:
    """Test POST /v1/practice/start endpoint."""

    def test_start_practice_success(self, authenticated_client, test_learner_user, test_cbap_course, test_user_competencies, db):
        """Test successful practice session start."""
        response = authenticated_client.post(
            "/v1/practice/start",
            json={
                "course_id": test_cbap_course.course_id,
                "num_questions": 10
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert "session_id" in data
        assert data["course_id"] == test_cbap_course.course_id
        assert data["course_name"] == test_cbap_course.course_name
        assert data["total_questions"] == 10
        assert data["session_type"] == "practice"
        assert "started_at" in data

    def test_start_practice_with_target_ka(self, authenticated_client, test_cbap_course, test_user_competencies, db):
        """Test starting practice targeting specific KA."""
        from app.models.course import KnowledgeArea

        # Get first KA from the course
        target_ka = db.query(KnowledgeArea).filter(
            KnowledgeArea.course_id == test_cbap_course.course_id
        ).first()

        response = authenticated_client.post(
            "/v1/practice/start",
            json={
                "course_id": test_cbap_course.course_id,
                "knowledge_area_id": target_ka.ka_id,
                "num_questions": 5
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["target_ka_id"] == target_ka.ka_id
        assert data["target_ka_name"] == target_ka.ka_name
        assert data["total_questions"] == 5

    def test_start_practice_invalid_course(self, authenticated_client):
        """Test starting practice with invalid course."""
        response = authenticated_client.post(
            "/v1/practice/start",
            json={
                "course_id": "00000000-0000-0000-0000-000000000000",
                "num_questions": 10
            }
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_start_practice_invalid_ka(self, authenticated_client, test_cbap_course):
        """Test starting practice with invalid KA."""
        response = authenticated_client.post(
            "/v1/practice/start",
            json={
                "course_id": test_cbap_course.course_id,
                "knowledge_area_id": "00000000-0000-0000-0000-000000000000",
                "num_questions": 10
            }
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "knowledge area" in response.json()["detail"].lower()

    def test_start_practice_requires_auth(self, client, test_cbap_course):
        """Test that endpoint requires authentication."""
        response = client.post(
            "/v1/practice/start",
            json={
                "course_id": test_cbap_course.course_id,
                "num_questions": 10
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestGetNextPracticeQuestion:
    """Test GET /v1/practice/next-question endpoint."""

    def test_get_next_question_success(self, authenticated_client, test_learner_user, test_cbap_course, test_questions, test_user_competencies, db):
        """Test getting next adaptive practice question."""
        from app.models.learning import Session as LearningSession

        # Use test_learner_user fixture

        # Create practice session
        session = LearningSession(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            session_type="practice",
            total_questions=10,
            correct_answers=0,
            is_completed=False
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        response = authenticated_client.get(
            f"/v1/practice/next-question?session_id={session.session_id}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "question_id" in data
        assert data["question_number"] == 1
        assert data["total_questions"] == 10
        assert "ka_id" in data
        assert "ka_name" in data
        assert "ka_current_competency" in data
        assert "question_text" in data
        assert "difficulty" in data
        assert "answer_choices" in data
        assert len(data["answer_choices"]) >= 2

        # Verify choices don't include is_correct
        for choice in data["answer_choices"]:
            assert "choice_id" in choice
            assert "choice_text" in choice
            assert "is_correct" not in choice

    def test_get_next_question_invalid_session(self, authenticated_client):
        """Test getting question with invalid session."""
        response = authenticated_client.get(
            "/v1/practice/next-question?session_id=00000000-0000-0000-0000-000000000000"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_next_question_completed_session(self, authenticated_client, test_learner_user, test_cbap_course, test_user_competencies, db):
        """Test getting question from completed session."""
        from app.models.learning import Session as LearningSession
        from datetime import datetime, timezone

        # Use test_learner_user fixture

        # Create completed session
        session = LearningSession(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            session_type="practice",
            total_questions=10,
            correct_answers=8,
            is_completed=True,
            completed_at=datetime.now(timezone.utc)
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        response = authenticated_client.get(
            f"/v1/practice/next-question?session_id={session.session_id}"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "completed" in response.json()["detail"].lower()

    def test_get_next_question_all_answered(self, authenticated_client, test_learner_user, test_cbap_course, test_questions, test_user_competencies, db):
        """Test getting question when all questions answered."""
        from app.models.learning import Session as LearningSession, QuestionAttempt
        from app.models.question import AnswerChoice

        # Use test_learner_user fixture

        # Create session with 3 questions
        session = LearningSession(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            session_type="practice",
            total_questions=3,
            correct_answers=0,
            is_completed=False
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Answer all 3 questions
        for question in test_questions[:3]:
            choice = db.query(AnswerChoice).filter(
                AnswerChoice.question_id == question.question_id
            ).first()

            attempt = QuestionAttempt(
                user_id=test_learner_user.user_id,
                question_id=question.question_id,
                session_id=session.session_id,
                selected_choice_id=choice.choice_id,
                is_correct=choice.is_correct,
                time_spent_seconds=30
            )
            db.add(attempt)
        db.commit()

        response = authenticated_client.get(
            f"/v1/practice/next-question?session_id={session.session_id}"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "all" in response.json()["detail"].lower()

    def test_get_next_question_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.get(
            "/v1/practice/next-question?session_id=test-session"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestSubmitPracticeAnswer:
    """Test POST /v1/practice/submit-answer endpoint."""

    def test_submit_answer_correct(self, authenticated_client, test_learner_user, test_cbap_course, test_questions, test_user_competencies, db):
        """Test submitting correct answer."""
        from app.models.learning import Session as LearningSession
        from app.models.question import AnswerChoice

        # Use test_learner_user fixture

        # Create session
        session = LearningSession(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            session_type="practice",
            total_questions=10,
            correct_answers=0,
            is_completed=False
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Get a question and its correct answer
        question = test_questions[0]
        correct_choice = db.query(AnswerChoice).filter(
            AnswerChoice.question_id == question.question_id,
            AnswerChoice.is_correct == True
        ).first()

        response = authenticated_client.post(
            "/v1/practice/submit-answer",
            json={
                "session_id": session.session_id,
                "question_id": question.question_id,
                "selected_choice_id": correct_choice.choice_id,
                "time_spent_seconds": 45
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "attempt_id" in data
        assert data["is_correct"] is True
        assert data["correct_choice_id"] == correct_choice.choice_id
        assert data["question_number"] == 1
        assert data["total_questions"] == 10
        assert data["questions_remaining"] == 9
        assert "ka_id" in data
        assert "ka_name" in data
        assert "previous_competency" in data
        assert "new_competency" in data
        assert "competency_change" in data
        assert "session_accuracy" in data
        assert "attempted_at" in data

    def test_submit_answer_incorrect(self, authenticated_client, test_learner_user, test_cbap_course, test_questions, test_user_competencies, db):
        """Test submitting incorrect answer."""
        from app.models.learning import Session as LearningSession
        from app.models.question import AnswerChoice

        # Use test_learner_user fixture

        # Create session
        session = LearningSession(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            session_type="practice",
            total_questions=10,
            correct_answers=0,
            is_completed=False
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Get a question and an incorrect answer
        question = test_questions[0]
        incorrect_choice = db.query(AnswerChoice).filter(
            AnswerChoice.question_id == question.question_id,
            AnswerChoice.is_correct == False
        ).first()

        response = authenticated_client.post(
            "/v1/practice/submit-answer",
            json={
                "session_id": session.session_id,
                "question_id": question.question_id,
                "selected_choice_id": incorrect_choice.choice_id,
                "time_spent_seconds": 30
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["is_correct"] is False
        assert "correct_choice_id" in data
        assert "explanation" in data
        assert "competency_change" in data

    def test_submit_answer_duplicate(self, authenticated_client, test_learner_user, test_cbap_course, test_questions, test_user_competencies, db):
        """Test submitting answer twice for same question."""
        from app.models.learning import Session as LearningSession, QuestionAttempt
        from app.models.question import AnswerChoice

        # Use test_learner_user fixture

        # Create session
        session = LearningSession(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            session_type="practice",
            total_questions=10,
            correct_answers=0,
            is_completed=False
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Get a question
        question = test_questions[0]
        correct_choice = db.query(AnswerChoice).filter(
            AnswerChoice.question_id == question.question_id,
            AnswerChoice.is_correct == True
        ).first()

        # Create existing attempt
        attempt = QuestionAttempt(
            user_id=test_learner_user.user_id,
            question_id=question.question_id,
            session_id=session.session_id,
            selected_choice_id=correct_choice.choice_id,
            is_correct=True,
            time_spent_seconds=45
        )
        db.add(attempt)
        db.commit()

        # Try to submit again
        response = authenticated_client.post(
            "/v1/practice/submit-answer",
            json={
                "session_id": session.session_id,
                "question_id": question.question_id,
                "selected_choice_id": correct_choice.choice_id,
                "time_spent_seconds": 30
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already answered" in response.json()["detail"].lower()

    def test_submit_answer_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.post(
            "/v1/practice/submit-answer",
            json={
                "session_id": "test-session",
                "question_id": "test-question",
                "selected_choice_id": "test-choice",
                "time_spent_seconds": 30
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestGetPracticeSession:
    """Test GET /v1/practice/session/{session_id} endpoint."""

    def test_get_practice_session_success(self, authenticated_client, test_learner_user, test_cbap_course, test_questions, test_user_competencies, db):
        """Test getting practice session details."""
        from app.models.learning import Session as LearningSession, QuestionAttempt
        from app.models.question import AnswerChoice

        # Use test_learner_user fixture

        # Create session
        session = LearningSession(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            session_type="practice",
            total_questions=10,
            correct_answers=0,
            is_completed=False
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Add some attempts
        for i, question in enumerate(test_questions[:5]):
            choice = db.query(AnswerChoice).filter(
                AnswerChoice.question_id == question.question_id,
                AnswerChoice.is_correct == (i % 2 == 0)  # Alternate correct/incorrect
            ).first()

            attempt = QuestionAttempt(
                user_id=test_learner_user.user_id,
                question_id=question.question_id,
                session_id=session.session_id,
                selected_choice_id=choice.choice_id,
                is_correct=(i % 2 == 0),
                time_spent_seconds=30
            )
            db.add(attempt)

            if i % 2 == 0:
                session.correct_answers += 1

        db.commit()

        response = authenticated_client.get(
            f"/v1/practice/session/{session.session_id}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["session_id"] == session.session_id
        assert data["user_id"] == test_learner_user.user_id
        assert data["course_id"] == test_cbap_course.course_id
        assert data["session_type"] == "practice"
        assert data["total_questions"] == 10
        assert data["questions_answered"] == 5
        assert data["correct_answers"] == 3
        assert data["accuracy_percentage"] == 60.0
        assert data["is_completed"] is False
        assert "started_at" in data
        assert "duration_seconds" in data
        assert "recent_attempts" in data
        assert len(data["recent_attempts"]) <= 5

    def test_get_practice_session_invalid(self, authenticated_client):
        """Test getting invalid session."""
        response = authenticated_client.get(
            "/v1/practice/session/00000000-0000-0000-0000-000000000000"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_practice_session_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.get(
            "/v1/practice/session/test-session"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestCompletePracticeSession:
    """Test POST /v1/practice/complete endpoint."""

    def test_complete_practice_success(self, authenticated_client, test_learner_user, test_cbap_course, test_questions, test_user_competencies, db):
        """Test completing practice session."""
        from app.models.learning import Session as LearningSession, QuestionAttempt
        from app.models.question import AnswerChoice

        # Use test_learner_user fixture

        # Create session
        session = LearningSession(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            session_type="practice",
            total_questions=5,
            correct_answers=0,
            is_completed=False
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Answer all 5 questions
        correct_count = 0
        for i, question in enumerate(test_questions[:5]):
            is_correct = i < 4  # 4 correct, 1 incorrect = 80%

            choice = db.query(AnswerChoice).filter(
                AnswerChoice.question_id == question.question_id,
                AnswerChoice.is_correct == is_correct
            ).first()

            attempt = QuestionAttempt(
                user_id=test_learner_user.user_id,
                question_id=question.question_id,
                session_id=session.session_id,
                selected_choice_id=choice.choice_id,
                is_correct=is_correct,
                time_spent_seconds=30,
                user_competency_at_attempt=0.50
            )
            db.add(attempt)

            if is_correct:
                correct_count += 1
                session.correct_answers += 1

        db.commit()

        response = authenticated_client.post(
            "/v1/practice/complete",
            json={"session_id": session.session_id}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["session_id"] == session.session_id
        assert data["total_questions"] == 5
        assert data["correct_answers"] == correct_count
        assert data["accuracy_percentage"] == 80.0
        assert "duration_minutes" in data
        assert "competencies_improved" in data
        assert "weakest_ka_name" in data
        assert "recommendation" in data
        assert "completed_at" in data

        # Verify session is marked complete
        db.refresh(session)
        assert session.is_completed is True

    def test_complete_practice_incomplete(self, authenticated_client, test_learner_user, test_cbap_course, test_questions, test_user_competencies, db):
        """Test completing session with unanswered questions."""
        from app.models.learning import Session as LearningSession, QuestionAttempt
        from app.models.question import AnswerChoice

        # Use test_learner_user fixture

        # Create session
        session = LearningSession(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            session_type="practice",
            total_questions=10,
            correct_answers=0,
            is_completed=False
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Answer only 5 questions
        for question in test_questions[:5]:
            choice = db.query(AnswerChoice).filter(
                AnswerChoice.question_id == question.question_id
            ).first()

            attempt = QuestionAttempt(
                user_id=test_learner_user.user_id,
                question_id=question.question_id,
                session_id=session.session_id,
                selected_choice_id=choice.choice_id,
                is_correct=choice.is_correct,
                time_spent_seconds=30
            )
            db.add(attempt)
        db.commit()

        response = authenticated_client.post(
            "/v1/practice/complete",
            json={"session_id": session.session_id}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "incomplete" in response.json()["detail"].lower()
        assert "5/10" in response.json()["detail"]

    def test_complete_practice_already_completed(self, authenticated_client, test_learner_user, test_cbap_course, test_user_competencies, db):
        """Test completing already completed session."""
        from app.models.learning import Session as LearningSession
        from datetime import datetime, timezone

        # Use test_learner_user fixture

        # Create completed session
        session = LearningSession(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            session_type="practice",
            total_questions=10,
            correct_answers=8,
            is_completed=True,
            completed_at=datetime.now(timezone.utc)
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        response = authenticated_client.post(
            "/v1/practice/complete",
            json={"session_id": session.session_id}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already completed" in response.json()["detail"].lower()

    def test_complete_practice_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.post(
            "/v1/practice/complete",
            json={"session_id": "test-session"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestGetPracticeHistory:
    """Test GET /v1/practice/history endpoint."""

    def test_get_history_success(self, authenticated_client, test_learner_user, test_cbap_course, test_user_competencies, db):
        """Test getting practice history."""
        from app.models.learning import Session as LearningSession
        from datetime import datetime, timedelta, timezone

        # Use test_learner_user fixture

        # Create multiple completed sessions
        for i in range(5):
            session = LearningSession(
                user_id=test_learner_user.user_id,
                course_id=test_cbap_course.course_id,
                session_type="practice",
                total_questions=10,
                correct_answers=7 + i,
                is_completed=True,
                completed_at=datetime.now(timezone.utc) - timedelta(days=i)
            )
            db.add(session)
        db.commit()

        response = authenticated_client.get(
            "/v1/practice/history"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total_sessions"] >= 5
        assert data["total_questions_practiced"] >= 50
        assert 0 <= data["overall_accuracy"] <= 100
        assert "sessions" in data
        assert len(data["sessions"]) >= 1

        # Verify session structure
        if len(data["sessions"]) > 0:
            session = data["sessions"][0]
            assert "session_id" in session
            assert "session_type" in session
            assert "total_questions" in session
            assert "accuracy_percentage" in session
            assert "is_completed" in session

    def test_get_history_with_limit(self, authenticated_client, test_learner_user, test_cbap_course, test_user_competencies, db):
        """Test getting history with limit."""
        from app.models.learning import Session as LearningSession
        from datetime import datetime, timezone

        # Use test_learner_user fixture

        # Create 10 sessions
        for i in range(10):
            session = LearningSession(
                user_id=test_learner_user.user_id,
                course_id=test_cbap_course.course_id,
                session_type="practice",
                total_questions=5,
                correct_answers=4,
                is_completed=True,
                completed_at=datetime.now(timezone.utc)
            )
            db.add(session)
        db.commit()

        response = authenticated_client.get(
            "/v1/practice/history?limit=3"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["sessions"]) <= 3

    def test_get_history_empty(self, authenticated_client):
        """Test getting history with no sessions."""
        response = authenticated_client.get(
            "/v1/practice/history"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total_sessions"] == 0
        assert data["total_questions_practiced"] == 0
        assert data["overall_accuracy"] == 0.0
        assert data["sessions"] == []

    def test_get_history_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.get(
            "/v1/practice/history"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
