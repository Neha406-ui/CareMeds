"""Add stock tracking, family contact requests, handovers, and audit logs."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261015_operations"
down_revision: Union[str, None] = "20261014_reminders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "medicines",
        sa.Column("reorder_level", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_table(
        "inventory_batches",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("medicine_id", sa.UUID(), nullable=False),
        sa.Column("lot_code", sa.String(length=120), nullable=False),
        sa.Column("expires_on", sa.Date(), nullable=False),
        sa.Column("quantity_remaining", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["medicine_id"], ["medicines.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("medicine_id", "lot_code", name="uq_inventory_medicine_lot"),
        sa.CheckConstraint("quantity_remaining >= 0", name="ck_inventory_nonnegative"),
    )
    op.create_table(
        "inventory_transactions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("batch_id", sa.UUID(), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("transaction_type", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("quantity_after", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["batch_id"], ["inventory_batches.id"]),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("transaction_type IN ('stock_in', 'stock_out')", name="ck_inventory_transaction_type"),
        sa.CheckConstraint("quantity > 0 AND quantity_after >= 0", name="ck_inventory_transaction_quantities"),
    )
    op.create_table(
        "family_contact_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("resident_id", sa.UUID(), nullable=False),
        sa.Column("family_member_id", sa.UUID(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("responded_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["resident_id"], ["residents.id"]),
        sa.ForeignKeyConstraint(["family_member_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["responded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("status IN ('pending', 'received', 'resolved')", name="ck_family_contact_status"),
    )
    op.create_table(
        "shift_handovers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("resident_id", sa.UUID(), nullable=False),
        sa.Column("outgoing_caretaker_id", sa.UUID(), nullable=False),
        sa.Column("incoming_caretaker_id", sa.UUID(), nullable=False),
        sa.Column("shift_started_at", sa.DateTime(), nullable=False),
        sa.Column("shift_ended_at", sa.DateTime(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("acknowledged_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["resident_id"], ["residents.id"]),
        sa.ForeignKeyConstraint(["outgoing_caretaker_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["incoming_caretaker_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["acknowledged_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("shift_ended_at > shift_started_at", name="ck_handover_shift_interval"),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for table in ("inventory_batches", "inventory_transactions", "family_contact_requests", "shift_handovers", "audit_logs"):
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    for table in ("audit_logs", "shift_handovers", "family_contact_requests", "inventory_transactions", "inventory_batches"):
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
    op.drop_table("audit_logs")
    op.drop_table("shift_handovers")
    op.drop_table("family_contact_requests")
    op.drop_table("inventory_transactions")
    op.drop_table("inventory_batches")
    op.drop_column("medicines", "reorder_level")
