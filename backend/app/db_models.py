"""Relational control plane; analytical source files remain UUID addressed."""
from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class UserSession(Base):
    __tablename__ = "user_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True)
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expires_at: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    last_seen_at: Mapped[int] = mapped_column(BigInteger, nullable=False)


class DatasetRecord(Base):
    __tablename__ = "dataset_metadata"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # NULL is a quarantined legacy import, never visible to an account.
    owner_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False)
    stored_extension: Mapped[str] = mapped_column(String(4), nullable=False)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)


class RateCounter(Base):
    __tablename__ = "rate_counters"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    window: Mapped[int] = mapped_column(BigInteger, nullable=False)
    hits: Mapped[int] = mapped_column(Integer, nullable=False)


class AIUsage(Base):
    __tablename__ = "ai_usage"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    dataset_id: Mapped[str] = mapped_column(String(36), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)


class OwnershipDecision(Base):
    __tablename__ = "ownership_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey(
        "dataset_metadata.id", ondelete="CASCADE"), nullable=False)
    owner_id: Mapped[str] = mapped_column(ForeignKey(
        "users.id", ondelete="RESTRICT"), nullable=False)
    administrator: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)


class Dashboard(Base):
    __tablename__ = "dashboards"
    __table_args__ = (
        CheckConstraint("revision >= 1", name="ck_dashboards_revision_positive"),
        Index("ix_dashboards_owner_updated", "owner_id", "updated_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)


class DashboardWidget(Base):
    __tablename__ = "dashboard_widgets"
    __table_args__ = (
        CheckConstraint("query_version >= 1", name="ck_dashboard_widgets_query_version_positive"),
        CheckConstraint("position >= 0 AND position < 12", name="ck_dashboard_widgets_position"),
        CheckConstraint("width_columns >= 1 AND width_columns <= 12", name="ck_dashboard_widgets_width"),
        CheckConstraint("height_rows >= 2 AND height_rows <= 12", name="ck_dashboard_widgets_height"),
        Index("ix_dashboard_widgets_dashboard_position", "dashboard_id", "position"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dashboard_id: Mapped[str] = mapped_column(
        ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_id: Mapped[str | None] = mapped_column(
        ForeignKey("dataset_metadata.id", ondelete="SET NULL"), index=True)
    dataset_id_snapshot: Mapped[str] = mapped_column(String(36), nullable=False)
    dataset_name_snapshot: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    query_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    query_spec_json: Mapped[str] = mapped_column(Text, nullable=False)
    visualization_json: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    width_columns: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    height_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
