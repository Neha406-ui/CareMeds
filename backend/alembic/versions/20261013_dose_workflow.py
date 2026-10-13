"""Persist explicit medication schedules and dose administration records."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261013_dose"
down_revision: Union[str, None] = "9f48c2a7d1e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "prescriptions",
        sa.Column("scheduled_times", sa.JSON(), server_default="[]", nullable=False),
    )
    op.add_column(
        "prescriptions",
        sa.Column("timezone", sa.String(length=64), server_default="UTC", nullable=False),
    )
    op.add_column(
        "prescriptions",
        sa.Column("schedule_revision", sa.Integer(), server_default="1", nullable=False),
    )
    op.create_table(
        "dose_occurrences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("prescription_id", sa.UUID(), nullable=False),
        sa.Column("schedule_revision", sa.Integer(), nullable=False),
        sa.Column("resident_id", sa.UUID(), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("scheduled_local_time", sa.String(length=5), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("medicine_name", sa.String(length=255), nullable=False),
        sa.Column("dosage", sa.String(length=100), nullable=False),
        sa.Column("route", sa.String(length=100), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="scheduled", nullable=False),
        sa.Column("actual_at", sa.DateTime(), nullable=True),
        sa.Column("recorded_by", sa.UUID(), nullable=True),
        sa.Column("outcome_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("acknowledged_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["prescription_id"], ["prescriptions.id"]),
        sa.ForeignKeyConstraint(["resident_id"], ["residents.id"]),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["acknowledged_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "prescription_id",
            "schedule_revision",
            "scheduled_for",
            name="uq_dose_prescription_revision_time",
        ),
        sa.CheckConstraint(
            "status IN ('scheduled', 'administered', 'refused', 'withheld', "
            "'not_administered', 'unable_to_confirm', 'cancelled')",
            name="ck_dose_occurrence_status",
        ),
    )
    op.create_index(
        "ix_dose_occurrences_resident_schedule",
        "dose_occurrences",
        ["resident_id", "scheduled_for"],
    )
    op.create_table(
        "dose_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("dose_occurrence_id", sa.UUID(), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("previous_status", sa.String(length=32), nullable=True),
        sa.Column("new_status", sa.String(length=32), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dose_occurrence_id"], ["dose_occurrences.id"]),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute('ALTER TABLE "dose_occurrences" ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "dose_events" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    op.execute('ALTER TABLE "dose_events" DISABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "dose_occurrences" DISABLE ROW LEVEL SECURITY')
    op.drop_table("dose_events")
    op.drop_index("ix_dose_occurrences_resident_schedule", table_name="dose_occurrences")
    op.drop_table("dose_occurrences")
    op.drop_column("prescriptions", "timezone")
    op.drop_column("prescriptions", "schedule_revision")
    op.drop_column("prescriptions", "scheduled_times")
