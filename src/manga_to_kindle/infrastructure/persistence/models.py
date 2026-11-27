"""Mapeamentos SQLAlchemy; nunca expostos às camadas de domínio ou interface."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Base comum dos modelos persistentes da aplicação."""


class MangaRecord(Base):
    __tablename__ = "manga"
    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="ck_manga_title"),
        Index("ix_manga_title_nocase", "title"),
        Index("ix_manga_favorite_updated", "favorite", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    search_key: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_ref: Mapped[str | None] = mapped_column(String(2048))
    provider_id: Mapped[str | None] = mapped_column(String(128))
    author: Mapped[str | None] = mapped_column(String(512))
    cover_path: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(64))
    simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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
        Index("ix_chapter_manga_favorite_position", "manga_id", "favorite", "position"),
        Index(
            "uq_chapter_manga_source_id",
            "manga_id",
            "source_chapter_id",
            unique=True,
            sqlite_where=text("source_chapter_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    manga_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("manga.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(512))
    search_key: Mapped[str] = mapped_column(Text, nullable=False, default="")
    number: Mapped[str | None] = mapped_column(String(64))
    volume: Mapped[str | None] = mapped_column(String(64))
    source_chapter_id: Mapped[str | None] = mapped_column(String(512))
    available: Mapped[bool | None] = mapped_column(Boolean)
    favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    manga: Mapped[MangaRecord] = relationship(back_populates="chapters")
    pages: Mapped[list[PageRecord]] = relationship(back_populates="chapter")


class UpdatePreferenceRecord(Base):
    __tablename__ = "update_preference"
    __table_args__ = (
        CheckConstraint("enabled IN (0, 1)", name="ck_update_preference_enabled"),
        CheckConstraint(
            "interval_seconds IS NULL OR interval_seconds >= 1",
            name="ck_update_preference_interval",
        ),
        CheckConstraint(
            "enabled = 0 OR interval_seconds IS NOT NULL",
            name="ck_update_preference_enabled_interval",
        ),
    )

    manga_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("manga.id", ondelete="RESTRICT"), primary_key=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    interval_seconds: Mapped[int | None] = mapped_column(Integer)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class UpdateCheckRecord(Base):
    __tablename__ = "update_check"
    __table_args__ = (
        CheckConstraint(
            "status IN ('succeeded', 'failed', 'rate_limited', 'cancelled', 'unsupported')",
            name="ck_update_check_status",
        ),
        CheckConstraint("chapter_count >= 0", name="ck_update_check_chapter_count"),
        CheckConstraint(
            "new_chapter_count >= 0 AND new_chapter_count <= chapter_count",
            name="ck_update_check_new_count",
        ),
        CheckConstraint(
            "policy_fingerprint IS NULL OR length(policy_fingerprint) = 64",
            name="ck_update_check_policy_fingerprint",
        ),
        Index("ix_update_check_manga_started", "manga_id", "started_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    manga_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("manga.id", ondelete="RESTRICT"), nullable=False
    )
    provider_id: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    chapter_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_chapter_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    safe_error_code: Mapped[str | None] = mapped_column(String(64))
    retry_after_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    policy_fingerprint: Mapped[str | None] = mapped_column(String(64))


class ChapterNoticeRecord(Base):
    __tablename__ = "chapter_notice"
    __table_args__ = (
        UniqueConstraint(
            "manga_id",
            "provider_id",
            "source_chapter_id",
            name="uq_chapter_notice_stable_identity",
        ),
        Index("ix_chapter_notice_manga_read", "manga_id", "read_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    manga_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("manga.id", ondelete="RESTRICT"), nullable=False
    )
    provider_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_chapter_id: Mapped[str] = mapped_column(String(512), nullable=False)
    chapter_title_snapshot: Mapped[str] = mapped_column(String(512), nullable=False)
    chapter_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("chapter.id", ondelete="RESTRICT"), nullable=False
    )
    check_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("update_check.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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
    source_relative_path: Mapped[str | None] = mapped_column(Text)
    source_sha256: Mapped[str | None] = mapped_column(String(64))
    source_media_type: Mapped[str | None] = mapped_column(String(32))
    source_width: Mapped[int | None] = mapped_column(Integer)
    source_height: Mapped[int | None] = mapped_column(Integer)
    import_job_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    duplicate_content: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    chapter: Mapped[ChapterRecord] = relationship(back_populates="pages")


class ImageImportJobRecord(Base):
    __tablename__ = "image_import_job"
    __table_args__ = (
        CheckConstraint(
            "state IN ('staging', 'succeeded', 'failed', 'cancelled', 'interrupted')",
            name="ck_image_import_job_state",
        ),
        CheckConstraint("total_images >= 0", name="ck_image_import_job_total"),
        CheckConstraint("completed_images >= 0", name="ck_image_import_job_completed"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    source_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    target_manga_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    target_chapter_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    manga_title_snapshot: Mapped[str | None] = mapped_column(String(512))
    chapter_title_snapshot: Mapped[str | None] = mapped_column(String(512))
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    total_images: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_images: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProcessedPageRecord(Base):
    __tablename__ = "processed_page"
    __table_args__ = (
        CheckConstraint("output_order >= 0", name="ck_processed_page_order"),
        CheckConstraint(
            "width BETWEEN 1 AND 10000 AND height BETWEEN 1 AND 10000 "
            "AND width * height <= 50000000",
            name="ck_processed_page_profile_size",
        ),
        UniqueConstraint("page_id", "output_order", name="uq_processed_page_order"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    page_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("page.id", ondelete="RESTRICT"), nullable=False
    )
    output_order: Mapped[int] = mapped_column(Integer, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    profile_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


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
            "state IN ('queued', 'running', 'paused', 'interrupted', "
            "'succeeded', 'failed', 'cancelled')",
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
    provider_id: Mapped[str | None] = mapped_column(String(128))
    policy_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DownloadChapterRecord(Base):
    __tablename__ = "download_chapter"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_download_chapter_position"),
        CheckConstraint(
            "page_total IS NULL OR (page_total >= 0 AND page_completed <= page_total)",
            name="ck_download_chapter_progress",
        ),
        UniqueConstraint("job_id", "position", name="uq_download_chapter_position"),
    )

    job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("download_job.id", ondelete="RESTRICT"), primary_key=True
    )
    chapter_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("chapter.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="queued")
    page_total: Mapped[int | None] = mapped_column(Integer)
    page_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class DownloadPageRecord(Base):
    __tablename__ = "download_page"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_download_page_position"),
        CheckConstraint("attempts >= 0", name="ck_download_page_attempts"),
        CheckConstraint("byte_size IS NULL OR byte_size >= 0", name="ck_download_page_size"),
        CheckConstraint(
            "state IN ('queued', 'running', 'staging', 'waiting_retry', "
            "'interrupted', 'complete', 'failed')",
            name="ck_download_page_state",
        ),
        UniqueConstraint(
            "job_id", "chapter_id", "provider_page_id", name="uq_download_page_identity"
        ),
        UniqueConstraint("job_id", "chapter_id", "position", name="uq_download_page_position"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("download_job.id", ondelete="RESTRICT"), nullable=False
    )
    chapter_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("chapter.id", ondelete="RESTRICT"), nullable=False
    )
    provider_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_page_id: Mapped[str] = mapped_column(String(512), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="queued")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    byte_size: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64))
    original_path: Mapped[str | None] = mapped_column(Text)
    temporary_path: Mapped[str | None] = mapped_column(Text)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))
    content_validator: Mapped[str | None] = mapped_column(String(512))
    duplicate_content: Mapped[bool] = mapped_column(nullable=False, default=False)


class DeviceProfileRecord(Base):
    __tablename__ = "device_profile"
    __table_args__ = (CheckConstraint("length(trim(name)) > 0", name="ck_device_profile_name"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ApplicationPreferencesRecord(Base):
    __tablename__ = "application_preferences"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_application_preferences_singleton"),
        CheckConstraint(
            "download_concurrency BETWEEN 1 AND 2",
            name="ck_application_preferences_download_concurrency",
        ),
        CheckConstraint(
            "cache_limit_bytes BETWEEN 104857600 AND 21474836480",
            name="ck_application_preferences_cache_limit",
        ),
        CheckConstraint(
            "cache_retention_days BETWEEN 1 AND 365",
            name="ck_application_preferences_cache_retention",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    selected_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    download_concurrency: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    download_directory: Mapped[str] = mapped_column(Text, nullable=False)
    export_directory: Mapped[str] = mapped_column(Text, nullable=False)
    cache_directory: Mapped[str] = mapped_column(Text, nullable=False)
    cache_limit_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1073741824)
    cache_retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CacheManifestRecord(Base):
    __tablename__ = "cache_manifest"
    __table_args__ = (
        UniqueConstraint("root_path", "relative_path", name="uq_cache_manifest_path"),
        CheckConstraint("length(sha256) = 64", name="ck_cache_manifest_sha256"),
        CheckConstraint("size_bytes >= 0", name="ck_cache_manifest_size"),
        CheckConstraint(
            "category IN ('preview', 'thumbnail')",
            name="ck_cache_manifest_category",
        ),
        Index("ix_cache_manifest_root_accessed", "root_path", "last_accessed_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    root_path: Mapped[str] = mapped_column(Text, nullable=False)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    in_use: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


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
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    chapters: Mapped[list[ExportChapterRecord]] = relationship(back_populates="export")
    artifacts: Mapped[list[ExportArtifactRecord]] = relationship(back_populates="export")


class ExportArtifactRecord(Base):
    __tablename__ = "export_artifact"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_export_artifact_position"),
        CheckConstraint("format IN ('epub', 'cbz', 'mobi')", name="ck_export_artifact_format"),
        CheckConstraint("length(sha256) = 64", name="ck_export_artifact_sha256"),
        CheckConstraint("size_bytes > 0", name="ck_export_artifact_size"),
        UniqueConstraint("export_id", "position", name="uq_export_artifact_position"),
        UniqueConstraint("export_id", "package_id", name="uq_export_artifact_package"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    export_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("export.id", ondelete="RESTRICT"), nullable=False
    )
    package_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    format: Mapped[str] = mapped_column(String(8), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    chapter_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    export: Mapped[ExportRecord] = relationship(back_populates="artifacts")


class SmtpProfileRecord(Base):
    __tablename__ = "smtp_profile"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_smtp_profile_singleton"),
        CheckConstraint("port BETWEEN 1 AND 65535", name="ck_smtp_profile_port"),
        CheckConstraint("tls_mode IN ('starttls', 'implicit')", name="ck_smtp_profile_tls"),
        CheckConstraint(
            "(username IS NULL AND credential_ref IS NULL) OR "
            "(username IS NOT NULL AND credential_ref IS NOT NULL)",
            name="ck_smtp_profile_auth_reference",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    host: Mapped[str] = mapped_column(String(253), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    tls_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    sender: Mapped[str] = mapped_column(String(254), nullable=False)
    recipient: Mapped[str] = mapped_column(String(254), nullable=False)
    username: Mapped[str | None] = mapped_column(String(513))
    credential_ref: Mapped[str | None] = mapped_column(String(36))
    sender_authorized: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recipient_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TransferJobRecord(Base):
    __tablename__ = "transfer_job"
    __table_args__ = (
        CheckConstraint(
            "state IN ('connecting', 'authenticating', 'transmitting', "
            "'accepted_by_smtp', 'rejected_temporary', 'rejected_permanent', "
            "'failed_before_submission', 'cancelled_before_submission', 'unknown', 'interrupted')",
            name="ck_transfer_job_state",
        ),
        CheckConstraint(
            "stage IN ('connecting', 'tls', 'authenticating', 'envelope', "
            "'transmitting', 'finished')",
            name="ck_transfer_job_stage",
        ),
        CheckConstraint("port BETWEEN 1 AND 65535", name="ck_transfer_job_port"),
        CheckConstraint("length(export_sha256) = 64", name="ck_transfer_job_sha256"),
        CheckConstraint("size_bytes > 0", name="ck_transfer_job_size"),
        CheckConstraint("tls_mode IN ('starttls', 'implicit')", name="ck_transfer_job_tls"),
        Index("ix_transfer_job_created", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    artifact_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("export_artifact.id", ondelete="RESTRICT"),
        nullable=False,
    )
    export_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    export_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    format: Mapped[str] = mapped_column(String(8), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    stage: Mapped[str] = mapped_column(String(16), nullable=False)
    host: Mapped[str] = mapped_column(String(253), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    tls_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    sender: Mapped[str] = mapped_column(String(254), nullable=False)
    recipient_masked: Mapped[str] = mapped_column(String(254), nullable=False)
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    error_code: Mapped[str | None] = mapped_column(String(64))
    smtp_code: Mapped[int | None] = mapped_column(Integer)


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


class LibraryPreferenceRecord(Base):
    __tablename__ = "library_preference"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_library_preference_singleton"),
        CheckConstraint(
            "availability_filter IS NULL OR availability_filter IN "
            "('downloaded', 'partial', 'not_downloaded', 'imported', 'missing', 'altered')",
            name="ck_library_preference_availability",
        ),
        CheckConstraint(
            "sort_order IN ('title', 'activity', 'state', 'chapter')",
            name="ck_library_preference_sort",
        ),
        CheckConstraint(
            "download_state IS NULL OR download_state IN "
            "('queued', 'running', 'paused', 'interrupted', 'succeeded', 'failed', 'cancelled')",
            name="ck_library_preference_download_state",
        ),
        CheckConstraint(
            "export_state IS NULL OR export_state IN "
            "('requested', 'running', 'completed', 'failed', 'cancelled', 'missing', 'altered')",
            name="ck_library_preference_export_state",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    favorite_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    availability_filter: Mapped[str | None] = mapped_column(String(32))
    download_state: Mapped[str | None] = mapped_column(String(24))
    export_state: Mapped[str | None] = mapped_column(String(24))
    sort_order: Mapped[str] = mapped_column(String(16), nullable=False, default="title")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class LibraryAssetRecord(Base):
    """Registro de arquivo que ficou sem vínculo depois da remoção de seus registros."""

    __tablename__ = "library_asset"
    __table_args__ = (
        CheckConstraint(
            "category IN ('original', 'processed', 'download', 'export')",
            name="ck_library_asset_category",
        ),
        CheckConstraint(
            "state IN ('unlinked', 'missing', 'changed')",
            name="ck_library_asset_state",
        ),
        CheckConstraint("size_bytes >= 0", name="ck_library_asset_size"),
        UniqueConstraint("path", name="uq_library_asset_path"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    media_type: Mapped[str | None] = mapped_column(String(64))
    managed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="unlinked")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class LibraryDeletionPlanRecord(Base):
    __tablename__ = "library_deletion_plan"
    __table_args__ = (
        CheckConstraint(
            "state IN ('planned', 'running', 'completed', 'partial', 'failed')",
            name="ck_library_deletion_plan_state",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="planned")
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class LibraryDeletionItemRecord(Base):
    __tablename__ = "library_deletion_item"
    __table_args__ = (
        CheckConstraint("kind IN ('record', 'asset')", name="ck_library_deletion_item_kind"),
        CheckConstraint(
            "state IN ('pending', 'deleted', 'preserved', 'missing', 'changed', 'failed')",
            name="ck_library_deletion_item_state",
        ),
        CheckConstraint(
            "size_bytes IS NULL OR size_bytes >= 0",
            name="ck_library_deletion_item_size",
        ),
        UniqueConstraint("plan_id", "kind", "target_id", name="uq_library_deletion_item_target"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    plan_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("library_deletion_plan.id", ondelete="RESTRICT"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(8), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str | None] = mapped_column(String(16))
    path: Mapped[str | None] = mapped_column(Text)
    sha256: Mapped[str | None] = mapped_column(String(64))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    error_code: Mapped[str | None] = mapped_column(String(64))
