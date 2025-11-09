#!/usr/bin/env python3
"""
Automated script to update DateTime columns to DateTime(timezone=True) in model files.

This script updates all remaining model files that haven't been manually updated yet.

Usage: python scripts/update_datetime_models.py
"""

import re
from pathlib import Path


def update_datetime_column(content: str) -> str:
    """
    Replace all instances of Column(DateTime with Column(DateTime(timezone=True).

    Handles various formatting patterns:
    - Column(DateTime, ...)
    - Column(DateTime,...)
    - Column( DateTime, ...)
    """
    # Pattern to match DateTime columns without timezone=True
    pattern = r'Column\(\s*DateTime(?!\(timezone=True\))'

    # Replace with DateTime(timezone=True)
    updated = re.sub(pattern, 'Column(DateTime(timezone=True)', content)

    return updated


def update_model_file(file_path: Path) -> tuple[bool, int]:
    """
    Update a single model file.

    Returns:
        (changed, count): Whether file was modified and count of replacements
    """
    content = file_path.read_text(encoding='utf-8')
    original_content = content

    # Update DateTime columns
    updated_content = update_datetime_column(content)

    # Count replacements
    count = updated_content.count('DateTime(timezone=True)') - original_content.count('DateTime(timezone=True)')

    if updated_content != original_content:
        file_path.write_text(updated_content, encoding='utf-8')
        return True, count

    return False, 0


def main():
    """Update all model files."""
    models_dir = Path(__file__).parent.parent / 'app' / 'models'

    files_to_update = [
        'question.py',
        'learning.py',
        'spaced_repetition.py',  # CRITICAL!
        'financial.py',
        'security.py',
        'content.py',
    ]

    print("=" * 60)
    print("Updating SQLAlchemy DateTime columns to DateTime(timezone=True)")
    print("=" * 60)
    print()

    total_replacements = 0
    files_updated = 0

    for filename in files_to_update:
        file_path = models_dir / filename

        if not file_path.exists():
            print(f"⚠️  {filename}: File not found")
            continue

        changed, count = update_model_file(file_path)

        if changed:
            print(f"✓ {filename}: Updated {count} DateTime columns")
            files_updated += 1
            total_replacements += count
        else:
            print(f"• {filename}: No changes needed (already updated)")

    print()
    print("=" * 60)
    print(f"Summary: Updated {files_updated} files, {total_replacements} DateTime columns")
    print("=" * 60)

    # Verify by counting total DateTime(timezone=True) across all files
    print()
    print("Verification:")

    all_model_files = [
        'user.py', 'course.py', 'question.py', 'learning.py',
        'spaced_repetition.py', 'financial.py', 'security.py', 'content.py'
    ]

    total_tz_aware = 0
    for filename in all_model_files:
        file_path = models_dir / filename
        if file_path.exists():
            content = file_path.read_text()
            count = content.count('DateTime(timezone=True)')
            total_tz_aware += count
            print(f"  {filename}: {count} timezone-aware DateTime columns")

    print()
    print(f"Total timezone-aware DateTime columns: {total_tz_aware}")
    print(f"Expected total: 70")

    if total_tz_aware == 70:
        print("✓ All 70 columns successfully updated!")
    else:
        print(f"⚠️  Expected 70 but found {total_tz_aware}")


if __name__ == '__main__':
    main()
