#!/usr/bin/env python
"""
Create Admin User Script

Creates a new admin or super_admin user in the LearnR platform.
Useful for bootstrapping the system or adding new administrators.

Usage:
    python scripts/create_admin_user.py --email admin@example.com --password SecurePass123 --role admin
    python scripts/create_admin_user.py --email super@example.com --password SuperPass123 --role super_admin

    # Interactive mode (prompts for password)
    python scripts/create_admin_user.py --email admin@example.com --role admin

Environment:
    DATABASE_URL: PostgreSQL connection string (required)
    ENCRYPTION_KEY: Fernet encryption key for PII (required)
"""
import sys
import os
import argparse
from getpass import getpass
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.security import SecurityLog
from app.utils.security import get_password_hash
from app.core.config import settings


def validate_email(email: str) -> bool:
    """Basic email validation."""
    return '@' in email and '.' in email.split('@')[1]


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password strength.

    Requirements:
    - At least 8 characters
    - Contains uppercase and lowercase
    - Contains at least one digit
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"

    return True, "Password is valid"


def create_admin_user(
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    role: str,
    db_session
) -> tuple[bool, str]:
    """
    Create an admin user in the database.

    Args:
        email: User email address
        password: Plain text password (will be hashed)
        first_name: User's first name
        last_name: User's last name
        role: 'admin' or 'super_admin'
        db_session: Database session

    Returns:
        Tuple of (success: bool, message: str)
    """
    # Check if user already exists
    # Since email is encrypted, we need to fetch all users and check in Python
    all_users = db_session.query(User).all()
    email_lower = email.lower()
    for existing_user in all_users:
        if existing_user.email.lower() == email_lower:
            return False, f"User with email '{email}' already exists"

    # Validate role
    if role not in ('admin', 'super_admin'):
        return False, f"Invalid role '{role}'. Must be 'admin' or 'super_admin'"

    # Create user
    try:
        user = User(
            email=email,  # Will be encrypted via hybrid property
            password_hash=get_password_hash(password),
            first_name=first_name,  # Will be encrypted
            last_name=last_name,  # Will be encrypted
            role=role,
            is_active=True,
            email_verified=True,  # Admin users are pre-verified
            two_factor_enabled=False
        )

        db_session.add(user)
        db_session.flush()  # Get user_id

        # Log the creation
        log = SecurityLog(
            user_id=user.user_id,
            event_type='admin_user_created',
            event_category='authentication',
            ip_address='127.0.0.1',
            user_agent='Admin Creation Script',
            success=True
        )
        db_session.add(log)

        db_session.commit()

        return True, f"Successfully created {role} user: {email} (ID: {user.user_id})"

    except Exception as e:
        db_session.rollback()
        return False, f"Failed to create user: {str(e)}"


def main():
    """Main script execution."""
    parser = argparse.ArgumentParser(
        description='Create an admin user in the LearnR platform',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create admin with command-line password
  python scripts/create_admin_user.py \\
    --email admin@learnr.com \\
    --password SecurePass123 \\
    --first-name Admin \\
    --last-name User \\
    --role admin

  # Create super_admin with interactive password prompt
  python scripts/create_admin_user.py \\
    --email super@learnr.com \\
    --first-name Super \\
    --last-name Admin \\
    --role super_admin

  # Quick bootstrap (prompts for all info)
  python scripts/create_admin_user.py
        """
    )

    parser.add_argument(
        '--email',
        help='Admin user email address',
        required=False
    )
    parser.add_argument(
        '--password',
        help='Admin user password (if not provided, will prompt securely)',
        required=False
    )
    parser.add_argument(
        '--first-name',
        help='Admin user first name (default: Admin)',
        default='Admin'
    )
    parser.add_argument(
        '--last-name',
        help='Admin user last name (default: User)',
        default='User'
    )
    parser.add_argument(
        '--role',
        choices=['admin', 'super_admin'],
        help='User role (default: admin)',
        default='admin'
    )
    parser.add_argument(
        '--db-url',
        help='Database URL (default: from DATABASE_URL env var)',
        default=None
    )

    args = parser.parse_args()

    # Get email (interactive if not provided)
    email = args.email
    if not email:
        email = input('Enter admin email address: ').strip()

    # Validate email
    if not validate_email(email):
        print(f"❌ Error: Invalid email address '{email}'")
        sys.exit(1)

    # Get password (interactive if not provided)
    password = args.password
    if not password:
        while True:
            password = getpass('Enter password (will not be displayed): ')
            password_confirm = getpass('Confirm password: ')

            if password != password_confirm:
                print("❌ Passwords do not match. Please try again.\n")
                continue

            # Validate password
            is_valid, message = validate_password(password)
            if not is_valid:
                print(f"❌ {message}\n")
                continue

            break
    else:
        # Validate provided password
        is_valid, message = validate_password(password)
        if not is_valid:
            print(f"❌ {message}")
            sys.exit(1)

    # Get database URL
    db_url = args.db_url or settings.DATABASE_URL
    if not db_url:
        print("❌ Error: DATABASE_URL not set. Provide via --db-url or environment variable.")
        sys.exit(1)

    # Check encryption key
    if not settings.ENCRYPTION_KEY:
        print("❌ Error: ENCRYPTION_KEY not set. Required for PII encryption.")
        sys.exit(1)

    # Create database session
    try:
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
    except Exception as e:
        print(f"❌ Error: Failed to connect to database: {e}")
        sys.exit(1)

    # Display summary
    print("\n" + "="*60)
    print("Admin User Creation Summary")
    print("="*60)
    print(f"Email:      {email}")
    print(f"First Name: {args.first_name}")
    print(f"Last Name:  {args.last_name}")
    print(f"Role:       {args.role}")
    print(f"Database:   {db_url.split('@')[1] if '@' in db_url else 'local'}")
    print("="*60)

    # Confirm
    confirm = input("\nProceed with creation? [y/N]: ").strip().lower()
    if confirm not in ('y', 'yes'):
        print("Aborted.")
        sys.exit(0)

    # Create user
    print("\nCreating admin user...")
    success, message = create_admin_user(
        email=email,
        password=password,
        first_name=args.first_name,
        last_name=args.last_name,
        role=args.role,
        db_session=session
    )

    if success:
        print(f"✅ {message}")
        print(f"\nYou can now login with:")
        print(f"  Email:    {email}")
        print(f"  Password: <the password you provided>")
        print(f"  Role:     {args.role}")
        sys.exit(0)
    else:
        print(f"❌ Error: {message}")
        sys.exit(1)


if __name__ == '__main__':
    main()
