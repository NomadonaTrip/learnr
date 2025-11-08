"""
Pytest configuration and shared fixtures.

This file is automatically loaded by pytest and provides
fixtures available to all test files.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from typing import Generator
import os

# Set test environment variables before importing app (only if not already set)
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/learnr_test_db")
os.environ.setdefault("ENCRYPTION_KEY", "8B7ZqnP_QvKxWmN5rF2jYhT3cD9gV6sA1wL4eR8uI0o=")  # Valid Fernet key for testing
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-testing-use-strong-key-in-production")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

from app.models.database import Base, get_db
from app.main import app


# Test database engine - use DATABASE_URL from environment
TEST_DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator:
    """
    Create a fresh database session for each test.
    Rolls back all changes after the test completes.
    """
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create session
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db) -> Generator:
    """
    Create a test client with database dependency override.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password": "SecurePassword123!",
        "first_name": "Test",
        "last_name": "User"
    }


@pytest.fixture
def sample_course_data():
    """Sample course data for testing."""
    return {
        "course_code": "CBAP",
        "course_name": "Certified Business Analysis Professional",
        "description": "Business Analysis certification",
        "version": "v3",
        "passing_score_percentage": 70,
        "total_questions": 120
    }


@pytest.fixture
def sample_question_data():
    """Sample question data for testing."""
    return {
        "question_text": "What is the primary purpose of requirements elicitation?",
        "question_type": "multiple_choice",
        "difficulty": 0.5,
        "source": "vendor"
    }


# ============================================================================
# Enhanced Fixtures for Comprehensive Testing
# ============================================================================

from app.models.user import User, UserProfile
from app.models.course import Course, KnowledgeArea
from app.models.question import Question, AnswerChoice
from app.models.learning import Session, UserCompetency
from app.utils.security import get_password_hash
from decimal import Decimal
import uuid


@pytest.fixture
def test_learner_user(db):
    """Create a test learner user."""
    user = User(
        email="learner@test.com",
        password_hash=get_password_hash("Test123Pass"),
        first_name="Test",
        last_name="Learner",
        role="learner",
        is_active=True,
        email_verified=True,
        two_factor_enabled=False,
        must_change_password=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_admin_user(db):
    """Create a test admin user."""
    user = User(
        email="admin@test.com",
        password_hash=get_password_hash("Admin123Pass"),
        first_name="Admin",
        last_name="User",
        role="admin",
        is_active=True,
        email_verified=True,
        two_factor_enabled=False,
        must_change_password=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_super_admin_user(db):
    """Create a test super admin user."""
    user = User(
        email="superadmin@test.com",
        password_hash=get_password_hash("SuperAdmin123Pass"),
        first_name="Super",
        last_name="Admin",
        role="super_admin",
        is_active=True,
        email_verified=True,
        two_factor_enabled=False,
        must_change_password=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_cbap_course(db):
    """Create a test CBAP course with all knowledge areas."""
    course = Course(
        course_code="CBAP",
        course_name="Certified Business Analysis Professional",
        description="IIBA CBAP Certification",
        version="v3",
        status="active",
        wizard_completed=True,
        passing_score_percentage=70,
        exam_duration_minutes=210,
        total_questions=120,
        min_questions_required=200,
        min_chunks_required=50,
        is_active=True
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    # Create 6 Knowledge Areas
    knowledge_areas_data = [
        {"ka_code": "BA-PA", "ka_name": "Business Analysis Planning and Monitoring",
         "ka_number": 1, "weight_percentage": Decimal("15.00")},
        {"ka_code": "BA-ED", "ka_name": "Elicitation and Collaboration",
         "ka_number": 2, "weight_percentage": Decimal("20.00")},
        {"ka_code": "BA-RM", "ka_name": "Requirements Life Cycle Management",
         "ka_number": 3, "weight_percentage": Decimal("16.00")},
        {"ka_code": "BA-SA", "ka_name": "Strategy Analysis",
         "ka_number": 4, "weight_percentage": Decimal("13.00")},
        {"ka_code": "BA-RAD", "ka_name": "Requirements Analysis and Design Definition",
         "ka_number": 5, "weight_percentage": Decimal("30.00")},
        {"ka_code": "BA-SE", "ka_name": "Solution Evaluation",
         "ka_number": 6, "weight_percentage": Decimal("6.00")}
    ]

    for ka_data in knowledge_areas_data:
        ka = KnowledgeArea(course_id=course.course_id, **ka_data)
        db.add(ka)

    db.commit()
    db.refresh(course)
    return course


@pytest.fixture
def test_questions(db, test_cbap_course):
    """Create test questions for each knowledge area."""
    questions = []
    kas = db.query(KnowledgeArea).filter_by(course_id=test_cbap_course.course_id).all()

    for ka in kas:
        # Create 3 questions per KA with varying difficulty
        for i, difficulty in enumerate([0.3, 0.5, 0.7]):
            question = Question(
                course_id=test_cbap_course.course_id,
                ka_id=ka.ka_id,
                question_text=f"Test question {i+1} for {ka.ka_name}",
                question_type="multiple_choice",
                difficulty=Decimal(str(difficulty)),
                discrimination=None,
                source="custom",
                is_active=True
            )
            db.add(question)
            db.commit()
            db.refresh(question)

            # Create 4 answer choices
            choices_data = [
                {"order": 1, "text": "Option A - Incorrect", "is_correct": False},
                {"order": 2, "text": "Option B - Correct", "is_correct": True},
                {"order": 3, "text": "Option C - Incorrect", "is_correct": False},
                {"order": 4, "text": "Option D - Incorrect", "is_correct": False}
            ]

            for choice_data in choices_data:
                choice = AnswerChoice(
                    question_id=question.question_id,
                    choice_order=choice_data["order"],
                    choice_text=choice_data["text"],
                    is_correct=choice_data["is_correct"],
                    explanation=f"Explanation for option {choice_data['order']}"
                )
                db.add(choice)

            questions.append(question)

    db.commit()
    return questions


@pytest.fixture
def test_user_with_profile(db, test_learner_user, test_cbap_course):
    """Create a test user with completed onboarding profile."""
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
    db.refresh(profile)
    return test_learner_user


@pytest.fixture
def test_user_competencies(db, test_user_with_profile, test_cbap_course):
    """Create initial competency scores for user."""
    competencies = []
    kas = db.query(KnowledgeArea).filter_by(course_id=test_cbap_course.course_id).all()

    for ka in kas:
        competency = UserCompetency(
            user_id=test_user_with_profile.user_id,
            ka_id=ka.ka_id,
            competency_score=Decimal("0.50"),
            attempts_count=0,
            correct_count=0,
            incorrect_count=0
        )
        db.add(competency)
        competencies.append(competency)

    db.commit()
    return competencies


@pytest.fixture
def authenticated_client(db, test_learner_user):
    """Return a test client with authentication token."""
    from app.services.auth import create_access_token

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    token = create_access_token({"sub": test_learner_user.user_id, "role": test_learner_user.role})

    with TestClient(app) as test_client:
        test_client.headers = {"Authorization": f"Bearer {token}"}
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_admin_with_profile(db, test_admin_user, test_cbap_course):
    """Create admin user with profile."""
    from datetime import date

    profile = UserProfile(
        user_id=test_admin_user.user_id,
        course_id=test_cbap_course.course_id,
        exam_date=date(2025, 12, 31),
        current_level="advanced",
        target_score_percentage=95,
        daily_commitment_minutes=120
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return test_admin_user


@pytest.fixture
def admin_authenticated_client(db, test_admin_user):
    """Return a test client with admin authentication token."""
    from app.services.auth import create_access_token

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    token = create_access_token({"sub": test_admin_user.user_id, "role": test_admin_user.role})

    with TestClient(app) as test_client:
        test_client.headers = {"Authorization": f"Bearer {token}"}
        yield test_client

    app.dependency_overrides.clear()
