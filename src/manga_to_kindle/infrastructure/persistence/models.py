"""Mapeamentos SQLAlchemy; nunca expostos às camadas de domínio ou interface."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Base comum dos modelos persistentes da aplicação."""


class MangaRecord(Base):
    __tablename__ = "manga"
    __table_args__ = (CheckConstraint("length(trim(title)) > 0", name="ck_manga_title"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(2048))
    provider_id: Mapped[str | None] = mapped_column(String(128))
    author: Mapped[str | None] = mapped_column(String(512))
    cover_path: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(64))
    simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    chapters: Mapped[list[ChapterRecord]] = relationship(back_populates="manga")


class ChapterRecord(Base):
    __tablename__ = "chapter"
    __table_args__ = (
        UniqueConstraint("manga_id", "position", name="uq_chapter_manga_position"),
        CheckConstraint("position >= 0", name="ck_chapter_position"),
        CheckConstraint(
            "length(trim(coalesce(title, ''))) > 0 OR number IS NOT NULL",
            name="ck_chapter_display_value",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    manga_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("manga.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(512))
    number: Mapped[str | None] = mapped_column(String(64))
    volume: Mapped[str | None] = mapped_column(String(64))
    available: Mapped[bool | None] = mapped_column(Boolean)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    manga: Mapped[MangaRecord] = relationship(back_populates="chapters")
    pages: Mapped[list[PageRecord]] = relationship(back_populates="chapter")


class PageRecord(Base):
    __tablename__ = "page"
    __table_args__ = (
        UniqueConstraint("chapter_id", "position", name="uq_page_chapter_position"),
        CheckConstraint("position >= 0", name="ck_page_position"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    chapter_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("chapter.id", ondelete="RESTRICT"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    original_path: Mapped[str] = mapped_column(Text, nullable=False)

    chapter: Mapped[ChapterRecord] = relationship(back_populates="pages")


class DownloadJobRecord(Base):
    __tablename__ = "download_job"
    __table_args__ = (
        CheckConstraint(
            "(manga_id IS NOT NULL AND chapter_id IS NULL) OR "
            "(manga_id IS NULL AND chapter_id IS NOT NULL)",
            name="ck_download_job_single_target",
        ),
        CheckConstraint("progress >= 0", name="ck_download_job_progress_nonnegative"),
        CheckConstraint(
            "total IS NULL OR (total >= 0 AND progress <= total)",
            name="ck_download_job_progress_total",
        ),
        CheckConstraint(
            "state IN ('queued', 'running', 'paused', 'succeeded', 'failed', 'cancelled')",
            name="ck_download_job_state",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    manga_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("manga.id", ondelete="RESTRICT")
    )
    chapter_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("chapter.id", ondelete="RESTRICT")
    )
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="queued")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total: Mapped[int | None] = mapped_column(Integer)
    cancel_requested: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DeviceProfileRecord(Base):
    __tablename__ = "device_profile"
    __table_args__ = (CheckConstraint("length(trim(name)) > 0", name="ck_device_profile_name"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ExportRecord(Base):
    __tablename__ = "export"
    __table_args__ = (
        CheckConstraint("length(trim(destination)) > 0", name="ck_export_destination"),
        CheckConstraint(
            "state IN ('requested', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_export_state",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    profile_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    destination: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="requested")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    chapters: Mapped[list[ExportChapterRecord]] = relationship(back_populates="export")


class ExportChapterRecord(Base):
    __tablename__ = "export_chapter"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_export_chapter_position"),
        UniqueConstraint("export_id", "position", name="uq_export_chapter_position"),
    )

    export_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("export.id", ondelete="RESTRICT"), primary_key=True
    )
    chapter_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("chapter.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    export: Mapped[ExportRecord] = relationship(back_populates="chapters")


class CatalogMembershipRecord(Base):
    __tablename__ = "catalog_membership"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_catalog_membership_position"),
        UniqueConstraint("manga_id", "position", name="uq_catalog_manga_position"),
    )

    manga_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("manga.id", ondelete="RESTRICT"), primary_key=True
    )
    chapter_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("chapter.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    source_order: Mapped[int | None] = mapped_column(Integer)
