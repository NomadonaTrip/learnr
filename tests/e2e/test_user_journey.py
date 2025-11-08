"""
End-to-end tests for complete user journeys.

These tests simulate real user flows from registration through
the complete learning experience.
"""
import pytest
from fastapi import status


@pytest.mark.e2e
class TestCompleteNewUserJourney:
    """
    Test complete journey for a new user.

    Flow:
    1. Register new account
    2. Login
    3. View available courses
    4. Complete onboarding
    5. Start practice session
    6. Answer questions
    7. Complete session
    8. View dashboard
    """

    def test_new_user_complete_journey(self, client, test_cbap_course, test_questions, db):
        """Test complete user journey from registration to practice."""

        # Step 1: Register new user
        register_response = client.post(
            "/v1/auth/register",
            json={
                "email": "e2e_user@test.com",
                "password": "E2EUser123!",
                "first_name": "E2E",
                "last_name": "User"
            }
        )
        assert register_response.status_code == status.HTTP_201_CREATED
        user_data = register_response.json()
        assert user_data["email"] == "e2e_user@test.com"

        # Step 2: Login
        login_response = client.post(
            "/v1/auth/login",
            json={
                "email": "e2e_user@test.com",
                "password": "E2EUser123!"
            }
        )
        assert login_response.status_code == status.HTTP_200_OK
        token_data = login_response.json()
        assert "access_token" in token_data

        access_token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Step 3: View available courses
        courses_response = client.get("/v1/onboarding/courses", headers=headers)
        assert courses_response.status_code == status.HTTP_200_OK
        courses = courses_response.json()
        assert len(courses) >= 1
        course_id = courses[0]["course_id"]

        # Step 4: Complete onboarding
        onboarding_response = client.post(
            "/v1/onboarding/profile",
            headers=headers,
            json={
                "course_id": course_id,
                "exam_date": "2025-12-31",
                "current_level": "intermediate",
                "target_score_percentage": 85,
                "daily_commitment_minutes": 90
            }
        )
        assert onboarding_response.status_code == status.HTTP_201_CREATED
        profile_data = onboarding_response.json()
        assert profile_data["course_id"] == course_id

        # Step 5: Start practice session
        session_response = client.post(
            "/v1/sessions",
            headers=headers,
            json={"session_type": "practice"}
        )
        assert session_response.status_code == status.HTTP_201_CREATED
        session_data = session_response.json()
        session_id = session_data["session_id"]
        assert session_data["is_completed"] is False

        # Step 6: Answer questions (answer 3 questions)
        for i in range(3):
            # Get next question
            question_response = client.get(
                f"/v1/sessions/{session_id}/next-question",
                headers=headers
            )
            assert question_response.status_code == status.HTTP_200_OK
            question_data = question_response.json()
            question_id = question_data["question_id"]

            # Get correct answer from database
            from app.models.question import AnswerChoice
            correct_choice = db.query(AnswerChoice).filter(
                AnswerChoice.question_id == question_id,
                AnswerChoice.is_correct == True
            ).first()

            # Submit answer
            attempt_response = client.post(
                f"/v1/sessions/{session_id}/attempt",
                headers=headers,
                json={
                    "question_id": question_id,
                    "selected_choice_id": correct_choice.choice_id,
                    "time_spent_seconds": 45
                }
            )
            assert attempt_response.status_code == status.HTTP_200_OK
            attempt_data = attempt_response.json()
            assert attempt_data["is_correct"] is True

        # Step 7: Complete session
        complete_response = client.post(
            f"/v1/sessions/{session_id}/complete",
            headers=headers,
            json={"duration_minutes": 15}
        )
        assert complete_response.status_code == status.HTTP_200_OK
        completed_session = complete_response.json()
        assert completed_session["is_completed"] is True
        assert completed_session["total_questions"] == 3
        assert completed_session["correct_answers"] == 3

        # Step 8: View dashboard
        dashboard_response = client.get("/v1/dashboard", headers=headers)
        assert dashboard_response.status_code == status.HTTP_200_OK
        dashboard_data = dashboard_response.json()
        assert dashboard_data["total_questions_attempted"] == 3
        assert dashboard_data["total_correct"] == 3
        assert dashboard_data["overall_accuracy"] == 100.0
        assert dashboard_data["total_sessions_completed"] == 1


@pytest.mark.e2e
class TestDiagnosticToReviewJourney:
    """
    Test journey from diagnostic assessment through to spaced repetition.

    Flow:
    1. User completes onboarding
    2. Takes diagnostic assessment
    3. Answers questions incorrectly
    4. Creates spaced repetition cards
    5. Reviews cards
    6. Checks review stats
    """

    def test_diagnostic_to_review_flow(self, authenticated_client, test_cbap_course, test_questions, test_learner_user, db):
        """Test flow from diagnostic through spaced repetition."""

        # Setup: Complete onboarding
        onboarding_response = authenticated_client.post(
            "/v1/onboarding/profile",
            json={
                "course_id": test_cbap_course.course_id,
                "exam_date": "2025-12-31",
                "current_level": "beginner",
                "target_score_percentage": 75,
                "daily_commitment_minutes": 60
            }
        )
        assert onboarding_response.status_code == status.HTTP_201_CREATED

        # Step 1: Start diagnostic session
        diagnostic_response = authenticated_client.post(
            "/v1/sessions",
            json={"session_type": "diagnostic"}
        )
        assert diagnostic_response.status_code == status.HTTP_201_CREATED
        session_id = diagnostic_response.json()["session_id"]

        # Step 2: Answer questions (mix of correct and incorrect)
        from app.models.question import AnswerChoice

        question_ids = []

        for i in range(5):
            # Get next question
            question_response = authenticated_client.get(
                f"/v1/sessions/{session_id}/next-question"
            )
            question_data = question_response.json()
            question_id = question_data["question_id"]
            question_ids.append(question_id)

            # Answer incorrectly to create review cards
            incorrect_choice = db.query(AnswerChoice).filter(
                AnswerChoice.question_id == question_id,
                AnswerChoice.is_correct == False
            ).first()

            authenticated_client.post(
                f"/v1/sessions/{session_id}/attempt",
                json={
                    "question_id": question_id,
                    "selected_choice_id": incorrect_choice.choice_id,
                    "time_spent_seconds": 30
                }
            )

        # Step 3: Complete diagnostic
        authenticated_client.post(
            f"/v1/sessions/{session_id}/complete",
            json={"duration_minutes": 20}
        )

        # Step 4: Create spaced repetition cards for incorrect answers
        from app.models.spaced_repetition import SpacedRepetitionCard
        from datetime import datetime, timedelta, timezone
        from decimal import Decimal

        # Use test_learner_user directly instead of querying
        for question_id in question_ids[:3]:  # Create cards for 3 questions
            card = SpacedRepetitionCard(
                user_id=test_learner_user.user_id,
                question_id=question_id,
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

        # Step 5: Get due reviews
        reviews_response = authenticated_client.get("/v1/reviews/due")
        assert reviews_response.status_code == status.HTTP_200_OK
        reviews_data = reviews_response.json()
        assert reviews_data["total_due"] >= 3
        assert len(reviews_data["cards"]) >= 3

        # Step 6: Answer a review card
        card_id = reviews_data["cards"][0]["card_id"]
        answer_response = authenticated_client.post(
            f"/v1/reviews/{card_id}/answer",
            json={
                "quality": 4,  # Good recall
                "time_spent_seconds": 45
            }
        )
        assert answer_response.status_code == status.HTTP_200_OK
        answer_data = answer_response.json()
        assert "updated" in answer_data
        assert answer_data["updated"]["interval_days"] >= 1

        # Step 7: Check review stats
        stats_response = authenticated_client.get("/v1/reviews/stats")
        assert stats_response.status_code == status.HTTP_200_OK
        stats_data = stats_response.json()
        assert stats_data["total_cards"] >= 3
        assert stats_data["total_reviews_completed"] >= 1


@pytest.mark.e2e
class TestMultiSessionProgressJourney:
    """
    Test user progress across multiple practice sessions.

    Flow:
    1. Complete onboarding
    2. Practice session 1 (low performance)
    3. Practice session 2 (improved performance)
    4. View competency improvement
    5. Check exam readiness
    """

    def test_multi_session_progress(self, authenticated_client, test_cbap_course, test_questions, db):
        """Test user progress across multiple sessions."""

        # Step 1: Complete onboarding
        authenticated_client.post(
            "/v1/onboarding/profile",
            json={
                "course_id": test_cbap_course.course_id,
                "exam_date": "2025-12-31",
                "current_level": "beginner",
                "target_score_percentage": 75,
                "daily_commitment_minutes": 60
            }
        )

        from app.models.question import AnswerChoice

        # Step 2: First practice session (answer 50% correct)
        session1 = authenticated_client.post(
            "/v1/sessions",
            json={"session_type": "practice"}
        )
        session1_id = session1.json()["session_id"]

        for i in range(4):
            question_response = authenticated_client.get(
                f"/v1/sessions/{session1_id}/next-question"
            )
            question_id = question_response.json()["question_id"]

            # Alternate correct/incorrect
            if i % 2 == 0:
                choice = db.query(AnswerChoice).filter(
                    AnswerChoice.question_id == question_id,
                    AnswerChoice.is_correct == True
                ).first()
            else:
                choice = db.query(AnswerChoice).filter(
                    AnswerChoice.question_id == question_id,
                    AnswerChoice.is_correct == False
                ).first()

            authenticated_client.post(
                f"/v1/sessions/{session1_id}/attempt",
                json={
                    "question_id": question_id,
                    "selected_choice_id": choice.choice_id,
                    "time_spent_seconds": 30
                }
            )

        authenticated_client.post(
            f"/v1/sessions/{session1_id}/complete",
            json={"duration_minutes": 10}
        )

        # Step 3: Second practice session (answer 100% correct)
        session2 = authenticated_client.post(
            "/v1/sessions",
            json={"session_type": "practice"}
        )
        session2_id = session2.json()["session_id"]

        for i in range(4):
            question_response = authenticated_client.get(
                f"/v1/sessions/{session2_id}/next-question"
            )
            question_id = question_response.json()["question_id"]

            # All correct
            choice = db.query(AnswerChoice).filter(
                AnswerChoice.question_id == question_id,
                AnswerChoice.is_correct == True
            ).first()

            authenticated_client.post(
                f"/v1/sessions/{session2_id}/attempt",
                json={
                    "question_id": question_id,
                    "selected_choice_id": choice.choice_id,
                    "time_spent_seconds": 30
                }
            )

        authenticated_client.post(
            f"/v1/sessions/{session2_id}/complete",
            json={"duration_minutes": 10}
        )

        # Step 4: View competency details
        competencies_response = authenticated_client.get("/v1/dashboard/competencies")
        assert competencies_response.status_code == status.HTTP_200_OK
        comp_data = competencies_response.json()

        # User should have competency data
        assert "overall_competency" in comp_data
        assert len(comp_data["competencies"]) > 0

        # Step 5: Check exam readiness
        readiness_response = authenticated_client.get("/v1/dashboard/exam-readiness")
        assert readiness_response.status_code == status.HTTP_200_OK
        readiness_data = readiness_response.json()

        assert "readiness_percentage" in readiness_data
        assert "recommendation" in readiness_data
        assert "next_steps" in readiness_data

        # Step 6: View recent activity
        recent_response = authenticated_client.get("/v1/dashboard/recent")
        assert recent_response.status_code == status.HTTP_200_OK
        recent_data = recent_response.json()

        assert len(recent_data["recent_sessions"]) == 2
        assert recent_data["questions_this_week"] == 8
        assert recent_data["accuracy_this_week"] == 75.0  # 6/8 = 75%


@pytest.mark.e2e
class TestPasswordChangeJourney:
    """Test user password change flow."""

    def test_change_password_flow(self, client, test_learner_user, db):
        """Test complete password change flow."""

        # Step 1: Login with original password
        login_response = client.post(
            "/v1/auth/login",
            json={
                "email": "learner@test.com",
                "password": "Test123Pass"
            }
        )
        assert login_response.status_code == status.HTTP_200_OK
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Change password
        change_response = client.post(
            "/v1/auth/change-password",
            headers=headers,
            json={
                "current_password": "Test123Pass",
                "new_password": "NewSecurePass123!"
            }
        )
        assert change_response.status_code == status.HTTP_200_OK

        # Step 3: Verify old password no longer works
        old_login = client.post(
            "/v1/auth/login",
            json={
                "email": "learner@test.com",
                "password": "Test123Pass"
            }
        )
        assert old_login.status_code == status.HTTP_401_UNAUTHORIZED

        # Step 4: Verify new password works
        new_login = client.post(
            "/v1/auth/login",
            json={
                "email": "learner@test.com",
                "password": "NewSecurePass123!"
            }
        )
        assert new_login.status_code == status.HTTP_200_OK


@pytest.mark.e2e
class TestTokenRefreshJourney:
    """Test token refresh flow."""

    def test_token_refresh_flow(self, client, test_learner_user):
        """Test JWT token refresh."""

        # Step 1: Login to get tokens
        login_response = client.post(
            "/v1/auth/login",
            json={
                "email": "learner@test.com",
                "password": "Test123Pass"
            }
        )
        assert login_response.status_code == status.HTTP_200_OK
        tokens = login_response.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # Step 2: Verify access token works
        me_response = client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert me_response.status_code == status.HTTP_200_OK

        # Step 3: Use refresh token to get new access token
        refresh_response = client.post(
            "/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert refresh_response.status_code == status.HTTP_200_OK
        new_tokens = refresh_response.json()
        new_access_token = new_tokens["access_token"]

        # Step 4: Verify new access token works
        new_me_response = client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"}
        )
        assert new_me_response.status_code == status.HTTP_200_OK
        assert new_me_response.json()["email"] == "learner@test.com"
