"""
Integration tests for content API endpoints.

Tests:
- GET /v1/content/recommendations - Get personalized content recommendations
- GET /v1/content/chunks/{chunk_id} - Get specific content chunk
"""
import pytest
from fastapi import status
from uuid import uuid4


@pytest.mark.integration
class TestContentRecommendations:
    """Test content recommendation endpoints."""

    def test_get_adaptive_recommendations_success(self, authenticated_client_with_profile, test_cbap_course, test_content_chunks, test_user_competencies):
        """Test getting adaptive recommendations based on competency."""
        response = authenticated_client_with_profile.get(
            "/v1/content/recommendations",
            params={"strategy": "adaptive", "limit": 5}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["strategy_used"] == "adaptive"
        assert data["total_recommendations"] >= 0
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)

        # Check context includes weak KAs
        if data["context"]:
            assert "weakest_knowledge_areas" in data["context"]
            assert "explanation" in data["context"]

    def test_get_recent_mistakes_recommendations_success(self, authenticated_client_with_profile, test_content_chunks, test_question_attempts):
        """Test getting recommendations based on recent mistakes."""
        response = authenticated_client_with_profile.get(
            "/v1/content/recommendations",
            params={"strategy": "recent_mistakes", "limit": 5}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["strategy_used"] == "recent_mistakes"
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)

    def test_get_ka_specific_recommendations_success(self, authenticated_client_with_profile, test_cbap_course, test_content_chunks):
        """Test getting recommendations for a specific KA."""
        # Get first KA from course
        ka_id = test_cbap_course.knowledge_areas[0].ka_id

        response = authenticated_client_with_profile.get(
            "/v1/content/recommendations",
            params={
                "strategy": "ka_specific",
                "ka_id": str(ka_id),
                "limit": 5
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["strategy_used"] == "ka_specific"
        assert "recommendations" in data

        # All recommendations should be from the specified KA
        for rec in data["recommendations"]:
            assert rec["ka_id"] == str(ka_id)

    def test_get_recommendations_ka_specific_without_ka_id_fails(self, authenticated_client_with_profile):
        """Test ka_specific strategy without ka_id parameter fails."""
        response = authenticated_client_with_profile.get(
            "/v1/content/recommendations",
            params={"strategy": "ka_specific", "limit": 5}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "ka_id is required" in response.json()["detail"].lower()

    def test_get_recommendations_invalid_strategy_fails(self, authenticated_client_with_profile):
        """Test invalid strategy parameter fails validation."""
        response = authenticated_client_with_profile.get(
            "/v1/content/recommendations",
            params={"strategy": "invalid_strategy", "limit": 5}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_recommendations_without_profile_fails(self, authenticated_client):
        """Test recommendations fail if user has no profile."""
        response = authenticated_client.get(
            "/v1/content/recommendations",
            params={"strategy": "adaptive", "limit": 5}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "profile not found" in response.json()["detail"].lower()

    def test_get_recommendations_unauthenticated_fails(self, client):
        """Test recommendations require authentication."""
        response = client.get(
            "/v1/content/recommendations",
            params={"strategy": "adaptive", "limit": 5}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_recommendations_custom_limit(self, authenticated_client_with_profile, test_content_chunks):
        """Test custom limit parameter."""
        response = authenticated_client_with_profile.get(
            "/v1/content/recommendations",
            params={"strategy": "adaptive", "limit": 3}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should not exceed requested limit
        assert len(data["recommendations"]) <= 3

    def test_get_recommendations_limit_bounds_validation(self, authenticated_client_with_profile):
        """Test limit parameter bounds validation."""
        # Too small
        response = authenticated_client_with_profile.get(
            "/v1/content/recommendations",
            params={"limit": 0}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Too large
        response = authenticated_client_with_profile.get(
            "/v1/content/recommendations",
            params={"limit": 100}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_recommendation_response_structure(self, authenticated_client_with_profile, test_content_chunks):
        """Test recommendation response has correct structure."""
        response = authenticated_client_with_profile.get(
            "/v1/content/recommendations",
            params={"strategy": "adaptive", "limit": 5}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check top-level fields
        assert "strategy_used" in data
        assert "total_recommendations" in data
        assert "recommendations" in data
        assert "context" in data

        # Check recommendation structure if any exist
        if data["recommendations"]:
            rec = data["recommendations"][0]
            assert "chunk_id" in rec
            assert "content_title" in rec
            assert "content_text" in rec
            assert "ka_id" in rec
            assert "difficulty_level" in rec
            assert "expert_reviewed" in rec
            assert "review_status" in rec
            assert "helpfulness_score" in rec
            assert "efficacy_rate" in rec


@pytest.mark.integration
class TestContentChunkRetrieval:
    """Test content chunk retrieval endpoint."""

    def test_get_content_chunk_success(self, authenticated_client, test_content_chunks):
        """Test retrieving a specific content chunk."""
        chunk_id = test_content_chunks[0].chunk_id

        response = authenticated_client.get(f"/v1/content/chunks/{chunk_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["chunk_id"] == str(chunk_id)
        assert "content_title" in data
        assert "content_text" in data
        assert "helpfulness_score" in data
        assert "efficacy_rate" in data

    def test_get_content_chunk_logs_reading(self, authenticated_client, test_content_chunks, db_session):
        """Test that accessing a chunk logs it as consumed."""
        from app.models.learning import ReadingConsumed

        chunk_id = test_content_chunks[0].chunk_id

        # Get initial count
        initial_count = db_session.query(ReadingConsumed).count()

        # Access chunk
        response = authenticated_client.get(f"/v1/content/chunks/{chunk_id}")
        assert response.status_code == status.HTTP_200_OK

        # Verify reading was logged
        final_count = db_session.query(ReadingConsumed).count()
        assert final_count == initial_count + 1

    def test_get_content_chunk_not_duplicate_within_hour(self, authenticated_client, test_content_chunks, db_session):
        """Test that accessing same chunk within an hour doesn't create duplicate log."""
        from app.models.learning import ReadingConsumed

        chunk_id = test_content_chunks[0].chunk_id

        # Access chunk twice
        response1 = authenticated_client.get(f"/v1/content/chunks/{chunk_id}")
        assert response1.status_code == status.HTTP_200_OK

        initial_count = db_session.query(ReadingConsumed).count()

        response2 = authenticated_client.get(f"/v1/content/chunks/{chunk_id}")
        assert response2.status_code == status.HTTP_200_OK

        # Should not create duplicate
        final_count = db_session.query(ReadingConsumed).count()
        assert final_count == initial_count

    def test_get_content_chunk_not_found(self, authenticated_client):
        """Test retrieving non-existent chunk returns 404."""
        fake_id = uuid4()

        response = authenticated_client.get(f"/v1/content/chunks/{fake_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_get_inactive_content_chunk_not_found(self, authenticated_client, test_inactive_content_chunk):
        """Test that inactive chunks are not accessible."""
        chunk_id = test_inactive_content_chunk.chunk_id

        response = authenticated_client.get(f"/v1/content/chunks/{chunk_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_content_chunk_unauthenticated_fails(self, client, test_content_chunks):
        """Test chunk retrieval requires authentication."""
        chunk_id = test_content_chunks[0].chunk_id

        response = client.get(f"/v1/content/chunks/{chunk_id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_content_chunk_invalid_uuid(self, authenticated_client):
        """Test invalid UUID format returns 422."""
        response = authenticated_client.get("/v1/content/chunks/not-a-uuid")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.integration
class TestContentQualityMetrics:
    """Test that quality metrics are included in responses."""

    def test_recommendations_include_quality_metrics(self, authenticated_client_with_profile, test_content_chunks_with_feedback):
        """Test recommendations include helpfulness and efficacy scores."""
        response = authenticated_client_with_profile.get(
            "/v1/content/recommendations",
            params={"strategy": "adaptive", "limit": 5}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        if data["recommendations"]:
            rec = data["recommendations"][0]
            # These can be None if no feedback exists
            assert "helpfulness_score" in rec
            assert "efficacy_rate" in rec

    def test_chunk_includes_quality_metrics(self, authenticated_client, test_content_chunks_with_feedback):
        """Test chunk response includes quality metrics."""
        chunk_id = test_content_chunks_with_feedback[0].chunk_id

        response = authenticated_client.get(f"/v1/content/chunks/{chunk_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "helpfulness_score" in data
        assert "efficacy_rate" in data
