"""
Integration tests for Admin Dashboard API endpoints.

Tests admin-only endpoints for platform management.
"""
import pytest
from fastapi import status
from datetime import datetime, timedelta, timezone
from decimal import Decimal


@pytest.mark.integration
class TestAdminAuthentication:
    """Test admin authentication and authorization."""

    def test_admin_endpoints_require_authentication(self, client):
        """Test that admin endpoints return 401 without authentication."""
        response = client.get("/v1/admin/users")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_endpoints_require_admin_role(self, authenticated_client, test_learner_user):
        """Test that learner role gets 403 Forbidden on admin endpoints."""
        response = authenticated_client.get("/v1/admin/users")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Insufficient permissions" in response.json()["detail"]


@pytest.mark.integration
class TestAdminUserManagement:
    """Test GET /v1/admin/users endpoint."""

    def test_list_users_success(self, admin_authenticated_client, test_learner_user, test_admin_user, db):
        """Test successful user listing."""
        response = admin_authenticated_client.get("/v1/admin/users")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify structure
        assert "users" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "total_pages" in data

        # Should have at least 2 users (learner + admin)
        assert data["total"] >= 2
        assert len(data["users"]) >= 2

        # Check user structure
        user = data["users"][0]
        assert "user_id" in user
        assert "email" in user
        assert "first_name" in user
        assert "last_name" in user
        assert "role" in user
        assert "is_active" in user
        assert "created_at" in user

    def test_list_users_pagination(self, admin_authenticated_client, db):
        """Test user listing with pagination."""
        # Create additional users
        from app.models.user import User
        from app.utils.security import get_password_hash

        for i in range(5):
            user = User(
                email=f"user{i}@test.com",
                password_hash=get_password_hash("Test123"),
                first_name=f"User{i}",
                last_name="Test",
                role="learner"
            )
            db.add(user)
        db.commit()

        # Test pagination
        response = admin_authenticated_client.get("/v1/admin/users?page=1&per_page=3")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["page"] == 1
        assert data["per_page"] == 3
        assert len(data["users"]) <= 3
        assert data["total_pages"] >= 1

    def test_list_users_search(self, admin_authenticated_client, test_learner_user):
        """Test user search functionality."""
        response = admin_authenticated_client.get("/v1/admin/users?search=learner")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should find the learner user
        assert data["total"] >= 1
        emails = [user["email"] for user in data["users"]]
        assert "learner@test.com" in emails

    def test_list_users_filter_by_role(self, admin_authenticated_client, test_learner_user, test_admin_user):
        """Test filtering users by role."""
        response = admin_authenticated_client.get("/v1/admin/users?role=admin")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # All returned users should be admins
        for user in data["users"]:
            assert user["role"] == "admin"

    def test_list_users_filter_by_active_status(self, admin_authenticated_client, db, test_learner_user):
        """Test filtering users by active status."""
        # Deactivate the learner user
        test_learner_user.is_active = False
        db.commit()

        response = admin_authenticated_client.get("/v1/admin/users?is_active=false")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # All returned users should be inactive
        for user in data["users"]:
            assert user["is_active"] is False


@pytest.mark.integration
class TestAdminMetrics:
    """Test GET /v1/admin/metrics/overview endpoint."""

    def test_get_metrics_overview_success(self, admin_authenticated_client, test_learner_user, test_cbap_course, db):
        """Test successful metrics retrieval."""
        response = admin_authenticated_client.get("/v1/admin/metrics/overview")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify structure
        assert "users" in data
        assert "revenue" in data
        assert "engagement" in data
        assert "courses" in data

        # User metrics
        assert data["users"]["total"] >= 1
        assert data["users"]["active"] >= 0
        assert data["users"]["new_this_month"] >= 0

        # Revenue metrics
        assert "mrr" in data["revenue"]
        assert "arr" in data["revenue"]
        assert "total_revenue_this_month" in data["revenue"]

        # Engagement metrics
        assert "daily_active_users" in data["engagement"]
        assert "questions_answered_today" in data["engagement"]

        # Course metrics
        assert data["courses"]["total_courses"] >= 1
        assert data["courses"]["active_courses"] >= 0
        assert data["courses"]["total_questions"] >= 0

    def test_metrics_counts_users_correctly(self, admin_authenticated_client, db):
        """Test that user counts are accurate."""
        from app.models.user import User
        from app.utils.security import get_password_hash

        # Create 3 active users
        for i in range(3):
            user = User(
                email=f"active{i}@test.com",
                password_hash=get_password_hash("Test123"),
                first_name=f"Active{i}",
                last_name="User",
                role="learner",
                is_active=True
            )
            db.add(user)

        # Create 1 inactive user
        inactive_user = User(
            email="inactive@test.com",
            password_hash=get_password_hash("Test123"),
            first_name="Inactive",
            last_name="User",
            role="learner",
            is_active=False
        )
        db.add(inactive_user)
        db.commit()

        response = admin_authenticated_client.get("/v1/admin/metrics/overview")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should count all users (active + inactive)
        assert data["users"]["total"] >= 4
        # Should only count active users
        assert data["users"]["active"] >= 3


@pytest.mark.integration
class TestAdminCourseManagement:
    """Test admin course management endpoints."""

    def test_list_courses_success(self, admin_authenticated_client, test_cbap_course):
        """Test successful course listing."""
        response = admin_authenticated_client.get("/v1/admin/courses")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "courses" in data
        assert len(data["courses"]) >= 1

        # Check course structure
        course = data["courses"][0]
        assert "course_id" in course
        assert "course_code" in course
        assert "course_name" in course
        assert "status" in course
        assert "wizard_completed" in course
        assert "total_questions" in course
        assert "total_chunks" in course
        assert "created_at" in course

    def test_create_course_success(self, admin_authenticated_client, test_admin_user):
        """Test successful course creation."""
        response = admin_authenticated_client.post(
            "/v1/admin/courses",
            json={
                "course_code": "PSM1",
                "course_name": "Professional Scrum Master I",
                "version": "v2020",
                "passing_score_percentage": 85,
                "exam_duration_minutes": 60,
                "total_questions": 80,
                "min_questions_required": 150,
                "min_chunks_required": 40
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Verify response
        assert data["course_code"] == "PSM1"
        assert data["status"] == "draft"
        assert data["wizard_completed"] is False
        assert "auto_delete_at" in data
        assert data["auto_delete_at"] is not None

        # Verify auto_delete_at is ~7 days from now
        auto_delete = datetime.fromisoformat(data["auto_delete_at"].replace('Z', '+00:00'))
        expected_delete = datetime.now(timezone.utc) + timedelta(days=7)
        time_diff = abs((auto_delete - expected_delete).total_seconds())
        assert time_diff < 60  # Within 1 minute

    def test_create_course_duplicate_code(self, admin_authenticated_client, test_cbap_course):
        """Test creating course with duplicate code fails."""
        response = admin_authenticated_client.post(
            "/v1/admin/courses",
            json={
                "course_code": "CBAP",  # Already exists
                "course_name": "Duplicate Course",
                "version": "v1",
                "passing_score_percentage": 70
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"]

    def test_create_course_invalid_passing_score(self, admin_authenticated_client):
        """Test creating course with invalid passing score."""
        response = admin_authenticated_client.post(
            "/v1/admin/courses",
            json={
                "course_code": "TEST",
                "course_name": "Test Course",
                "version": "v1",
                "passing_score_percentage": 150  # Invalid: > 100
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.integration
class TestAdminKnowledgeAreaManagement:
    """Test knowledge area management endpoints."""

    def test_create_knowledge_areas_success(self, admin_authenticated_client, db):
        """Test successful knowledge area creation."""
        # First create a course
        from app.models.course import Course

        course = Course(
            course_code="PSM1",
            course_name="Professional Scrum Master I",
            version="v2020",
            status="draft",
            wizard_completed=False,
            passing_score_percentage=85
        )
        db.add(course)
        db.commit()
        db.refresh(course)

        # Create knowledge areas
        response = admin_authenticated_client.post(
            f"/v1/admin/courses/{course.course_id}/knowledge-areas",
            json={
                "knowledge_areas": [
                    {
                        "ka_code": "SCRUM_THEORY",
                        "ka_name": "Scrum Theory & Principles",
                        "ka_number": 1,
                        "weight_percentage": 33.33
                    },
                    {
                        "ka_code": "SCRUM_ROLES",
                        "ka_name": "Scrum Roles",
                        "ka_number": 2,
                        "weight_percentage": 33.33
                    },
                    {
                        "ka_code": "SCRUM_EVENTS",
                        "ka_name": "Scrum Events",
                        "ka_number": 3,
                        "weight_percentage": 33.34
                    }
                ]
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Verify response
        assert data["course_id"] == str(course.course_id)
        assert len(data["knowledge_areas"]) == 3
        assert Decimal(data["total_weight"]) == Decimal("100.00")
        assert data["validation_passed"] is True

        # Verify KA structure
        ka = data["knowledge_areas"][0]
        assert "ka_id" in ka
        assert "ka_code" in ka
        assert "ka_name" in ka
        assert "weight_percentage" in ka

    def test_create_knowledge_areas_weights_must_sum_to_100(self, admin_authenticated_client, db):
        """Test that KA weights must sum to 100%."""
        from app.models.course import Course

        course = Course(
            course_code="TEST",
            course_name="Test Course",
            version="v1",
            status="draft",
            passing_score_percentage=70
        )
        db.add(course)
        db.commit()
        db.refresh(course)

        # Create KAs with weights that don't sum to 100
        response = admin_authenticated_client.post(
            f"/v1/admin/courses/{course.course_id}/knowledge-areas",
            json={
                "knowledge_areas": [
                    {
                        "ka_code": "KA1",
                        "ka_name": "Knowledge Area 1",
                        "ka_number": 1,
                        "weight_percentage": 50.00
                    },
                    {
                        "ka_code": "KA2",
                        "ka_name": "Knowledge Area 2",
                        "ka_number": 2,
                        "weight_percentage": 40.00  # Total: 90% - should fail
                    }
                ]
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_knowledge_areas_course_not_found(self, admin_authenticated_client):
        """Test creating KAs for non-existent course."""
        response = admin_authenticated_client.post(
            "/v1/admin/courses/00000000-0000-0000-0000-000000000000/knowledge-areas",
            json={
                "knowledge_areas": [
                    {
                        "ka_code": "KA1",
                        "ka_name": "Knowledge Area 1",
                        "ka_number": 1,
                        "weight_percentage": 100.00
                    }
                ]
            }
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_knowledge_areas_only_for_draft_courses(self, admin_authenticated_client, test_cbap_course, db):
        """Test that KAs can only be added to draft courses."""
        # Set course to active
        test_cbap_course.status = "active"
        db.commit()

        response = admin_authenticated_client.post(
            f"/v1/admin/courses/{test_cbap_course.course_id}/knowledge-areas",
            json={
                "knowledge_areas": [
                    {
                        "ka_code": "NEW_KA",
                        "ka_name": "New Knowledge Area",
                        "ka_number": 7,
                        "weight_percentage": 100.00
                    }
                ]
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "draft" in response.json()["detail"].lower()


@pytest.mark.integration
class TestAdminCoursePublishing:
    """Test course publishing endpoint."""

    def test_publish_course_success(self, admin_authenticated_client, db, test_admin_user):
        """Test successful course publishing."""
        from app.models.course import Course, KnowledgeArea
        from app.models.question import Question, AnswerChoice
        from app.models.content import ContentChunk

        # Create a draft course
        course = Course(
            course_code="PSM1",
            course_name="Professional Scrum Master I",
            version="v2020",
            status="draft",
            wizard_completed=False,
            passing_score_percentage=85,
            min_questions_required=10,  # Lower threshold for testing
            min_chunks_required=5,
            auto_delete_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        db.add(course)
        db.commit()
        db.refresh(course)

        # Add knowledge areas
        ka = KnowledgeArea(
            course_id=course.course_id,
            ka_code="SCRUM",
            ka_name="Scrum Fundamentals",
            ka_number=1,
            weight_percentage=Decimal("100.00")
        )
        db.add(ka)
        db.commit()
        db.refresh(ka)

        # Add enough questions (10)
        for i in range(10):
            question = Question(
                course_id=course.course_id,
                ka_id=ka.ka_id,
                question_text=f"Test question {i}",
                question_type="multiple_choice",
                difficulty=Decimal("0.5"),
                source="custom",
                is_active=True
            )
            db.add(question)
            db.commit()
            db.refresh(question)

            # Add answer choices
            for j in range(4):
                choice = AnswerChoice(
                    question_id=question.question_id,
                    choice_order=j+1,
                    choice_text=f"Option {j+1}",
                    is_correct=(j == 0)
                )
                db.add(choice)

        # Add enough content chunks (5)
        for i in range(5):
            chunk = ContentChunk(
                course_id=course.course_id,
                ka_id=ka.ka_id,
                content_title=f"Chunk {i}",
                content_text=f"Content {i}",
                source_document="Test Doc"
            )
            db.add(chunk)

        db.commit()

        # Publish the course
        response = admin_authenticated_client.post(
            f"/v1/admin/courses/{course.course_id}/publish"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response
        assert data["status"] == "active"
        assert data["wizard_completed"] is True
        assert data["validation"]["min_questions_met"] is True
        assert data["validation"]["min_chunks_met"] is True
        assert data["validation"]["ka_weights_valid"] is True
        assert data["validation"]["ready_for_learners"] is True

        # Verify database changes
        db.refresh(course)
        assert course.status == "active"
        assert course.wizard_completed is True
        assert course.auto_delete_at is None
        assert course.is_active is True

    def test_publish_course_insufficient_questions(self, admin_authenticated_client, db):
        """Test publishing course with insufficient questions."""
        from app.models.course import Course, KnowledgeArea

        course = Course(
            course_code="TEST",
            course_name="Test Course",
            version="v1",
            status="draft",
            passing_score_percentage=70,
            min_questions_required=200
        )
        db.add(course)
        db.commit()
        db.refresh(course)

        # Add KA with valid weight
        ka = KnowledgeArea(
            course_id=course.course_id,
            ka_code="TEST_KA",
            ka_name="Test KA",
            ka_number=1,
            weight_percentage=Decimal("100.00")
        )
        db.add(ka)
        db.commit()

        # Try to publish without enough questions
        response = admin_authenticated_client.post(
            f"/v1/admin/courses/{course.course_id}/publish"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "publishing requirements" in response.json()["detail"].lower()

    def test_publish_course_already_published(self, admin_authenticated_client, test_cbap_course, db):
        """Test publishing already published course."""
        # Set course to active
        test_cbap_course.status = "active"
        db.commit()

        response = admin_authenticated_client.post(
            f"/v1/admin/courses/{test_cbap_course.course_id}/publish"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already published" in response.json()["detail"].lower()

    def test_publish_course_no_knowledge_areas(self, admin_authenticated_client, db):
        """Test publishing course without knowledge areas."""
        from app.models.course import Course

        course = Course(
            course_code="EMPTY",
            course_name="Empty Course",
            version="v1",
            status="draft",
            passing_score_percentage=70
        )
        db.add(course)
        db.commit()
        db.refresh(course)

        response = admin_authenticated_client.post(
            f"/v1/admin/courses/{course.course_id}/publish"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "knowledge area" in response.json()["detail"].lower()


@pytest.mark.integration
class TestBulkQuestionImport:
    """Test bulk question import endpoint."""

    def test_bulk_import_success(self, admin_authenticated_client, db):
        """Test successful bulk question import."""
        from app.models.course import Course, KnowledgeArea

        # Create a course with KA
        course = Course(
            course_code="TEST_IMPORT",
            course_name="Test Import Course",
            version="v1",
            status="draft",
            passing_score_percentage=70
        )
        db.add(course)
        db.commit()
        db.refresh(course)

        # Add KA
        ka = KnowledgeArea(
            course_id=course.course_id,
            ka_code="KA1",
            ka_name="Knowledge Area 1",
            ka_number=1,
            weight_percentage=Decimal("100.00")
        )
        db.add(ka)
        db.commit()

        # Bulk import 3 questions
        response = admin_authenticated_client.post(
            f"/v1/admin/courses/{course.course_id}/questions/bulk",
            json={
                "questions": [
                    {
                        "ka_code": "KA1",
                        "question_text": "What is the capital of France?",
                        "question_type": "multiple_choice",
                        "difficulty": 0.5,
                        "source": "vendor",
                        "answer_choices": [
                            {"choice_text": "Paris", "is_correct": True, "choice_order": 1},
                            {"choice_text": "London", "is_correct": False, "choice_order": 2},
                            {"choice_text": "Berlin", "is_correct": False, "choice_order": 3},
                            {"choice_text": "Madrid", "is_correct": False, "choice_order": 4}
                        ]
                    },
                    {
                        "ka_code": "KA1",
                        "question_text": "What is 2 + 2?",
                        "question_type": "multiple_choice",
                        "difficulty": 0.2,
                        "source": "custom",
                        "answer_choices": [
                            {"choice_text": "3", "is_correct": False, "choice_order": 1},
                            {"choice_text": "4", "is_correct": True, "choice_order": 2},
                            {"choice_text": "5", "is_correct": False, "choice_order": 3}
                        ]
                    },
                    {
                        "ka_code": "KA1",
                        "question_text": "Is Python a programming language?",
                        "question_type": "true_false",
                        "difficulty": 0.1,
                        "source": "generated",
                        "answer_choices": [
                            {"choice_text": "True", "is_correct": True, "choice_order": 1},
                            {"choice_text": "False", "is_correct": False, "choice_order": 2}
                        ]
                    }
                ]
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Verify response
        assert data["course_id"] == str(course.course_id)
        assert data["questions_imported"] == 3
        assert data["questions_failed"] == 0
        assert data["validation_summary"]["total_questions"] == 3
        assert data["validation_summary"]["imported"] == 3
        assert data["validation_summary"]["failed"] == 0

        # Verify questions were created in database
        from app.models.question import Question
        questions = db.query(Question).filter(Question.course_id == course.course_id).all()
        assert len(questions) == 3

    def test_bulk_import_invalid_ka_code(self, admin_authenticated_client, test_cbap_course, db):
        """Test bulk import with invalid KA code."""
        response = admin_authenticated_client.post(
            f"/v1/admin/courses/{test_cbap_course.course_id}/questions/bulk",
            json={
                "questions": [
                    {
                        "ka_code": "INVALID_KA",
                        "question_text": "Test question?",
                        "question_type": "multiple_choice",
                        "difficulty": 0.5,
                        "source": "vendor",
                        "answer_choices": [
                            {"choice_text": "A", "is_correct": True, "choice_order": 1},
                            {"choice_text": "B", "is_correct": False, "choice_order": 2}
                        ]
                    }
                ]
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["questions_imported"] == 0
        assert data["questions_failed"] == 1
        assert len(data["validation_summary"]["errors"]) >= 1
        assert "Invalid KA code" in data["validation_summary"]["errors"][0]

    def test_bulk_import_mixed_success_failure(self, admin_authenticated_client, db):
        """Test bulk import with both valid and invalid questions."""
        from app.models.course import Course, KnowledgeArea

        # Create course with KA
        course = Course(
            course_code="MIXED",
            course_name="Mixed Test",
            version="v1",
            status="draft",
            passing_score_percentage=70
        )
        db.add(course)
        db.commit()
        db.refresh(course)

        ka = KnowledgeArea(
            course_id=course.course_id,
            ka_code="VALID_KA",
            ka_name="Valid KA",
            ka_number=1,
            weight_percentage=Decimal("100.00")
        )
        db.add(ka)
        db.commit()

        # Import with mixed valid/invalid
        response = admin_authenticated_client.post(
            f"/v1/admin/courses/{course.course_id}/questions/bulk",
            json={
                "questions": [
                    {
                        "ka_code": "VALID_KA",
                        "question_text": "Valid question?",
                        "question_type": "multiple_choice",
                        "difficulty": 0.5,
                        "source": "vendor",
                        "answer_choices": [
                            {"choice_text": "A", "is_correct": True, "choice_order": 1},
                            {"choice_text": "B", "is_correct": False, "choice_order": 2}
                        ]
                    },
                    {
                        "ka_code": "INVALID_KA",
                        "question_text": "Invalid question?",
                        "question_type": "multiple_choice",
                        "difficulty": 0.5,
                        "source": "vendor",
                        "answer_choices": [
                            {"choice_text": "A", "is_correct": True, "choice_order": 1},
                            {"choice_text": "B", "is_correct": False, "choice_order": 2}
                        ]
                    },
                    {
                        "ka_code": "VALID_KA",
                        "question_text": "Another valid question?",
                        "question_type": "multiple_choice",
                        "difficulty": 0.3,
                        "source": "vendor",
                        "answer_choices": [
                            {"choice_text": "X", "is_correct": False, "choice_order": 1},
                            {"choice_text": "Y", "is_correct": True, "choice_order": 2}
                        ]
                    }
                ]
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["questions_imported"] == 2
        assert data["questions_failed"] == 1
        assert data["validation_summary"]["total_questions"] == 3

        # Verify only valid questions were created
        from app.models.question import Question
        questions = db.query(Question).filter(Question.course_id == course.course_id).all()
        assert len(questions) == 2

    def test_bulk_import_course_not_found(self, admin_authenticated_client):
        """Test bulk import for non-existent course."""
        response = admin_authenticated_client.post(
            "/v1/admin/courses/00000000-0000-0000-0000-000000000000/questions/bulk",
            json={
                "questions": [
                    {
                        "ka_code": "KA1",
                        "question_text": "What is this test question?",
                        "question_type": "multiple_choice",
                        "difficulty": 0.5,
                        "source": "vendor",
                        "answer_choices": [
                            {"choice_text": "A", "is_correct": True, "choice_order": 1},
                            {"choice_text": "B", "is_correct": False, "choice_order": 2}
                        ]
                    }
                ]
            }
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_bulk_import_validation_errors(self, admin_authenticated_client, test_cbap_course, db):
        """Test request validation (invalid question data)."""
        # Test: No correct answer
        response = admin_authenticated_client.post(
            f"/v1/admin/courses/{test_cbap_course.course_id}/questions/bulk",
            json={
                "questions": [
                    {
                        "ka_code": "REQUIREMENTS_ANALYSIS",
                        "question_text": "Test?",
                        "question_type": "multiple_choice",
                        "difficulty": 0.5,
                        "source": "vendor",
                        "answer_choices": [
                            {"choice_text": "A", "is_correct": False, "choice_order": 1},
                            {"choice_text": "B", "is_correct": False, "choice_order": 2}
                        ]
                    }
                ]
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test: Two correct answers
        response = admin_authenticated_client.post(
            f"/v1/admin/courses/{test_cbap_course.course_id}/questions/bulk",
            json={
                "questions": [
                    {
                        "ka_code": "REQUIREMENTS_ANALYSIS",
                        "question_text": "Test?",
                        "question_type": "multiple_choice",
                        "difficulty": 0.5,
                        "source": "vendor",
                        "answer_choices": [
                            {"choice_text": "A", "is_correct": True, "choice_order": 1},
                            {"choice_text": "B", "is_correct": True, "choice_order": 2}
                        ]
                    }
                ]
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
