#!/usr/bin/env python
"""
Seed CBAP Course Data

Creates a complete CBAP course with knowledge areas, domains, and sample questions.
Uses the seed data from docs/samples/cbap_seed_data.json.

Usage:
    python scripts/seed_cbap_course.py
    python scripts/seed_cbap_course.py --file custom_seed_data.json
    python scripts/seed_cbap_course.py --skip-questions

Environment Variables:
    DATABASE_URL: PostgreSQL connection string (required)
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.course import Course, KnowledgeArea, Domain
from app.models.question import Question, AnswerChoice


def load_seed_data(file_path: str) -> dict:
    """Load seed data from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: Seed data file not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in seed data file")
        print(f"   Line {e.lineno}: {e.msg}")
        sys.exit(1)


def create_course(db_session, course_data: dict) -> Course:
    """Create CBAP course."""
    print("\n📚 Creating CBAP course...")

    course = Course(
        course_code=course_data['course_code'],
        course_name=course_data['course_name'],
        version=course_data['version'],
        description=course_data.get('description'),
        passing_score_percentage=course_data['passing_score_percentage'],
        exam_duration_minutes=course_data.get('exam_duration_minutes'),
        total_questions=course_data.get('total_questions'),
        min_questions_required=course_data.get('min_questions_required', 200),
        min_chunks_required=course_data.get('min_chunks_required', 50),
        status=course_data.get('status', 'draft'),
        wizard_completed=False,
        created_at=datetime.now(timezone.utc)
    )

    db_session.add(course)
    db_session.flush()

    print(f"   ✓ Course created: {course.course_name} (ID: {course.course_id})")
    return course


def create_knowledge_areas(db_session, course_id, ka_data_list: list) -> dict:
    """Create knowledge areas and domains."""
    print(f"\n📖 Creating {len(ka_data_list)} knowledge areas...")

    ka_map = {}  # Map ka_code to ka_id for question creation
    ka_objects = []  # Store KA objects for domain creation

    # Create all knowledge areas first (without flush)
    for ka_data in ka_data_list:
        ka = KnowledgeArea(
            course_id=course_id,
            ka_code=ka_data['ka_code'],
            ka_name=ka_data['ka_name'],
            ka_number=ka_data['ka_number'],
            weight_percentage=Decimal(str(ka_data['weight_percentage'])),
            description=ka_data.get('description'),
            created_at=datetime.now(timezone.utc)
        )

        db_session.add(ka)
        ka_objects.append((ka, ka_data))

        print(f"   ✓ KA {ka.ka_number}: {ka.ka_name} ({ka.weight_percentage}%)")

    # Flush all KAs together (trigger validates total = 100%)
    db_session.flush()

    # Now create domains for each KA
    for ka, ka_data in ka_objects:
        ka_map[ka.ka_code] = ka.ka_id

        if 'domains' in ka_data:
            for domain_data in ka_data['domains']:
                domain = Domain(
                    ka_id=ka.ka_id,
                    domain_code=domain_data['domain_code'],
                    domain_name=domain_data['domain_name'],
                    domain_number=domain_data['domain_number'],
                    description=domain_data.get('description'),
                    created_at=datetime.now(timezone.utc)
                )

                db_session.add(domain)

            print(f"      → {len(ka_data['domains'])} domains added to {ka.ka_code}")

    db_session.flush()

    # Verify weights sum to 100%
    total_weight = sum(Decimal(str(ka['weight_percentage'])) for ka in ka_data_list)
    print(f"\n   Total KA weight: {total_weight}% (must be 100%)")

    if not (99.99 <= total_weight <= 100.01):
        print(f"   ⚠️  Warning: KA weights don't sum to 100%")

    return ka_map


def create_questions(db_session, course_id, ka_map: dict, questions_data: list):
    """Create sample questions."""
    print(f"\n❓ Creating {len(questions_data)} sample questions...")

    created = 0
    skipped = 0

    for q_data in questions_data:
        ka_code = q_data['ka_code']

        if ka_code not in ka_map:
            print(f"   ⚠️  Skipping question: KA code '{ka_code}' not found")
            skipped += 1
            continue

        # Get domain_id if domain_code provided
        domain_id = None
        if 'domain_code' in q_data and q_data['domain_code']:
            domain = db_session.query(Domain).filter(
                Domain.ka_id == ka_map[ka_code],
                Domain.domain_code == q_data['domain_code']
            ).first()

            if domain:
                domain_id = domain.domain_id
            else:
                print(f"   ⚠️  Domain '{q_data['domain_code']}' not found for KA '{ka_code}'")

        # Create question
        question = Question(
            course_id=course_id,
            ka_id=ka_map[ka_code],
            domain_id=domain_id,
            question_text=q_data['question_text'],
            question_type=q_data['question_type'],
            difficulty=Decimal(str(q_data['difficulty'])),
            source=q_data['source'],
            is_active=True,
            times_used=0,
            times_correct=0,
            created_at=datetime.now(timezone.utc)
        )

        db_session.add(question)
        db_session.flush()

        # Create answer choices
        for choice_data in q_data['answer_choices']:
            choice = AnswerChoice(
                question_id=question.question_id,
                choice_text=choice_data['choice_text'],
                is_correct=choice_data['is_correct'],
                choice_order=choice_data['choice_order'],
                explanation=choice_data.get('explanation'),
                created_at=datetime.now(timezone.utc)
            )

            db_session.add(choice)

        created += 1

    db_session.flush()

    print(f"   ✓ Created {created} questions")
    if skipped > 0:
        print(f"   ⚠️  Skipped {skipped} questions")

    return created


def main():
    """Main seed script execution."""
    parser = argparse.ArgumentParser(
        description='Seed CBAP course with knowledge areas, domains, and sample questions',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--file',
        help='Path to seed data JSON file',
        default='docs/samples/cbap_seed_data.json'
    )
    parser.add_argument(
        '--skip-questions',
        action='store_true',
        help='Skip creating sample questions (only create course and KAs)'
    )
    parser.add_argument(
        '--db-url',
        help='Database URL (default: from DATABASE_URL env var)',
        default=None
    )

    args = parser.parse_args()

    # Get database URL
    db_url = args.db_url or settings.DATABASE_URL
    if not db_url:
        print("❌ Error: DATABASE_URL not set")
        print("   Set via environment variable or --db-url argument")
        sys.exit(1)

    # Load seed data
    print(f"Loading seed data from {args.file}...")
    seed_data = load_seed_data(args.file)

    # Create database session
    try:
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
    except Exception as e:
        print(f"❌ Error: Failed to connect to database: {e}")
        sys.exit(1)

    # Display summary
    print("\n" + "="*70)
    print("CBAP Course Seed Data Import")
    print("="*70)
    print(f"Course: {seed_data['course']['course_name']}")
    print(f"Knowledge Areas: {len(seed_data['knowledge_areas'])}")

    total_domains = sum(
        len(ka.get('domains', []))
        for ka in seed_data['knowledge_areas']
    )
    print(f"Domains: {total_domains}")

    if not args.skip_questions:
        print(f"Sample Questions: {len(seed_data.get('sample_questions', []))}")
    else:
        print("Sample Questions: SKIPPED")

    print("="*70)

    # Confirm
    confirm = input("\nProceed with import? [y/N]: ").strip().lower()
    if confirm not in ('y', 'yes'):
        print("Aborted.")
        sys.exit(0)

    try:
        # Create course
        course = create_course(session, seed_data['course'])

        # Create knowledge areas and domains
        ka_map = create_knowledge_areas(
            session,
            course.course_id,
            seed_data['knowledge_areas']
        )

        # Create sample questions
        questions_created = 0
        if not args.skip_questions and 'sample_questions' in seed_data:
            questions_created = create_questions(
                session,
                course.course_id,
                ka_map,
                seed_data['sample_questions']
            )

        # Commit transaction
        session.commit()

        # Summary
        print("\n" + "="*70)
        print("✅ Import Successful!")
        print("="*70)
        print(f"Course ID: {course.course_id}")
        print(f"Course Code: {course.course_code}")
        print(f"Status: {course.status}")
        print(f"\nKnowledge Areas: {len(ka_map)}")
        print(f"Domains: {total_domains}")
        print(f"Sample Questions: {questions_created}")
        print("\n" + "="*70)

        print("\nNext steps:")
        print("1. Add more questions via bulk import:")
        print(f"   POST /v1/admin/courses/{course.course_id}/questions/bulk")
        print("\n2. Add content chunks for RAG-based learning")
        print("\n3. Publish course when ready:")
        print(f"   POST /v1/admin/courses/{course.course_id}/publish")

        sys.exit(0)

    except Exception as e:
        session.rollback()
        print(f"\n❌ Error during import: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == '__main__':
    main()
