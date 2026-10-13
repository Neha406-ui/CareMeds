"""Create the first CareMeds administrator from a trusted local shell."""

import argparse
from getpass import getpass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.base import SessionLocal
from app.models.user import User, UserRole
from app.services.audit import record_audit


def bootstrap_first_admin(
    db: Session,
    username: str,
    password: str,
    full_name: str | None = None,
) -> User:
    username = username.strip()
    if not username or len(username) > 150:
        raise ValueError("Username must be between 1 and 150 characters")
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters")
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 UTF-8 bytes")

    dialect = db.bind.dialect.name if db.bind is not None else None
    if dialect == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(731904217)"))
    elif dialect == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    else:
        raise RuntimeError(f"Admin bootstrap is unsupported for database dialect {dialect!r}")

    existing_admin = db.query(User.id).filter(User.role == UserRole.ADMIN).first()
    if existing_admin is not None:
        db.rollback()
        raise ValueError("An administrator already exists; use the authenticated Admin account workflow")
    if db.query(User.id).filter(User.username == username).first():
        db.rollback()
        raise ValueError("That username is already registered")

    admin = User(
        username=username,
        password_hash=get_password_hash(password),
        role=UserRole.ADMIN,
        full_name=full_name.strip() if full_name and full_name.strip() else None,
        is_active=True,
    )
    db.add(admin)
    db.flush()
    record_audit(db, admin.id, "first_admin_bootstrapped", "user", admin.id)
    db.commit()
    db.refresh(admin)
    return admin


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the first CareMeds administrator; credentials are entered interactively."
    )
    parser.add_argument("--username", required=True, help="Username for the first administrator")
    parser.add_argument("--full-name", help="Optional administrator display name")
    arguments = parser.parse_args()

    if SessionLocal is None:
        parser.error("Database not configured. Set DATABASE_URL in backend/.env and run migrations first.")

    password = getpass("New administrator password (12-72 characters): ")
    confirmation = getpass("Confirm administrator password: ")
    if password != confirmation:
        parser.error("Passwords do not match.")

    with SessionLocal() as db:
        try:
            admin = bootstrap_first_admin(db, arguments.username, password, arguments.full_name)
        except (RuntimeError, ValueError) as exc:
            parser.error(str(exc))
    print(f"Created first administrator account {admin.username!r} (id: {admin.id}).")


if __name__ == "__main__":
    main()
