"""RBAC, session revocation, consent defaults, and database RLS.

Revision ID: 9f48c2a7d1e3
Revises: 26c19111897e
Create Date: 2026-10-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9f48c2a7d1e3"
down_revision: Union[str, None] = "26c19111897e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


RLS_TABLES = (
    "users",
    "residents",
    "medicines",
    "prescriptions",
    "prescription_history",
    "caretaker_assignments",
    "family_links",
)


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
    )
    # Existing links had an implicit-consent default; require fresh consent.
    op.execute(
        "UPDATE family_links SET consent_granted = false "
        "WHERE consent_granted IS DISTINCT FROM false"
    )
    op.alter_column(
        "family_links",
        "consent_granted",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        nullable=False,
    )
    op.add_column(
        "family_links",
        sa.Column("consent_granted_by", sa.UUID(), nullable=True),
    )
    op.add_column(
        "family_links",
        sa.Column("can_view_profile", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "family_links",
        sa.Column("can_view_prescriptions", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_foreign_key(
        "fk_family_links_consent_granted_by_users",
        "family_links",
        "users",
        ["consent_granted_by"],
        ["id"],
    )
    op.add_column(
        "family_links",
        sa.Column("requested_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "doctor_assignments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("doctor_id", sa.UUID(), nullable=False),
        sa.Column("resident_id", sa.UUID(), nullable=False),
        sa.Column("assigned_by", sa.UUID(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("assigned_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("unassigned_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["doctor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["resident_id"], ["residents.id"]),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doctor_id", "resident_id", name="uq_doctor_resident"),
    )
    for table in RLS_TABLES + ("doctor_assignments",):
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    for table in reversed(RLS_TABLES + ("doctor_assignments",)):
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
    op.drop_table("doctor_assignments")
    op.alter_column(
        "family_links",
        "consent_granted",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        nullable=True,
    )
    op.drop_column("family_links", "requested_at")
    op.drop_constraint("fk_family_links_consent_granted_by_users", "family_links", type_="foreignkey")
    op.drop_column("family_links", "can_view_prescriptions")
    op.drop_column("family_links", "can_view_profile")
    op.drop_column("family_links", "consent_granted_by")
    op.drop_column("users", "token_version")
