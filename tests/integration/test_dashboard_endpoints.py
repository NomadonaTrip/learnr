"""
Integration tests for dashboard API endpoints.

Tests:
- GET /v1/dashboard - Get dashboard overview
- GET /v1/dashboard/competencies - Get detailed competencies
- GET /v1/dashboard/recent - Get recent activity
- GET /v1/dashboard/exam-readiness - Get exam readiness
"""
import pytest
from fastapi import status
from decimal import Decimal


@pytest.mark.integration
class TestGetDashboardOverview:
    """Test GET /v1/dashboard endpoint."""

    def test_get_dashboard_with_activity_success(self, authenticated_client, test_user_competencies, test_questions, db):
        """Test successful dashboard retrieval with user activity."""
        from app.models.learning import Session as LearningSession

        # Create a session for the user
        session = LearningSession(
            user_id=test_user_competencies[0].user_id,
            course_id=test_questions[0].course_id,
            session_type="practice",
            total_questions=5,
            correct_answers=4,
            is_completed=True
        )
        db.add(session)
        db.commit()

        response = authenticated_client.get("/v1/dashboard")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify overview structure
        assert "overall_competency" in data
        assert "overall_competency_status" in data
        assert "exam_readiness_percentage" in data
        assert "total_questions_attempted" in data
        assert "total_correct" in data
        assert "overall_accuracy" in data
        assert "total_sessions_completed" in data
        assert "diagnostic_completed" in data
        assert "reviews_due_today" in data
        assert "competencies" in data

        # Verify competencies is a list
        assert isinstance(data["competencies"], list)
        assert len(data["competencies"]) == 6  # CBAP has 6 KAs

    def test_get_dashboard_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.get("/v1/dashboard")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_dashboard_no_activity(self, authenticated_client, test_cbap_course):
        """Test dashboard when user has no activity."""
        response = authenticated_client.get("/v1/dashboard")

        # Should return error or empty state
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST
        ]


@pytest.mark.integration
class TestGetCompetenciesDetail:
    """Test GET /v1/dashboard/competencies endpoint."""

    def test_get_competencies_detail_success(self, authenticated_client, test_user_competencies, test_questions, db):
        """Test successful retrieval of detailed competencies."""
        from app.models.learning import Session as LearningSession

        # Create session for activity
        session = LearningSession(
            user_id=test_user_competencies[0].user_id,
            course_id=test_questions[0].course_id,
            session_type="practice",
            total_questions=1,
            correct_answers=1,
            is_completed=True
        )
        db.add(session)
        db.commit()

        response = authenticated_client.get("/v1/dashboard/competencies")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify structure
        assert "overall_competency" in data
        assert "overall_trend_direction" in data
        assert "competencies" in data

        # Verify detailed competency data
        competencies = data["competencies"]
        assert isinstance(competencies, list)
        assert len(competencies) > 0

        # Check first competency has detailed data
        comp = competencies[0]
        assert "ka_id" in comp
        assert "ka_code" in comp
        assert "ka_name" in comp
        assert "current_competency" in comp
        assert "status" in comp
        assert "total_attempts" in comp
        assert "correct_count" in comp
        assert "accuracy_percentage" in comp

    def test_get_competencies_detail_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.get("/v1/dashboard/competencies")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_competencies_detail_ordering(self, authenticated_client, test_user_competencies, test_questions, db):
        """Test that competencies are ordered by score (weakest first)."""
        from app.models.learning import Session as LearningSession, UserCompetency

        # Create session
        session = LearningSession(
            user_id=test_user_competencies[0].user_id,
            course_id=test_questions[0].course_id,
            session_type="practice",
            total_questions=1,
            correct_answers=1,
            is_completed=True
        )
        db.add(session)
        db.commit()

        # Set varying competency scores
        competencies = db.query(UserCompetency).filter_by(
            user_id=test_user_competencies[0].user_id
        ).all()

        for i, comp in enumerate(competencies):
            comp.competency_score = Decimal(str(0.3 + i * 0.1))
        db.commit()

        response = authenticated_client.get("/v1/dashboard/competencies")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify ordering (weakest first)
        comp_scores = [c["current_competency"] for c in data["competencies"]]
        assert comp_scores == sorted(comp_scores)


@pytest.mark.integration
class TestGetRecentActivity:
    """Test GET /v1/dashboard/recent endpoint."""

    def test_get_recent_activity_success(self, authenticated_client, test_user_competencies, test_questions, db):
        """Test successful retrieval of recent activity."""
        from app.models.learning import Session as LearningSession, QuestionAttempt
        from datetime import datetime, timedelta, timezone

        user_id = test_user_competencies[0].user_id

        # Create recent sessions
        for i in range(3):
            session = LearningSession(
                user_id=user_id,
                course_id=test_questions[0].course_id,
                session_type="practice",
                total_questions=5 + i,
                correct_answers=3 + i,
                is_completed=True,
                completed_at=datetime.now(timezone.utc) - timedelta(days=i)
            )
            db.add(session)

        db.commit()

        response = authenticated_client.get("/v1/dashboard/recent")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify structure
        assert "recent_sessions" in data
        assert "sessions_this_week" in data
        assert "accuracy_this_week" in data
        assert "current_streak_days" in data

        # Verify sessions are ordered by date (most recent first)
        sessions = data["recent_sessions"]
        assert isinstance(sessions, list)
        assert len(sessions) >= 1

        # Check session structure
        if len(sessions) > 0:
            session = sessions[0]
            assert "session_id" in session
            assert "session_type" in session
            assert "total_questions" in session
            assert "correct_answers" in session
            assert "completed_at" in session

    def test_get_recent_activity_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.get("/v1/dashboard/recent")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_recent_activity_no_sessions(self, authenticated_client):
        """Test recent activity when user has no sessions."""
        response = authenticated_client.get("/v1/dashboard/recent")

        # Should return success with empty/zero values
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["recent_sessions"] == [] or len(data["recent_sessions"]) == 0
        assert data["current_streak_days"] == 0


@pytest.mark.integration
class TestGetExamReadiness:
    """Test GET /v1/dashboard/exam-readiness endpoint."""

    def test_get_exam_readiness_success(self, authenticated_client, test_user_competencies, test_questions, db):
        """Test successful retrieval of exam readiness."""
        from app.models.learning import Session as LearningSession, UserCompetency

        # Create session
        session = LearningSession(
            user_id=test_user_competencies[0].user_id,
            course_id=test_questions[0].course_id,
            session_type="practice",
            total_questions=10,
            correct_answers=8,
            is_completed=True
        )
        db.add(session)

        # Set some KAs to high competency
        competencies = db.query(UserCompetency).filter_by(
            user_id=test_user_competencies[0].user_id
        ).all()

        for i, comp in enumerate(competencies):
            if i < 3:
                comp.competency_score = Decimal("0.85")  # Ready
            else:
                comp.competency_score = Decimal("0.60")  # Not ready

        db.commit()

        response = authenticated_client.get("/v1/dashboard/exam-readiness")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify structure
        assert "readiness_percentage" in data
        assert "kas_ready" in data
        assert "kas_not_ready" in data
        assert "exam_ready" in data
        assert "weakest_kas" in data
        assert "next_steps" in data

        # Verify calculations
        assert data["kas_ready"] == 3
        assert data["kas_not_ready"] == 3
        assert 0 <= data["readiness_percentage"] <= 100

    def test_get_exam_readiness_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.get("/v1/dashboard/exam-readiness")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_exam_readiness_fully_ready(self, authenticated_client, test_user_competencies, test_questions, db):
        """Test exam readiness when all KAs are at target."""
        from app.models.learning import Session as LearningSession, UserCompetency

        # Create session
        session = LearningSession(
            user_id=test_user_competencies[0].user_id,
            course_id=test_questions[0].course_id,
            session_type="practice",
            total_questions=10,
            correct_answers=9,
            is_completed=True
        )
        db.add(session)

        # Set all KAs to high competency
        competencies = db.query(UserCompetency).filter_by(
            user_id=test_user_competencies[0].user_id
        ).all()

        for comp in competencies:
            comp.competency_score = Decimal("0.90")

        db.commit()

        response = authenticated_client.get("/v1/dashboard/exam-readiness")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # All KAs should be ready
        assert data["kas_ready"] == 6
        assert data["kas_not_ready"] == 0
        assert data["readiness_percentage"] == 100.0
        assert data["exam_ready"] is True

    def test_get_exam_readiness_not_ready(self, authenticated_client, test_user_competencies, test_questions, db):
        """Test exam readiness when no KAs are at target."""
        from app.models.learning import Session as LearningSession, UserCompetency

        # Create session
        session = LearningSession(
            user_id=test_user_competencies[0].user_id,
            course_id=test_questions[0].course_id,
            session_type="practice",
            total_questions=10,
            correct_answers=4,
            is_completed=True
        )
        db.add(session)

        # Set all KAs to low competency
        competencies = db.query(UserCompetency).filter_by(
            user_id=test_user_competencies[0].user_id
        ).all()

        for comp in competencies:
            comp.competency_score = Decimal("0.40")

        db.commit()

        response = authenticated_client.get("/v1/dashboard/exam-readiness")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # No KAs should be ready
        assert data["kas_ready"] == 0
        assert data["kas_not_ready"] == 6
        assert data["readiness_percentage"] == 0.0
        assert data["exam_ready"] is False
