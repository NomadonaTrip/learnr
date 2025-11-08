"""
Integration tests for onboarding API endpoints.

Tests:
- GET /v1/onboarding/courses - Get available courses
- POST /v1/onboarding/profile - Complete onboarding
- GET /v1/onboarding/me - Get user with profile
"""
import pytest
from fastapi import status
from datetime import date


@pytest.mark.integration
class TestGetCourses:
    """Test GET /v1/onboarding/courses endpoint."""

    def test_get_courses_success(self, authenticated_client, test_cbap_course):
        """Test successful retrieval of active courses."""
        response = authenticated_client.get("/v1/onboarding/courses")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Verify course structure
        course = data[0]
        assert "course_id" in course
        assert "course_code" in course
        assert "course_name" in course
        assert course["status"] == "active"
        assert course["course_code"] == "CBAP"

    def test_get_courses_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.get("/v1/onboarding/courses")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_courses_only_shows_active(self, authenticated_client, db, test_cbap_course):
        """Test that only active courses are returned."""
        from app.models.course import Course

        # Create a draft course
        draft_course = Course(
            course_code="PSM1",
            course_name="Professional Scrum Master I",
            version="v1",
            status="draft",
            wizard_completed=False,
            passing_score_percentage=85,
            is_active=False
        )
        db.add(draft_course)
        db.commit()

        response = authenticated_client.get("/v1/onboarding/courses")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify only active courses are returned
        course_codes = [c["course_code"] for c in data]
        assert "CBAP" in course_codes
        assert "PSM1" not in course_codes


@pytest.mark.integration
class TestCompleteOnboarding:
    """Test POST /v1/onboarding/profile endpoint."""

    def test_complete_onboarding_success(self, authenticated_client, test_cbap_course, db):
        """Test successful onboarding completion."""
        response = authenticated_client.post(
            "/v1/onboarding/profile",
            json={
                "course_id": test_cbap_course.course_id,
                "exam_date": "2025-12-31",
                "current_level": "intermediate",
                "target_score_percentage": 85,
                "daily_commitment_minutes": 90
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Verify profile data
        assert "profile_id" in data
        assert data["course_id"] == test_cbap_course.course_id
        assert data["current_level"] == "intermediate"
        assert data["target_score_percentage"] == 85
        assert data["daily_commitment_minutes"] == 90

        # Verify UserCompetency records were created
        from app.models.learning import UserCompetency
        from app.models.user import User

        user_email = authenticated_client.headers.get("Authorization", "").split()[-1]
        # Get user from database to check competencies were created
        competencies = db.query(UserCompetency).count()
        assert competencies == 6  # Should have 6 competencies for CBAP

    def test_complete_onboarding_requires_auth(self, client, test_cbap_course):
        """Test that endpoint requires authentication."""
        response = client.post(
            "/v1/onboarding/profile",
            json={
                "course_id": test_cbap_course.course_id,
                "exam_date": "2025-12-31",
                "current_level": "beginner",
                "target_score_percentage": 75,
                "daily_commitment_minutes": 60
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_complete_onboarding_invalid_course(self, authenticated_client):
        """Test onboarding with non-existent course."""
        response = authenticated_client.post(
            "/v1/onboarding/profile",
            json={
                "course_id": "00000000-0000-0000-0000-000000000000",  # Non-existent
                "exam_date": "2025-12-31",
                "current_level": "beginner",
                "target_score_percentage": 75,
                "daily_commitment_minutes": 60
            }
        )

        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST]

    def test_complete_onboarding_duplicate_profile(self, authenticated_client, test_user_with_profile, test_cbap_course):
        """Test that user cannot create duplicate profile."""
        response = authenticated_client.post(
            "/v1/onboarding/profile",
            json={
                "course_id": test_cbap_course.course_id,
                "exam_date": "2025-12-31",
                "current_level": "beginner",
                "target_score_percentage": 75,
                "daily_commitment_minutes": 60
            }
        )

        # Should fail because profile already exists
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT]

    def test_complete_onboarding_invalid_prep_level(self, authenticated_client, test_cbap_course):
        """Test onboarding with invalid preparation level."""
        response = authenticated_client.post(
            "/v1/onboarding/profile",
            json={
                "course_id": test_cbap_course.course_id,
                "exam_date": "2025-12-31",
                "current_level": "invalid_level",  # Invalid
                "target_score_percentage": 75,
                "daily_commitment_minutes": 60
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_complete_onboarding_missing_required_fields(self, authenticated_client, test_cbap_course):
        """Test onboarding with missing required fields."""
        response = authenticated_client.post(
            "/v1/onboarding/profile",
            json={
                "course_id": test_cbap_course.course_id
                # Missing all other required fields
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.integration
class TestGetUserWithProfile:
    """Test GET /v1/onboarding/me endpoint."""

    def test_get_user_with_profile_success(self, authenticated_client, test_user_with_profile):
        """Test successful retrieval of user with profile."""
        response = authenticated_client.get("/v1/onboarding/me")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify user data
        assert "user_id" in data
        assert "email" in data
        assert "first_name" in data
        assert "last_name" in data

        # Verify profile data is included
        assert "profile" in data
        profile = data["profile"]
        assert "course_id" in profile
        assert "exam_date" in profile
        assert "current_level" in profile

    def test_get_user_with_profile_no_profile(self, authenticated_client):
        """Test getting user without profile returns user data only."""
        response = authenticated_client.get("/v1/onboarding/me")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # User data should be present
        assert "user_id" in data
        assert "email" in data

        # Profile may be None or not present
        assert data.get("profile") is None or "profile" not in data

    def test_get_user_with_profile_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.get("/v1/onboarding/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
