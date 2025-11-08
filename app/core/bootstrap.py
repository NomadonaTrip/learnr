"""
Bootstrap admin user creation process.

Decision #79: Environment variable bootstrap for first admin account.
This runs once on application startup if no super_admin exists.
"""
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


def create_bootstrap_admin(db: Session) -> None:
    """
    Create first super_admin if none exists.
    Runs once on application startup.

    Args:
        db: Database session

    Returns:
        None
    """
    from app.models.user import User
    from app.utils.security import get_password_hash
    from app.core.config import settings

    # Check if any super_admin exists
    existing_super_admin = db.query(User).filter(
        User.role == 'super_admin'
    ).first()

    if existing_super_admin:
        logger.info("Super admin already exists. Skipping bootstrap.")
        return

    # Get bootstrap credentials from environment
    bootstrap_email = settings.BOOTSTRAP_ADMIN_EMAIL
    bootstrap_password = settings.BOOTSTRAP_ADMIN_PASSWORD

    if not bootstrap_email or not bootstrap_password:
        logger.warning(
            "BOOTSTRAP_ADMIN_EMAIL or BOOTSTRAP_ADMIN_PASSWORD not set. "
            "Skipping admin creation."
        )
        return

    # Validate password strength
    if len(bootstrap_password) < 12:
        logger.error("Bootstrap password too weak (min 12 chars). Aborting.")
        raise ValueError("Bootstrap password must be at least 12 characters")

    # Create super_admin user
    super_admin = User(
        email=bootstrap_email,
        password_hash=get_password_hash(bootstrap_password),
        first_name="Super",
        last_name="Admin",
        role="super_admin",
        email_verified=True,
        is_active=True,
        must_change_password=True  # Force password change on first login
    )

    db.add(super_admin)
    db.commit()
    db.refresh(super_admin)

    logger.info(f"✅ Bootstrap super_admin created: {bootstrap_email}")

    # Create security log
    try:
        from app.models.security import SecurityLog
        security_log = SecurityLog(
            user_id=super_admin.user_id,
            event_type="bootstrap_admin_created",
            ip_address="127.0.0.1",
            user_agent="System",
            success=True,
            metadata={"email": bootstrap_email}
        )
        db.add(security_log)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to create security log for bootstrap: {e}")
