"""Add lifecycle fields without removing existing data."""

from alembic import op
import sqlalchemy as sa

revision = "c301_personal_lifecycle"
down_revision = "ba0170a97753"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("jobs", sa.Column("archived_at", sa.DateTime(), nullable=True))
    op.create_index("ix_jobs_archived_at", "jobs", ["archived_at"])
    op.add_column("jobs", sa.Column("provenance", sa.JSON(), server_default="[]", nullable=False))
    op.add_column(
        "job_sources", sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False)
    )


def downgrade():
    raise RuntimeError(
        "Restore a verified backup in another database instead of discarding lifecycle data."
    )
