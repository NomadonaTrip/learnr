"""
Integration tests for diagnostic assessment API endpoints.

Tests:
- POST /v1/diagnostic/start - Start diagnostic assessment
- GET /v1/diagnostic/next-question - Get next diagnostic question
- POST /v1/diagnostic/submit-answer - Submit diagnostic answer
- GET /v1/diagnostic/results - Get diagnostic results
- GET /v1/diagnostic/progress - Get diagnostic progress
"""
import pytest
from fastapi import status


@pytest.mark.integration
class TestStartDiagnostic:
    """Test POST /v1/diagnostic/start endpoint."""

    def test_start_diagnostic_success(self, authenticated_client, test_learner_user, test_cbap_course, db):
        """Test successful diagnostic start."""
        # Create user profile (required for diagnostic)
        from app.models.user import UserProfile
        from datetime import date

        profile = UserProfile(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            exam_date=date(2025, 12, 31),
            current_level="beginner",
            target_score_percentage=75,
            daily_commitment_minutes=60
        )
        db.add(profile)
        db.commit()

        response = authenticated_client.post(
            "/v1/diagnostic/start",
            json={"course_id": test_cbap_course.course_id}
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert "session_id" in data
        assert data["course_id"] == test_cbap_course.course_id
        assert data["course_name"] == test_cbap_course.course_name
        assert data["total_questions"] == 24  # 6 KAs * 4 questions
        assert data["questions_per_ka"] == 4
        assert data["status"] == "in_progress"
        assert "started_at" in data

    def test_start_diagnostic_invalid_course(self, authenticated_client):
        """Test starting diagnostic with invalid course."""
        response = authenticated_client.post(
            "/v1/diagnostic/start",
            json={"course_id": "00000000-0000-0000-0000-000000000000"}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_start_diagnostic_duplicate_incomplete(self, authenticated_client, test_learner_user, test_cbap_course, db):
        """Test that users cannot start duplicate incomplete diagnostic."""
        from app.models.user import UserProfile
        from app.models.learning import Session as LearningSession
        from datetime import date

        # Create profile
        profile = UserProfile(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            exam_date=date(2025, 12, 31),
            current_level="beginner",
            target_score_percentage=75,
            daily_commitment_minutes=60
        )
        db.add(profile)

        # Create incomplete diagnostic session
        session = LearningSession(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            session_type="diagnostic",
            total_questions=24,
            correct_answers=0,
            is_completed=False
        )
        db.add(session)
        db.commit()

        # Try to start another
        response = authenticated_client.post(
            "/v1/diagnostic/start",
            json={"course_id": test_cbap_course.course_id}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "incomplete" in response.json()["detail"].lower()

    def test_start_diagnostic_requires_auth(self, client, test_cbap_course):
        """Test that endpoint requires authentication."""
        response = client.post(
            "/v1/diagnostic/start",
            json={"course_id": test_cbap_course.course_id}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestGetNextDiagnosticQuestion:
    """Test GET /v1/diagnostic/next-question endpoint."""

    def test_get_next_question_success(self, authenticated_client, test_learner_user, test_cbap_course, test_questions, db):
        """Test getting next diagnostic question."""
        from app.models.user import User, UserProfile
        from app.models.learning import Session as LearningSession
        from datetime import date

        # Use test_learner_user fixture

        # Create profile
        profile = UserProfile(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            exam_date=date(2025, 12, 31),
            current_level="beginner",
            target_score_percentage=75,
            daily_commitment_minutes=60
        )
        db.add(profile)

        # Create diagnostic session
        session = LearningSession(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            session_type="diagnostic",
            total_questions=24,
            correct_answers=0,
            is_completed=False
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        response = authenticated_client.get(
            f"/v1/diagnostic/next-question?session_id={session.session_id}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "question_id" in data
        assert data["question_number"] == 1
        assert data["total_questions"] == 24
        assert "ka_id" in data
        assert "ka_name" in data
        assert "question_text" in data
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
            "/v1/diagnostic/next-question?session_id=00000000-0000-0000-0000-000000000000"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_next_question_completed_session(self, authenticated_client, test_learner_user, test_cbap_course, db):
        """Test getting question from completed session."""
        from app.models.learning import Session as LearningSession
        from datetime import datetime, timezone

        # Use test_learner_user fixture

        # Create completed session
        session = LearningSession(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            session_type="diagnostic",
            total_questions=24,
            correct_answers=18,
            is_completed=True,
            completed_at=datetime.now(timezone.utc)
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        response = authenticated_client.get(
            f"/v1/diagnostic/next-question?session_id={session.session_id}"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "completed" in response.json()["detail"].lower()

    def test_get_next_question_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.get(
            "/v1/diagnostic/next-question?session_id=test-session-id"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestSubmitDiagnosticAnswer:
    """Test POST /v1/diagnostic/submit-answer endpoint."""

    def test_submit_answer_correct(self, authenticated_client, test_learner_user, test_cbap_course, test_questions, db):
        """Test submitting correct answer."""
        from app.models.learning import Session as LearningSession
        from app.models.question import AnswerChoice

        # Use test_learner_user fixture

        # Create session
        session = LearningSession(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            session_type="diagnostic",
            total_questions=24,
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
            "/v1/diagnostic/submit-answer",
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
        assert data["total_questions"] == 24
        assert data["questions_remaining"] == 23
        assert "attempted_at" in data

    def test_submit_answer_incorrect(self, authenticated_client, test_learner_user, test_cbap_course, test_questions, db):
        """Test submitting incorrect answer."""
        from app.models.learning import Session as LearningSession
        from app.models.question import AnswerChoice

        # Use test_learner_user fixture

        # Create session
        session = LearningSession(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            session_type="diagnostic",
            total_questions=24,
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
            "/v1/diagnostic/submit-answer",
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

    def test_submit_answer_duplicate(self, authenticated_client, test_learner_user, test_cbap_course, test_questions, db):
        """Test submitting answer twice for same question."""
        from app.models.learning import Session as LearningSession, QuestionAttempt
        from app.models.question import AnswerChoice

        # Use test_learner_user fixture

        # Create session
        session = LearningSession(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            session_type="diagnostic",
            total_questions=24,
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
            "/v1/diagnostic/submit-answer",
            json={
                "session_id": session.session_id,
                "question_id": question.question_id,
                "selected_choice_id": correct_choice.choice_id,
                "time_spent_seconds": 30
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already answered" in response.json()["detail"].lower()

    def test_submit_answer_invalid_choice(self, authenticated_client, test_learner_user, test_cbap_course, test_questions, db):
        """Test submitting answer with invalid choice."""
        from app.models.learning import Session as LearningSession

        # Use test_learner_user fixture

        # Create session
        session = LearningSession(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            session_type="diagnostic",
            total_questions=24,
            correct_answers=0,
            is_completed=False
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        response = authenticated_client.post(
            "/v1/diagnostic/submit-answer",
            json={
                "session_id": session.session_id,
                "question_id": test_questions[0].question_id,
                "selected_choice_id": "00000000-0000-0000-0000-000000000000",
                "time_spent_seconds": 30
            }
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "invalid" in response.json()["detail"].lower()

    def test_submit_answer_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.post(
            "/v1/diagnostic/submit-answer",
            json={
                "session_id": "test-session",
                "question_id": "test-question",
                "selected_choice_id": "test-choice",
                "time_spent_seconds": 30
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestGetDiagnosticResults:
    """Test GET /v1/diagnostic/results endpoint."""

    def test_get_results_success(self, authenticated_client, test_learner_user, test_cbap_course, test_questions, db):
        """Test getting diagnostic results after completing all questions."""
        from app.models.learning import Session as LearningSession, QuestionAttempt
        from app.models.question import AnswerChoice
        from datetime import datetime, timezone

        # Use test_learner_user fixture

        # Determine actual number of questions available
        num_questions = min(len(test_questions), 24)

        # Create session
        session = LearningSession(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            session_type="diagnostic",
            total_questions=num_questions,
            correct_answers=0,
            is_completed=False
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Answer all available questions
        correct_count = 0
        for i, question in enumerate(test_questions[:num_questions]):
            # Answer correctly 75% of the time
            is_correct = (i % 4) != 0

            if is_correct:
                choice = db.query(AnswerChoice).filter(
                    AnswerChoice.question_id == question.question_id,
                    AnswerChoice.is_correct == True
                ).first()
                if choice:
                    correct_count += 1
                else:
                    # If no correct choice, use first choice
                    choice = db.query(AnswerChoice).filter(
                        AnswerChoice.question_id == question.question_id
                    ).first()
                    is_correct = False
            else:
                choice = db.query(AnswerChoice).filter(
                    AnswerChoice.question_id == question.question_id,
                    AnswerChoice.is_correct == False
                ).first()
                if not choice:
                    # If no incorrect choice, use first choice
                    choice = db.query(AnswerChoice).filter(
                        AnswerChoice.question_id == question.question_id
                    ).first()

            if choice:
                attempt = QuestionAttempt(
                    user_id=test_learner_user.user_id,
                    question_id=question.question_id,
                    session_id=session.session_id,
                    selected_choice_id=choice.choice_id,
                    is_correct=is_correct,
                    time_spent_seconds=45
                )
                db.add(attempt)

        session.correct_answers = correct_count
        db.commit()

        response = authenticated_client.get(
            f"/v1/diagnostic/results?session_id={session.session_id}"
        )

        assert response.status_code == status.HTTP_200_OK, f"Failed with: {response.json()}"
        data = response.json()

        assert data["session_id"] == session.session_id
        assert data["total_questions"] == num_questions
        assert data["total_correct"] == correct_count
        assert 0 <= data["overall_accuracy"] <= 100
        assert "overall_competency" in data
        assert "ka_results" in data
        assert len(data["ka_results"]) >= 1  # At least 1 KA covered

        # Verify KA results structure
        for ka_result in data["ka_results"]:
            assert "ka_id" in ka_result
            assert "ka_name" in ka_result
            assert "competency_score" in ka_result
            assert "accuracy_percentage" in ka_result
            assert "status" in ka_result

        assert "weakest_ka_id" in data
        assert "weakest_ka_name" in data
        assert "recommendation" in data

        # Verify session is now marked complete
        db.refresh(session)
        assert session.is_completed is True

    def test_get_results_incomplete(self, authenticated_client, test_learner_user, test_cbap_course, test_questions, db):
        """Test getting results when diagnostic is incomplete."""
        from app.models.learning import Session as LearningSession, QuestionAttempt
        from app.models.question import AnswerChoice

        # Use test_learner_user fixture

        # Create session
        session = LearningSession(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            session_type="diagnostic",
            total_questions=24,
            correct_answers=0,
            is_completed=False
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Answer only 10 questions
        for question in test_questions[:10]:
            choice = db.query(AnswerChoice).filter(
                AnswerChoice.question_id == question.question_id
            ).first()

            attempt = QuestionAttempt(
                user_id=test_learner_user.user_id,
                question_id=question.question_id,
                session_id=session.session_id,
                selected_choice_id=choice.choice_id,
                is_correct=choice.is_correct,
                time_spent_seconds=45
            )
            db.add(attempt)
        db.commit()

        response = authenticated_client.get(
            f"/v1/diagnostic/results?session_id={session.session_id}"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "incomplete" in response.json()["detail"].lower()
        assert "10/24" in response.json()["detail"]

    def test_get_results_invalid_session(self, authenticated_client):
        """Test getting results with invalid session."""
        response = authenticated_client.get(
            "/v1/diagnostic/results?session_id=00000000-0000-0000-0000-000000000000"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_results_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.get(
            "/v1/diagnostic/results?session_id=test-session"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestGetDiagnosticProgress:
    """Test GET /v1/diagnostic/progress endpoint."""

    def test_get_progress_success(self, authenticated_client, test_learner_user, test_cbap_course, test_questions, db):
        """Test getting diagnostic progress."""
        from app.models.learning import Session as LearningSession, QuestionAttempt
        from app.models.question import AnswerChoice

        # Use test_learner_user fixture

        # Create session
        session = LearningSession(
            user_id=test_learner_user.user_id,
            course_id=test_cbap_course.course_id,
            session_type="diagnostic",
            total_questions=24,
            correct_answers=0,
            is_completed=False
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Answer 12 questions (50%)
        for question in test_questions[:12]:
            choice = db.query(AnswerChoice).filter(
                AnswerChoice.question_id == question.question_id
            ).first()

            attempt = QuestionAttempt(
                user_id=test_learner_user.user_id,
                question_id=question.question_id,
                session_id=session.session_id,
                selected_choice_id=choice.choice_id,
                is_correct=choice.is_correct,
                time_spent_seconds=45
            )
            db.add(attempt)
        db.commit()

        response = authenticated_client.get(
            f"/v1/diagnostic/progress?session_id={session.session_id}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["session_id"] == session.session_id
        assert data["session_type"] == "diagnostic"
        assert data["is_completed"] is False
        assert data["questions_answered"] == 12
        assert data["total_questions"] == 24
        assert data["progress_percentage"] == 50.0
        assert "started_at" in data

    def test_get_progress_invalid_session(self, authenticated_client):
        """Test getting progress with invalid session."""
        response = authenticated_client.get(
            "/v1/diagnostic/progress?session_id=00000000-0000-0000-0000-000000000000"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_progress_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.get(
            "/v1/diagnostic/progress?session_id=test-session"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
