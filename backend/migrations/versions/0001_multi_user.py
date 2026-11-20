"""Add the SaaS control plane without touching legacy datasets/files.

Revision ID: 0001_multi_user
"""
from alembic import op
import sqlalchemy as sa
revision = "0001_multi_user"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users", sa.Column("id", sa.String(36), primary_key=True), sa.Column("email", sa.String(320), nullable=False, unique=True), sa.Column(
        "password_hash", sa.Text(), nullable=False), sa.Column("created_at", sa.BigInteger(), nullable=False), sa.Column("active", sa.Boolean(), nullable=False))
    op.create_table("user_sessions", sa.Column("token_hash", sa.String(64), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE")), sa.Column("csrf_token", sa.String(
        64), nullable=False), sa.Column("created_at", sa.BigInteger(), nullable=False), sa.Column("expires_at", sa.BigInteger(), nullable=False), sa.Column("last_seen_at", sa.BigInteger(), nullable=False))
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])
    op.create_table("dataset_metadata", sa.Column("id", sa.String(36), primary_key=True), sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT")), sa.Column(
        "metadata_json", sa.Text(), nullable=False), sa.Column("stored_extension", sa.String(4), nullable=False), sa.Column("created_at", sa.String(40), nullable=False))
    op.create_index("ix_dataset_metadata_owner_id", "dataset_metadata", ["owner_id"])
    op.create_table("rate_counters", sa.Column("key", sa.String(200), primary_key=True), sa.Column(
        "window", sa.BigInteger(), nullable=False), sa.Column("hits", sa.Integer(), nullable=False))
    op.create_table("ai_usage", sa.Column("id", sa.String(36), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False), sa.Column("dataset_id", sa.String(36), nullable=False), sa.Column("model", sa.String(
        100), nullable=False), sa.Column("input_tokens", sa.Integer(), nullable=False), sa.Column("output_tokens", sa.Integer(), nullable=False), sa.Column("outcome", sa.String(30), nullable=False), sa.Column("created_at", sa.BigInteger(), nullable=False))
    op.create_index("ix_ai_usage_user_id", "ai_usage", ["user_id"])
    op.create_index("ix_ai_usage_created_at", "ai_usage", ["created_at"])
    op.create_table("ownership_decisions", sa.Column("id", sa.String(36), primary_key=True), sa.Column("dataset_id", sa.String(36), sa.ForeignKey("dataset_metadata.id", ondelete="CASCADE"), nullable=False), sa.Column(
        "owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False), sa.Column("administrator", sa.String(200), nullable=False), sa.Column("created_at", sa.BigInteger(), nullable=False))


def downgrade():
    # Explicit operator action only; never erase accounts or imported metadata silently.
    connection = op.get_bind()
    for table in ("users", "dataset_metadata", "ai_usage"):
        if connection.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar():
            raise RuntimeError(
                "Refusing a destructive downgrade of a populated SaaS database. Back up and migrate data explicitly.")
    for table in ("ownership_decisions", "ai_usage", "rate_counters", "dataset_metadata", "user_sessions", "users"):
        op.drop_table(table)
