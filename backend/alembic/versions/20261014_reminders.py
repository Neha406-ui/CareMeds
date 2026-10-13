"""Persist in-app reminders and overdue escalation events."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261014_reminders"
down_revision: Union[str, None] = "20261013_dose"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("dose_occurrence_id", sa.UUID(), nullable=False),
        sa.Column("recipient_id", sa.UUID(), nullable=False),
        sa.Column("notification_type", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["dose_occurrence_id"], ["dose_occurrences.id"]),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dose_occurrence_id",
            "recipient_id",
            "notification_type",
            name="uq_notification_dose_recipient_type",
        ),
        sa.CheckConstraint(
            "notification_type IN ('dose_upcoming', 'dose_due', 'dose_overdue')",
            name="ck_notification_type",
        ),
    )
    op.create_table(
        "escalation_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("dose_occurrence_id", sa.UUID(), nullable=False),
        sa.Column("recipient_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by", sa.UUID(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["dose_occurrence_id"], ["dose_occurrences.id"]),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dose_occurrence_id",
            "recipient_id",
            name="uq_escalation_dose_recipient",
        ),
        sa.CheckConstraint("status IN ('open', 'resolved')", name="ck_escalation_status"),
    )
    op.create_index(
        "ix_notifications_recipient_created",
        "notifications",
        ["recipient_id", "created_at"],
    )
    op.execute('ALTER TABLE "notifications" ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "escalation_events" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    op.execute('ALTER TABLE "escalation_events" DISABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "notifications" DISABLE ROW LEVEL SECURITY')
    op.drop_index("ix_notifications_recipient_created", table_name="notifications")
    op.drop_table("escalation_events")
    op.drop_table("notifications")
