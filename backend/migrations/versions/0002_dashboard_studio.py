"""Add owner-scoped dashboards and persistent analytical widgets.

Revision ID: 0002_dashboard_studio
Revises: 0001_multi_user
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_dashboard_studio"
down_revision = "0001_multi_user"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dashboards",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.String(500)),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("revision >= 1", name="ck_dashboards_revision_positive"),
    )
    op.create_index("ix_dashboards_owner_id", "dashboards", ["owner_id"])
    op.create_index("ix_dashboards_owner_updated", "dashboards", ["owner_id", "updated_at"])

    op.create_table(
        "dashboard_widgets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dashboard_id", sa.String(36), sa.ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dataset_id", sa.String(36), sa.ForeignKey("dataset_metadata.id", ondelete="SET NULL")),
        sa.Column("dataset_id_snapshot", sa.String(36), nullable=False),
        sa.Column("dataset_name_snapshot", sa.String(120), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("query_version", sa.Integer(), nullable=False),
        sa.Column("query_spec_json", sa.Text(), nullable=False),
        sa.Column("visualization_json", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("width_columns", sa.Integer(), nullable=False),
        sa.Column("height_rows", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("query_version >= 1", name="ck_dashboard_widgets_query_version_positive"),
        sa.CheckConstraint("position >= 0 AND position < 12", name="ck_dashboard_widgets_position"),
        sa.CheckConstraint("width_columns >= 1 AND width_columns <= 12", name="ck_dashboard_widgets_width"),
        sa.CheckConstraint("height_rows >= 2 AND height_rows <= 12", name="ck_dashboard_widgets_height"),
    )
    op.create_index("ix_dashboard_widgets_dashboard_id", "dashboard_widgets", ["dashboard_id"])
    op.create_index("ix_dashboard_widgets_dataset_id", "dashboard_widgets", ["dataset_id"])
    op.create_index("ix_dashboard_widgets_dashboard_position", "dashboard_widgets", ["dashboard_id", "position"])


def downgrade():
    connection = op.get_bind()
    for table in ("dashboard_widgets", "dashboards"):
        if connection.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar():
            raise RuntimeError(
                "Refusing a destructive Dashboard Studio downgrade while saved dashboards exist."
            )
    op.drop_table("dashboard_widgets")
    op.drop_table("dashboards")
