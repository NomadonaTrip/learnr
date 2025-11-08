"""
Seed database with test data for LearnR MVP.

Creates:
- CBAP course with 6 knowledge areas
- Sample questions for each KA
- Test users
"""
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.models.database import SessionLocal, engine, Base
from app.models.course import Course, KnowledgeArea, Domain
from app.models.question import Question, AnswerChoice
from app.models.user import User
from app.utils.security import get_password_hash
from decimal import Decimal
from datetime import datetime
import uuid


def seed_database():
    """Seed database with test data."""
    print("=" * 60)
    print("LearnR Database Seeding Script")
    print("=" * 60)
    print()
    
    db = SessionLocal()
    
    try:
        # 1. Create CBAP Course
        print("📚 Creating CBAP course...")
        cbap_course = Course(
            course_code="CBAP",
            course_name="Certified Business Analysis Professional",
            description="IIBA CBAP Certification - Business Analysis Body of Knowledge v3",
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
        db.add(cbap_course)
        db.commit()
        db.refresh(cbap_course)
        print(f"   ✓ Created course: {cbap_course.course_name}")
        print()
        
        # 2. Create 6 Knowledge Areas for CBAP
        print("📖 Creating 6 Knowledge Areas...")
        knowledge_areas_data = [
            {
                "ka_code": "BA-PA",
                "ka_name": "Business Analysis Planning and Monitoring",
                "ka_number": 1,
                "weight_percentage": Decimal("15.00"),
                "description": "Planning BA activities and monitoring progress"
            },
            {
                "ka_code": "BA-ED",
                "ka_name": "Elicitation and Collaboration",
                "ka_number": 2,
                "weight_percentage": Decimal("20.00"),
                "description": "Gathering and managing stakeholder input"
            },
            {
                "ka_code": "BA-RM",
                "ka_name": "Requirements Life Cycle Management",
                "ka_number": 3,
                "weight_percentage": Decimal("16.00"),
                "description": "Managing requirements throughout their lifecycle"
            },
            {
                "ka_code": "BA-SA",
                "ka_name": "Strategy Analysis",
                "ka_number": 4,
                "weight_percentage": Decimal("13.00"),
                "description": "Analyzing business strategy and defining scope"
            },
            {
                "ka_code": "BA-RAD",
                "ka_name": "Requirements Analysis and Design Definition",
                "ka_number": 5,
                "weight_percentage": Decimal("30.00"),
                "description": "Analyzing and defining requirements"
            },
            {
                "ka_code": "BA-SE",
                "ka_name": "Solution Evaluation",
                "ka_number": 6,
                "weight_percentage": Decimal("6.00"),
                "description": "Evaluating proposed solutions"
            }
        ]
        
        knowledge_areas = []
        for ka_data in knowledge_areas_data:
            ka = KnowledgeArea(
                course_id=cbap_course.course_id,
                **ka_data
            )
            db.add(ka)
            knowledge_areas.append(ka)
        
        db.commit()
        
        # Refresh all KAs to get their IDs
        for ka in knowledge_areas:
            db.refresh(ka)
            print(f"   ✓ {ka.ka_code}: {ka.ka_name} ({ka.weight_percentage}%)")
        
        # Verify weights sum to 100%
        total_weight = sum(ka.weight_percentage for ka in knowledge_areas)
        print(f"\n   Total weight: {total_weight}% (should be 100%)")
        print()
        
        # 3. Create sample questions for each KA
        print("❓ Creating sample questions...")
        questions_created = 0
        
        for ka in knowledge_areas:
            # Create 5 questions per KA (30 total for testing)
            for i in range(5):
                difficulty = Decimal(f"0.{30 + i * 10}")  # 0.30, 0.40, 0.50, 0.60, 0.70
                
                question = Question(
                    course_id=cbap_course.course_id,
                    ka_id=ka.ka_id,
                    question_text=f"Sample question {i+1} for {ka.ka_name}. This tests knowledge of {ka.ka_code}. Which of the following is correct?",
                    question_type="multiple_choice",
                    difficulty=difficulty,
                    discrimination=None,  # NULL for MVP (1PL IRT)
                    source="vendor",
                    is_active=True
                )
                db.add(question)
                db.commit()
                db.refresh(question)
                
                # Create 4 answer choices
                choices = [
                    {"order": 1, "text": f"Option A - Incorrect answer for {ka.ka_code}", "is_correct": False},
                    {"order": 2, "text": f"Option B - Correct answer for {ka.ka_code}", "is_correct": True},
                    {"order": 3, "text": f"Option C - Incorrect answer for {ka.ka_code}", "is_correct": False},
                    {"order": 4, "text": f"Option D - Incorrect answer for {ka.ka_code}", "is_correct": False},
                ]

                for choice_data in choices:
                    choice = AnswerChoice(
                        question_id=question.question_id,
                        choice_order=choice_data["order"],
                        choice_text=choice_data["text"],
                        is_correct=choice_data["is_correct"],
                        explanation=f"Explanation for choice {choice_data['order']}: This is the {'correct' if choice_data['is_correct'] else 'incorrect'} answer because..."
                    )
                    db.add(choice)
                
                questions_created += 1
            
            print(f"   ✓ Created 5 questions for {ka.ka_code}")
        
        db.commit()
        print(f"\n   Total questions created: {questions_created}")
        print()
        
        # 4. Create test users
        print("👤 Creating test users...")
        
        # Test learner
        test_learner = User(
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
        db.add(test_learner)
        
        # Test admin
        test_admin = User(
            email="admin@test.com",
            password_hash=get_password_hash("Admin123Pass"),
            first_name="Test",
            last_name="Admin",
            role="admin",
            is_active=True,
            email_verified=True,
            two_factor_enabled=False,
            must_change_password=False
        )
        db.add(test_admin)
        
        db.commit()
        print("   ✓ Test Learner: learner@test.com / Test123Pass")
        print("   ✓ Test Admin:   admin@test.com / Admin123Pass")
        print()
        
        print("=" * 60)
        print("✅ Database seeding completed successfully!")
        print("=" * 60)
        print()
        print("Summary:")
        print(f"  - Courses: 1 (CBAP)")
        print(f"  - Knowledge Areas: 6")
        print(f"  - Questions: {questions_created}")
        print(f"  - Answer Choices: {questions_created * 4}")
        print(f"  - Test Users: 2")
        print()
        print("Next steps:")
        print("  1. Start API server: uvicorn app.main:app --reload")
        print("  2. Login as test learner: learner@test.com / Test123Pass")
        print("  3. Complete onboarding")
        print("  4. Start practice session")
        print()
        
    except Exception as e:
        print(f"\n❌ Error seeding database: {e}")
        db.rollback()
        raise
    
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
