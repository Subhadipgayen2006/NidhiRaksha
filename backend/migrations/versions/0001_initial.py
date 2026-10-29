from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None
def upgrade():
    op.create_table("fdr_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_name", sa.String(240), nullable=False),
        sa.Column("institution_id", sa.String(100), nullable=False),
        sa.Column("bank_name", sa.String(200), nullable=False),
        sa.Column("fdr_number", sa.String(160), nullable=False),
        sa.Column("deposit_amount", sa.Numeric(14,2), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("maturity_date", sa.Date(), nullable=False),
        sa.Column("document_path", sa.String(500)),
        sa.Column("document_original_name", sa.String(255)),
        sa.Column("document_mime", sa.String(100)),
        sa.Column("ocr_text", sa.Text()),
        sa.Column("extracted_data", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("record_status", sa.String(40), nullable=False, server_default="active"),
        sa.Column("review_status", sa.String(40), nullable=False, server_default="pending_review"),
        sa.Column("created_by_role", sa.String(40), nullable=False, server_default="institution"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("institution_id", "fdr_number", name="uq_institution_fdr"))
    op.create_index("ix_fdr_records_fdr_number", "fdr_records", ["fdr_number"])
    op.create_table("audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("record_id", sa.Integer(), sa.ForeignKey("fdr_records.id", ondelete="SET NULL")),
        sa.Column("actor_role", sa.String(40), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("lifecycle_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("record_id", sa.Integer(), sa.ForeignKey("fdr_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("reference", sa.String(200)),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_by_role", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("release_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("record_id", sa.Integer(), sa.ForeignKey("fdr_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_type", sa.String(40), nullable=False),
        sa.Column("amount", sa.Numeric(14,2)),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="pending"),
        sa.Column("requested_by_role", sa.String(40), nullable=False),
        sa.Column("officer_note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
def downgrade():
    op.drop_table("release_requests")
    op.drop_table("lifecycle_events")
    op.drop_table("audit_logs")
    op.drop_index("ix_fdr_records_fdr_number", table_name="fdr_records")
    op.drop_table("fdr_records")
