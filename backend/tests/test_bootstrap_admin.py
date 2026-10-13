import pytest

from app.bootstrap_admin import bootstrap_first_admin
from app.core.security import verify_password
from app.models.operations import AuditLog
from app.models.user import User, UserRole


def test_bootstrap_creates_an_active_admin_with_a_hashed_password_and_audit_entry(db_session):
    db_session.add(User(
        username="existing-resident",
        password_hash="not-used",
        role=UserRole.RESIDENT,
        is_active=True,
    ))
    db_session.commit()

    admin = bootstrap_first_admin(
        db_session,
        " first-admin ",
        "an-initial-secure-password",
        "First Administrator",
    )

    assert admin.username == "first-admin"
    assert admin.role == UserRole.ADMIN
    assert admin.is_active is True
    assert admin.full_name == "First Administrator"
    assert admin.password_hash != "an-initial-secure-password"
    assert verify_password("an-initial-secure-password", admin.password_hash)
    audit = db_session.query(AuditLog).filter_by(action="first_admin_bootstrapped").one()
    assert audit.actor_id == admin.id


def test_bootstrap_is_one_time_and_rejects_invalid_credentials(db_session):
    bootstrap_first_admin(db_session, "administrator", "a-valid-initial-password")

    with pytest.raises(ValueError, match="administrator already exists"):
        bootstrap_first_admin(db_session, "second-admin", "another-valid-password")

    with pytest.raises(ValueError, match="at least 12"):
        bootstrap_first_admin(db_session, "short-password", "short")

    with pytest.raises(ValueError, match="72 UTF-8 bytes"):
        bootstrap_first_admin(db_session, "long-byte-password", "é" * 37)


def test_bootstrap_rejects_username_collision_even_without_existing_admin(db_session):
    db_session.add(User(
        username="already-used",
        password_hash="not-used",
        role=UserRole.RESIDENT,
        is_active=True,
    ))
    db_session.commit()

    with pytest.raises(ValueError, match="already registered"):
        bootstrap_first_admin(db_session, "already-used", "a-valid-initial-password")
    assert db_session.query(User).filter(User.role == UserRole.ADMIN).count() == 0
