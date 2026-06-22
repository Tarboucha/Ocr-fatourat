"""add ocr_jobs, boxes.ocr_job_id, pages.ocr_status

Revision ID: 0002_add_ocr_jobs
Revises: 0001_initial
Create Date: 2026-06-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_add_ocr_jobs"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ocr_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("page_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("pipeline", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("x", sa.Float(), nullable=True),
        sa.Column("y", sa.Float(), nullable=True),
        sa.Column("w", sa.Float(), nullable=True),
        sa.Column("h", sa.Float(), nullable=True),
        sa.Column("box_id", sa.Integer(), nullable=True),
        sa.Column("result_text", sa.String(), nullable=True),
        sa.Column("result_confidence", sa.Float(), nullable=True),
        sa.Column("box_count", sa.Integer(), nullable=True),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["page_id"], ["pages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ocr_jobs_page_id", "ocr_jobs", ["page_id"])

    op.add_column("boxes", sa.Column("ocr_job_id", sa.Integer(), nullable=True))
    op.create_index("ix_boxes_ocr_job_id", "boxes", ["ocr_job_id"])
    op.create_foreign_key(
        "fk_boxes_ocr_job_id",
        "boxes",
        "ocr_jobs",
        ["ocr_job_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "pages",
        sa.Column("ocr_status", sa.String(length=16), nullable=False, server_default="idle"),
    )


def downgrade() -> None:
    op.drop_column("pages", "ocr_status")
    op.drop_constraint("fk_boxes_ocr_job_id", "boxes", type_="foreignkey")
    op.drop_index("ix_boxes_ocr_job_id", table_name="boxes")
    op.drop_column("boxes", "ocr_job_id")
    op.drop_index("ix_ocr_jobs_page_id", table_name="ocr_jobs")
    op.drop_table("ocr_jobs")
