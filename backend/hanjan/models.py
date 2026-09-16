from datetime import date, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hanjan.db import Base

# 마이그레이션의 vector 차원과 반드시 같아야 한다.
# 임베딩 모델을 차원이 다른 것으로 바꾸면 새 마이그레이션 + 전체 재임베딩.
EMBEDDING_DIM = 384


class Grinder(Base):
    __tablename__ = "grinders"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Bean(Base):
    __tablename__ = "beans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    roaster: Mapped[str | None] = mapped_column(String(200))
    country: Mapped[str | None] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(100))
    variety: Mapped[str | None] = mapped_column(String(100))
    processing: Mapped[str | None] = mapped_column(String(100))
    roast_level: Mapped[str | None] = mapped_column(String(100))
    bag_flavor_notes: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    brews: Mapped[list["Brew"]] = relationship(back_populates="bean")


class Brew(Base):
    __tablename__ = "brews"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_brews_rating"),
        CheckConstraint("grind_clicks IS NULL OR grind_clicks >= 0", name="ck_brews_clicks"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bean_id: Mapped[int] = mapped_column(ForeignKey("beans.id", ondelete="RESTRICT"), index=True)
    grinder_id: Mapped[int | None] = mapped_column(ForeignKey("grinders.id", ondelete="SET NULL"))
    brewed_on: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    # 영점(가장 곱게 조인 상태)에서 푼 클릭 수
    grind_clicks: Mapped[int | None] = mapped_column(Integer)
    water_temp_c: Mapped[int | None] = mapped_column(Integer)
    dose_g: Mapped[float | None] = mapped_column(Float)
    water_g: Mapped[float | None] = mapped_column(Float)
    brew_time_s: Mapped[int | None] = mapped_column(Integer)
    rating: Mapped[int] = mapped_column(Integer)
    flavor_tags: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    bean: Mapped[Bean] = relationship(back_populates="brews")
    grinder: Mapped[Grinder | None] = relationship()
    measurements: Mapped[list["GrindMeasurement"]] = relationship(
        back_populates="brew", order_by="GrindMeasurement.id"
    )


class GrindMeasurement(Base):
    """입도 측정 1회. 추출 기록이 지워져도 클릭 ↔ 입도 표의 근거라서 남긴다 (brew_id SET NULL)."""

    __tablename__ = "grind_measurements"

    id: Mapped[int] = mapped_column(primary_key=True)
    brew_id: Mapped[int | None] = mapped_column(ForeignKey("brews.id", ondelete="SET NULL"), index=True)
    grinder_id: Mapped[int] = mapped_column(ForeignKey("grinders.id", ondelete="CASCADE"), index=True)
    clicks: Mapped[int] = mapped_column(Integer)
    mm_per_px: Mapped[float] = mapped_column(Float)
    particle_count: Mapped[int] = mapped_column(Integer)
    # 투영 면적 가중 백분위 (주 지표)
    d10_mm: Mapped[float] = mapped_column(Float)
    d50_mm: Mapped[float] = mapped_column(Float)
    d90_mm: Mapped[float] = mapped_column(Float)
    # 개수 기준 중앙값 (보조 지표)
    count_d50_mm: Mapped[float] = mapped_column(Float)
    min_detectable_mm: Mapped[float] = mapped_column(Float)
    clump_suspects: Mapped[int] = mapped_column(Integer)
    histogram: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    warnings: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    brew: Mapped[Brew | None] = relationship(back_populates="measurements")


class CatalogBean(Base):
    """로스터리에서 수집한 신상 원두."""

    __tablename__ = "catalog_beans"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(100))
    source_url: Mapped[str] = mapped_column(String(1000), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    raw_text: Mapped[str] = mapped_column(Text)
    price: Mapped[str | None] = mapped_column(String(50))  # 사이트 표기 그대로
    available: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # pending: LLM 정리 전 (한도 소진 시 다음 실행으로 넘어감) | normalized | skipped(원두 아님) | failed
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending", index=True)
    normalized: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # SQL 필터용으로 normalized에서 복사
    country: Mapped[str | None] = mapped_column(String(100))
    processing: Mapped[str | None] = mapped_column(String(100))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Document(Base):
    """검색용 텍스트 + 임베딩. 벡터마다 어떤 모델로 만들었는지 남긴다."""

    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("kind", "ref_id", "model_id", name="uq_documents_ref_model"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))  # bean | catalog
    ref_id: Mapped[int] = mapped_column(Integer)
    model_id: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LlmUsage(Base):
    """모델별 하루 호출 수. day는 태평양 시간 날짜 (Gemini RPD가 태평양 자정에 초기화)."""

    __tablename__ = "llm_usage"

    model: Mapped[str] = mapped_column(String(200), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)


class RecommendationSnapshot(Base):
    """추천 결과 저장본. 공개 조회는 이것만 읽는다 — 방문자가 LLM 할당량을 쓰지 않게."""

    __tablename__ = "recommendation_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    embedding_model: Mapped[str] = mapped_column(String(200))
    llm_model: Mapped[str | None] = mapped_column(String(200))
    profile_brew_ids: Mapped[list[int]] = mapped_column(JSONB)
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
