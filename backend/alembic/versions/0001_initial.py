"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-15

myWeb은 ddl-auto=update로 운영해 스키마 이력이 없었다. 여기서는 처음부터 마이그레이션으로 관리하고,
CI의 `alembic check`가 모델과 마이그레이션의 어긋남을 잡는다.

벡터 인덱스(HNSW 등)는 두지 않는다. 기록이 수백~수천 건이면 순차 스캔이 충분히 빠르고 결과가 정확하다.
근사 인덱스는 결과가 달라질 수 있어서, 데이터가 커질 때 측정하고 추가한다.
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

EMBEDDING_DIM = 384


def _created_at() -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "grinders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        _created_at(),
    )

    op.create_table(
        "beans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("roaster", sa.String(200), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("variety", sa.String(100), nullable=True),
        sa.Column("processing", sa.String(100), nullable=True),
        sa.Column("roast_level", sa.String(100), nullable=True),
        sa.Column("bag_flavor_notes", postgresql.JSONB(), server_default="[]", nullable=False),
        _created_at(),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "brews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bean_id", sa.Integer(), sa.ForeignKey("beans.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("grinder_id", sa.Integer(), sa.ForeignKey("grinders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("brewed_on", sa.Date(), server_default=sa.func.current_date(), nullable=False),
        sa.Column("grind_clicks", sa.Integer(), nullable=True),
        sa.Column("water_temp_c", sa.Integer(), nullable=True),
        sa.Column("dose_g", sa.Float(), nullable=True),
        sa.Column("water_g", sa.Float(), nullable=True),
        sa.Column("brew_time_s", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("flavor_tags", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        _created_at(),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_brews_rating"),
        sa.CheckConstraint("grind_clicks IS NULL OR grind_clicks >= 0", name="ck_brews_clicks"),
    )
    op.create_index("ix_brews_bean_id", "brews", ["bean_id"])

    op.create_table(
        "grind_measurements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("brew_id", sa.Integer(), sa.ForeignKey("brews.id", ondelete="SET NULL"), nullable=True),
        sa.Column("grinder_id", sa.Integer(), sa.ForeignKey("grinders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False),
        sa.Column("mm_per_px", sa.Float(), nullable=False),
        sa.Column("particle_count", sa.Integer(), nullable=False),
        sa.Column("d10_mm", sa.Float(), nullable=False),
        sa.Column("d50_mm", sa.Float(), nullable=False),
        sa.Column("d90_mm", sa.Float(), nullable=False),
        sa.Column("count_d50_mm", sa.Float(), nullable=False),
        sa.Column("min_detectable_mm", sa.Float(), nullable=False),
        sa.Column("clump_suspects", sa.Integer(), nullable=False),
        sa.Column("histogram", postgresql.JSONB(), nullable=False),
        sa.Column("warnings", postgresql.JSONB(), server_default="[]", nullable=False),
        _created_at(),
    )
    op.create_index("ix_grind_measurements_brew_id", "grind_measurements", ["brew_id"])
    op.create_index("ix_grind_measurements_grinder_id", "grind_measurements", ["grinder_id"])

    op.create_table(
        "catalog_beans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_name", sa.String(100), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=False, unique=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("price", sa.String(50), nullable=True),
        sa.Column("available", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("normalized", postgresql.JSONB(), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("processing", sa.String(100), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_catalog_beans_status", "catalog_beans", ["status"])

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("ref_id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("kind", "ref_id", "model_id", name="uq_documents_ref_model"),
    )

    op.create_table(
        "llm_usage",
        sa.Column("model", sa.String(200), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False),
    )

    op.create_table(
        "recommendation_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("embedding_model", sa.String(200), nullable=False),
        sa.Column("llm_model", sa.String(200), nullable=True),
        sa.Column("profile_brew_ids", postgresql.JSONB(), nullable=False),
        sa.Column("items", postgresql.JSONB(), nullable=False),
        _created_at(),
    )


def downgrade() -> None:
    for table in (
        "recommendation_snapshots",
        "llm_usage",
        "documents",
        "catalog_beans",
        "grind_measurements",
        "brews",
        "beans",
        "grinders",
    ):
        op.drop_table(table)
