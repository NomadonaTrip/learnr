#!/usr/bin/env python
"""
Validate Bulk Import JSON

Validates a bulk question import JSON file before sending to the API.
This helps catch errors early and provides detailed feedback.

Usage:
    python scripts/validate_bulk_import.py questions.json
    python scripts/validate_bulk_import.py questions.json --course-id <uuid>
"""
import sys
import json
import argparse
from typing import List, Dict, Any
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import ValidationError
from app.schemas.admin import BulkQuestionImportRequest


def load_json_file(file_path: str) -> dict:
    """Load and parse JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: File not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON format")
        print(f"   Line {e.lineno}, Column {e.colno}: {e.msg}")
        sys.exit(1)


def validate_structure(data: dict) -> tuple[bool, List[str]]:
    """Validate JSON structure using Pydantic schemas."""
    errors = []

    try:
        # Validate using Pydantic schema
        BulkQuestionImportRequest(**data)
        return True, []

    except ValidationError as e:
        for error in e.errors():
            location = " -> ".join(str(loc) for loc in error['loc'])
            message = error['msg']
            errors.append(f"  {location}: {message}")
        return False, errors


def analyze_questions(data: dict) -> Dict[str, Any]:
    """Analyze question distribution and statistics."""
    questions = data.get('questions', [])

    stats = {
        'total_questions': len(questions),
        'by_ka': {},
        'by_type': {'multiple_choice': 0, 'true_false': 0},
        'by_source': {'vendor': 0, 'generated': 0, 'custom': 0},
        'by_difficulty': {
            'easy (0.0-0.3)': 0,
            'medium (0.4-0.6)': 0,
            'hard (0.7-1.0)': 0
        },
        'with_domain': 0,
        'with_explanations': 0
    }

    for q in questions:
        # By KA
        ka_code = q.get('ka_code', 'unknown')
        stats['by_ka'][ka_code] = stats['by_ka'].get(ka_code, 0) + 1

        # By type
        qtype = q.get('question_type', 'unknown')
        if qtype in stats['by_type']:
            stats['by_type'][qtype] += 1

        # By source
        source = q.get('source', 'unknown')
        if source in stats['by_source']:
            stats['by_source'][source] += 1

        # By difficulty
        difficulty = q.get('difficulty', 0.5)
        if difficulty <= 0.3:
            stats['by_difficulty']['easy (0.0-0.3)'] += 1
        elif difficulty <= 0.6:
            stats['by_difficulty']['medium (0.4-0.6)'] += 1
        else:
            stats['by_difficulty']['hard (0.7-1.0)'] += 1

        # Domain
        if q.get('domain_code'):
            stats['with_domain'] += 1

        # Explanations
        answer_choices = q.get('answer_choices', [])
        if any(choice.get('explanation') for choice in answer_choices):
            stats['with_explanations'] += 1

    return stats


def print_stats(stats: Dict[str, Any]):
    """Print statistics in a formatted way."""
    print("\n" + "="*60)
    print("Question Statistics")
    print("="*60)

    print(f"\nTotal Questions: {stats['total_questions']}")

    print("\nBy Knowledge Area:")
    for ka, count in sorted(stats['by_ka'].items()):
        percentage = (count / stats['total_questions']) * 100
        print(f"  {ka}: {count} ({percentage:.1f}%)")

    print("\nBy Question Type:")
    for qtype, count in stats['by_type'].items():
        percentage = (count / stats['total_questions']) * 100
        print(f"  {qtype}: {count} ({percentage:.1f}%)")

    print("\nBy Source:")
    for source, count in stats['by_source'].items():
        percentage = (count / stats['total_questions']) * 100
        print(f"  {source}: {count} ({percentage:.1f}%)")

    print("\nBy Difficulty:")
    for difficulty, count in stats['by_difficulty'].items():
        percentage = (count / stats['total_questions']) * 100
        print(f"  {difficulty}: {count} ({percentage:.1f}%)")

    print(f"\nWith Domains: {stats['with_domain']}")
    print(f"With Explanations: {stats['with_explanations']}")
    print("="*60)


def validate_ka_codes(data: dict, course_id: str = None) -> tuple[bool, List[str]]:
    """Validate knowledge area codes against course (if course_id provided)."""
    if not course_id:
        return True, []

    # This would require database connection to validate KA codes
    # For now, just return True
    # In production, you'd query the database:
    # valid_ka_codes = db.query(KnowledgeArea.ka_code).filter(
    #     KnowledgeArea.course_id == course_id
    # ).all()

    return True, []


def main():
    """Main validation script."""
    parser = argparse.ArgumentParser(
        description='Validate bulk question import JSON file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate JSON structure only
  python scripts/validate_bulk_import.py questions.json

  # Validate with course context
  python scripts/validate_bulk_import.py questions.json --course-id abc123...

  # Show statistics without validation
  python scripts/validate_bulk_import.py questions.json --stats-only
        """
    )

    parser.add_argument(
        'file',
        help='Path to JSON file to validate'
    )
    parser.add_argument(
        '--course-id',
        help='Course ID to validate KA codes against (requires database)',
        default=None
    )
    parser.add_argument(
        '--stats-only',
        action='store_true',
        help='Show statistics without validation'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed validation messages'
    )

    args = parser.parse_args()

    # Load JSON file
    print(f"Loading {args.file}...")
    data = load_json_file(args.file)

    # Show statistics
    stats = analyze_questions(data)
    print_stats(stats)

    if args.stats_only:
        sys.exit(0)

    # Validate structure
    print("\n" + "="*60)
    print("Validation Results")
    print("="*60)

    is_valid, errors = validate_structure(data)

    if is_valid:
        print("\n✅ JSON structure is valid!")
        print(f"\n✓ All {stats['total_questions']} questions passed schema validation")
        print("✓ Ready to import via API")

        # Show import command
        if args.course_id:
            print(f"\nImport command:")
            print(f"  POST /v1/admin/courses/{args.course_id}/questions/bulk")
        else:
            print(f"\nImport command:")
            print(f"  POST /v1/admin/courses/{{course_id}}/questions/bulk")

        sys.exit(0)
    else:
        print("\n❌ Validation failed with the following errors:\n")
        for error in errors:
            print(error)

        print(f"\n{len(errors)} validation error(s) found.")
        print("Please fix the errors and try again.")
        sys.exit(1)


if __name__ == '__main__':
    main()
