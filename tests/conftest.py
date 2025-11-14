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


@pytest.fixture
def authenticated_client_with_profile(db, test_user_with_profile):
    """Return authenticated client with user profile."""
    from app.services.auth import create_access_token

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Expire all objects to force fresh queries from database
    db.expire_all()

    token = create_access_token({"sub": test_user_with_profile.user_id, "role": test_user_with_profile.role})

    with TestClient(app) as test_client:
        test_client.headers = {"Authorization": f"Bearer {token}"}
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_content_chunks(db, test_cbap_course):
    """Create test content chunks."""
    from app.models.content import ContentChunk

    chunks = []
    kas = db.query(KnowledgeArea).filter_by(course_id=test_cbap_course.course_id).all()

    for ka in kas[:3]:  # Create chunks for first 3 KAs
        for i in range(2):  # 2 chunks per KA
            chunk = ContentChunk(
                course_id=test_cbap_course.course_id,
                ka_id=ka.ka_id,
                content_title=f"Content for {ka.ka_name} - Part {i+1}",
                content_text=f"This is detailed content about {ka.ka_name}. " * 10,
                content_type="babok",
                source_document="BABOK v3",
                source_section=f"Section {ka.ka_code}",
                source_verified=True,
                expert_reviewed=True,
                review_status='approved',
                is_active=True
            )
            db.add(chunk)
            chunks.append(chunk)

    db.commit()
    return chunks


@pytest.fixture
def test_question_attempts(db, test_user_with_profile, test_questions):
    """Create test question attempts."""
    from app.models.learning import QuestionAttempt
    from datetime import datetime, timedelta

    # Create a practice session
    session = Session(
        user_id=test_user_with_profile.user_id,
        course_id=test_questions[0].course_id,
        session_type="practice",
        total_questions=10,
        is_completed=False
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    attempts = []
    # Create attempts for first 5 questions
    for i, question in enumerate(test_questions[:5]):
        # Get correct answer choice
        correct_choice = db.query(AnswerChoice).filter_by(
            question_id=question.question_id,
            is_correct=True
        ).first()

        # Alternate between correct and incorrect
        is_correct = (i % 2 == 0)
        selected_choice = correct_choice if is_correct else db.query(AnswerChoice).filter_by(
            question_id=question.question_id,
            is_correct=False
        ).first()

        attempt = QuestionAttempt(
            session_id=session.session_id,
            user_id=test_user_with_profile.user_id,
            question_id=question.question_id,
            selected_choice_id=selected_choice.choice_id,
            is_correct=is_correct,
            time_spent_seconds=30 + i * 10,
            attempted_at=datetime.utcnow() - timedelta(minutes=10-i)
        )
        db.add(attempt)
        attempts.append(attempt)

    db.commit()
    return attempts


# Additional fixtures for mock exam tests
@pytest.fixture
def test_questions_full(db, test_cbap_course):
    """Create 240+ questions for mock exam testing."""
    questions = []
    kas = db.query(KnowledgeArea).filter_by(course_id=test_cbap_course.course_id).all()

    # Create 40 questions per KA (6 KAs = 240 questions)
    # Mock exams need 120 questions distributed by KA weight (max 30% = 36 questions)
    for ka in kas:
        for i in range(40):
            # Vary difficulty
            difficulty = Decimal(str(0.3 + (i % 3) * 0.2))  # 0.3, 0.5, 0.7

            question = Question(
                course_id=test_cbap_course.course_id,
                ka_id=ka.ka_id,
                question_text=f"Mock exam question {i+1} for {ka.ka_name}",
                question_type="multiple_choice",
                difficulty=difficulty,
                discrimination=None,
                source="custom",
                is_active=True
            )
            db.add(question)
            db.commit()
            db.refresh(question)

            # Create 4 answer choices
            for j in range(4):
                choice = AnswerChoice(
                    question_id=question.question_id,
                    choice_order=j + 1,
                    choice_text=f"Option {chr(65+j)}",
                    is_correct=(j == 1),  # Option B is correct
                    explanation=f"Explanation for option {chr(65+j)}"
                )
                db.add(choice)

            questions.append(question)

    db.commit()
    return questions


@pytest.fixture
def test_inactive_content_chunk(db, test_cbap_course):
    """Create an inactive content chunk."""
    from app.models.content import ContentChunk

    kas = db.query(KnowledgeArea).filter_by(course_id=test_cbap_course.course_id).first()

    chunk = ContentChunk(
        course_id=test_cbap_course.course_id,
        ka_id=kas.ka_id,
        content_title="Inactive Content",
        content_text="This content is not active",
        content_type="babok",
        source_document="BABOK v3",
        is_active=False  # Inactive
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


@pytest.fixture
def test_content_chunks_with_feedback(db, test_cbap_course, test_user_with_profile):
    """Create content chunks with feedback."""
    from app.models.content import ContentChunk, ContentFeedback

    chunks = []
    kas = db.query(KnowledgeArea).filter_by(course_id=test_cbap_course.course_id).all()

    for ka in kas[:2]:
        chunk = ContentChunk(
            course_id=test_cbap_course.course_id,
            ka_id=ka.ka_id,
            content_title=f"Content with feedback for {ka.ka_name}",
            content_text=f"Detailed content about {ka.ka_name}. " * 10,
            content_type="babok",
            source_document="BABOK v3",
            expert_reviewed=True,
            source_verified=True,
            review_status='approved',
            is_active=True
        )
        db.add(chunk)
        db.commit()
        db.refresh(chunk)

        # Add feedback
        feedback = ContentFeedback(
            chunk_id=chunk.chunk_id,
            user_id=test_user_with_profile.user_id,
            was_helpful=True,
            feedback_text="Very helpful content"
        )
        db.add(feedback)
        chunks.append(chunk)

    db.commit()
    return chunks


@pytest.fixture
def test_question_attempts_recent(db, test_user_with_profile, test_questions_full):
    """Create recent question attempts."""
    from app.models.learning import QuestionAttempt
    from datetime import datetime, timedelta

    # Create a session
    session = Session(
        user_id=test_user_with_profile.user_id,
        course_id=test_questions_full[0].course_id,
        session_type="practice",
        total_questions=60,
        is_completed=False
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    attempts = []
    # Create 60 recent attempts (within last 50 questions limit)
    for i, question in enumerate(test_questions_full[:60]):
        correct_choice = db.query(AnswerChoice).filter_by(
            question_id=question.question_id,
            is_correct=True
        ).first()

        attempt = QuestionAttempt(
            session_id=session.session_id,
            user_id=test_user_with_profile.user_id,
            question_id=question.question_id,
            selected_choice_id=correct_choice.choice_id,
            is_correct=True,
            time_spent_seconds=60,
            attempted_at=datetime.utcnow() - timedelta(minutes=60-i)
        )
        db.add(attempt)
        attempts.append(attempt)

    db.commit()
    return attempts


@pytest.fixture
def test_completed_mock_exam(db, test_user_with_profile, test_questions_full):
    """Create a completed mock exam with results."""
    from app.models.learning import QuestionAttempt

    # Create mock exam session
    session = Session(
        user_id=test_user_with_profile.user_id,
        course_id=test_questions_full[0].course_id,
        session_type="mock_exam",
        total_questions=100,
        is_completed=True
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Create attempts for 100 questions (70% correct)
    for i, question in enumerate(test_questions_full[:100]):
        correct_choice = db.query(AnswerChoice).filter_by(
            question_id=question.question_id,
            is_correct=True
        ).first()

        incorrect_choice = db.query(AnswerChoice).filter_by(
            question_id=question.question_id,
            is_correct=False
        ).first()

        # 70% correct
        is_correct = (i % 10) < 7
        selected = correct_choice if is_correct else incorrect_choice

        attempt = QuestionAttempt(
            session_id=session.session_id,
            user_id=test_user_with_profile.user_id,
            question_id=question.question_id,
            selected_choice_id=selected.choice_id,
            is_correct=is_correct,
            time_spent_seconds=120
        )
        db.add(attempt)

    db.commit()
    db.refresh(session)
    return session


@pytest.fixture
def test_completed_mock_exam_passing(db, test_user_with_profile, test_questions_full):
    """Create a completed mock exam with passing score (75%)."""
    from app.models.learning import QuestionAttempt

    session = Session(
        user_id=test_user_with_profile.user_id,
        course_id=test_questions_full[0].course_id,
        session_type="mock_exam",
        total_questions=100,
        is_completed=True
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # 75% correct
    for i, question in enumerate(test_questions_full[:100]):
        correct_choice = db.query(AnswerChoice).filter_by(
            question_id=question.question_id,
            is_correct=True
        ).first()

        incorrect_choice = db.query(AnswerChoice).filter_by(
            question_id=question.question_id,
            is_correct=False
        ).first()

        is_correct = (i % 4) != 0  # 75% correct
        selected = correct_choice if is_correct else incorrect_choice

        attempt = QuestionAttempt(
            session_id=session.session_id,
            user_id=test_user_with_profile.user_id,
            question_id=question.question_id,
            selected_choice_id=selected.choice_id,
            is_correct=is_correct,
            time_spent_seconds=120
        )
        db.add(attempt)

    db.commit()
    db.refresh(session)
    return session


@pytest.fixture
def test_completed_mock_exam_failing(db, test_user_with_profile, test_questions_full):
    """Create a completed mock exam with failing score (50%)."""
    from app.models.learning import QuestionAttempt

    session = Session(
        user_id=test_user_with_profile.user_id,
        course_id=test_questions_full[0].course_id,
        session_type="mock_exam",
        total_questions=100,
        is_completed=True
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # 50% correct
    for i, question in enumerate(test_questions_full[:100]):
        correct_choice = db.query(AnswerChoice).filter_by(
            question_id=question.question_id,
            is_correct=True
        ).first()

        incorrect_choice = db.query(AnswerChoice).filter_by(
            question_id=question.question_id,
            is_correct=False
        ).first()

        is_correct = (i % 2) == 0  # 50% correct
        selected = correct_choice if is_correct else incorrect_choice

        attempt = QuestionAttempt(
            session_id=session.session_id,
            user_id=test_user_with_profile.user_id,
            question_id=question.question_id,
            selected_choice_id=selected.choice_id,
            is_correct=is_correct,
            time_spent_seconds=120
        )
        db.add(attempt)

    db.commit()
    db.refresh(session)
    return session


@pytest.fixture
def test_incomplete_mock_exam(db, test_user_with_profile, test_questions_full):
    """Create an incomplete mock exam."""
    session = Session(
        user_id=test_user_with_profile.user_id,
        course_id=test_questions_full[0].course_id,
        session_type="mock_exam",
        total_questions=100,
        is_completed=False  # Incomplete
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@pytest.fixture
def test_practice_session(db, test_user_with_profile, test_questions):
    """Create a practice session (not mock exam)."""
    session = Session(
        user_id=test_user_with_profile.user_id,
        course_id=test_questions[0].course_id,
        session_type="practice",  # Not mock_exam
        total_questions=10,
        is_completed=True
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@pytest.fixture
def other_user_mock_exam(db, test_admin_user, test_questions_full):
    """Create a mock exam for a different user."""
    session = Session(
        user_id=test_admin_user.user_id,  # Different user
        course_id=test_questions_full[0].course_id,
        session_type="mock_exam",
        total_questions=100,
        is_completed=True
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@pytest.fixture
def test_completed_mock_exam_with_time(db, test_user_with_profile, test_questions_full):
    """Create a completed mock exam with time tracking."""
    from app.models.learning import QuestionAttempt

    session = Session(
        user_id=test_user_with_profile.user_id,
        course_id=test_questions_full[0].course_id,
        session_type="mock_exam",
        total_questions=100,
        is_completed=True
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Create attempts with varying time
    for i, question in enumerate(test_questions_full[:100]):
        correct_choice = db.query(AnswerChoice).filter_by(
            question_id=question.question_id,
            is_correct=True
        ).first()

        # Time ranges from 60 to 180 seconds
        time_spent = 60 + (i % 13) * 10

        attempt = QuestionAttempt(
            session_id=session.session_id,
            user_id=test_user_with_profile.user_id,
            question_id=question.question_id,
            selected_choice_id=correct_choice.choice_id,
            is_correct=True,
            time_spent_seconds=time_spent
        )
        db.add(attempt)

    db.commit()

    # Calculate total duration from all attempts
    total_duration = sum(60 + (i % 13) * 10 for i in range(100))
    session.duration_seconds = total_duration
    db.commit()
    db.refresh(session)
    return session
