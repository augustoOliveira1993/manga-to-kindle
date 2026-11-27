from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from manga_to_kindle.domain.catalog import CatalogSnapshot
from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.manga import Manga
from manga_to_kindle.domain.updates import (
    UpdateCheck,
    UpdateCheckStatus,
    UpdatePreference,
)
from manga_to_kindle.infrastructure.paths import AppPaths
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.models import ChapterNoticeRecord
from manga_to_kindle.infrastructure.persistence.update_repository import (
    UpdatePersistenceError,
    UpdateRepository,
)


def test_update_history_notices_and_opt_out_survive_database_restart(tmp_path) -> None:
    database_path = AppPaths.from_root(tmp_path).database_file
    database = SQLiteDatabase(database_path)
    database.initialize()
    repository = UpdateRepository(database)
    manga_id = uuid4()
    chapter_id = uuid4()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    chapter = Chapter(
        manga_id=manga_id,
        id=chapter_id,
        position=0,
        title="Capítulo novo",
        number=Decimal("1"),
        source_chapter_id="provider:chapter-1",
    )
    snapshot = CatalogSnapshot(
        provider_id="provider",
        source_id="provider:series-1",
        manga=Manga(
            id=manga_id,
            title="Série autorizada",
            source_ref="provider:series-1",
            chapters=(chapter,),
        ),
        updated_at=now,
        simulated=False,
    )
    check = UpdateCheck(
        manga_id=manga_id,
        provider_id="provider",
        started_at=now,
        finished_at=now,
        status=UpdateCheckStatus.SUCCEEDED,
        chapter_count=1,
        new_chapter_count=1,
    )
    try:
        notices = repository.commit_snapshot(snapshot, check, ("provider:chapter-1",))
        assert len(notices) == 1
        assert repository.list_notices(manga_id, unread_only=True) == notices
        assert repository.latest_check(manga_id) == check
        saved = repository.save_preference(
            UpdatePreference(
                manga_id=manga_id,
                enabled=True,
                interval_seconds=600,
                notifications_enabled=False,
                updated_at=now,
            )
        )
        assert saved.notifications_enabled is False
    finally:
        database.close()

    reopened = SQLiteDatabase(database_path)
    reopened.initialize()
    try:
        after_restart = UpdateRepository(reopened)
        statuses = after_restart.list_statuses()
        assert len(statuses) == 1
        assert statuses[0].last_check == check
        assert statuses[0].unread_notice_count == 1
        assert after_restart.get_preference(manga_id).enabled is True
        assert after_restart.get_preference(manga_id).notifications_enabled is False
        assert len(after_restart.list_notices(manga_id)) == 1
        assert after_restart.mark_notice_read(notices[0].id, now)
        assert after_restart.list_notices(manga_id, unread_only=True) == ()
    finally:
        reopened.close()


def test_snapshot_and_update_history_roll_back_together_on_invalid_notice(tmp_path) -> None:
    database = SQLiteDatabase(AppPaths.from_root(tmp_path).database_file)
    database.initialize()
    repository = UpdateRepository(database)
    manga_id = uuid4()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    chapter = Chapter(
        manga_id=manga_id,
        position=0,
        title="Capítulo",
        source_chapter_id="provider:chapter-1",
    )
    snapshot = CatalogSnapshot(
        provider_id="provider",
        source_id="provider:series-1",
        manga=Manga(
            id=manga_id,
            title="Série",
            source_ref="provider:series-1",
            chapters=(chapter,),
        ),
        updated_at=now,
        simulated=False,
    )
    check = UpdateCheck(
        manga_id=manga_id,
        provider_id="provider",
        started_at=now,
        finished_at=now,
        status=UpdateCheckStatus.SUCCEEDED,
        chapter_count=1,
        new_chapter_count=1,
    )
    try:
        with pytest.raises(UpdatePersistenceError):
            repository.commit_snapshot(snapshot, check, ("provider:missing",))
        assert repository.latest_check(manga_id) is None
        assert repository.list_statuses() == ()
    finally:
        database.close()


def test_database_has_unique_provider_scoped_chapter_identity(tmp_path) -> None:
    database = SQLiteDatabase(AppPaths.from_root(tmp_path).database_file)
    database.initialize()
    repository = UpdateRepository(database)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    manga_id = uuid4()
    chapter = Chapter(
        manga_id=manga_id,
        position=0,
        title="Capítulo",
        source_chapter_id="provider:chapter-1",
    )
    snapshot = CatalogSnapshot(
        provider_id="provider",
        source_id="provider:series-1",
        manga=Manga(id=manga_id, title="Série", chapters=(chapter,)),
        updated_at=now,
        simulated=False,
    )
    check = UpdateCheck(
        manga_id=manga_id,
        provider_id="provider",
        started_at=now,
        finished_at=now,
        status=UpdateCheckStatus.SUCCEEDED,
        chapter_count=1,
    )
    try:
        repository.commit_snapshot(snapshot, check, ())
        with database.unit_of_work() as session:
            rows = tuple(
                session.scalars(
                    select(ChapterNoticeRecord).where(
                        ChapterNoticeRecord.source_chapter_id == "provider:chapter-1"
                    )
                )
            )
        assert rows == ()
    finally:
        database.close()
