from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.device_profile import DeviceProfile
from manga_to_kindle.domain.download_job import DownloadJob, DownloadState
from manga_to_kindle.domain.errors import DomainValidationError
from manga_to_kindle.domain.export import Export, ExportState
from manga_to_kindle.domain.manga import Manga
from manga_to_kindle.domain.page import Page


def test_manga_requires_a_title_and_unique_ordered_chapters() -> None:
    manga_id = uuid4()
    chapter_one = Chapter(manga_id=manga_id, position=0, number=Decimal("1"))
    chapter_two = Chapter(manga_id=manga_id, position=1, title="Especial")

    manga = Manga(id=manga_id, title="Exemplo", chapters=(chapter_one, chapter_two))

    assert manga.chapters == (chapter_one, chapter_two)
    with pytest.raises(DomainValidationError):
        Manga(id=manga_id, title="  ")
    with pytest.raises(DomainValidationError):
        Manga(
            id=manga_id,
            title="Exemplo",
            chapters=(chapter_one, Chapter(manga_id=manga_id, position=0, title="Duplicado")),
        )


def test_chapter_requires_display_value_and_valid_position() -> None:
    manga_id = uuid4()

    assert Chapter(manga_id=manga_id, position=0, number=Decimal("1.5"))
    assert Chapter(manga_id=manga_id, position=1, title="Extra")
    with pytest.raises(DomainValidationError):
        Chapter(manga_id=manga_id, position=0)
    with pytest.raises(DomainValidationError):
        Chapter(manga_id=manga_id, position=-1, title="Inválido")
    with pytest.raises(DomainValidationError):
        Chapter(manga_id=manga_id, position=0, number=Decimal("NaN"))


def test_page_keeps_an_immutable_reference_to_the_original() -> None:
    original_path = Path("originais") / "pagina-001.webp"
    page = Page(chapter_id=uuid4(), position=0, original_path=original_path)

    assert page.original_path == original_path
    with pytest.raises((AttributeError, TypeError)):
        page.original_path = Path("derivada.png")  # type: ignore[misc]
    with pytest.raises(DomainValidationError):
        Page(chapter_id=uuid4(), position=-1, original_path=original_path)


def test_download_job_rejects_invalid_target_progress_and_terminal_transition() -> None:
    chapter_id = uuid4()
    job = DownloadJob(target_chapter_id=chapter_id, total=3)

    running = job.transition_to(DownloadState.RUNNING)
    progressed = running.with_progress(2)
    completed = progressed.transition_to(DownloadState.SUCCEEDED)

    assert completed.state is DownloadState.SUCCEEDED
    with pytest.raises(DomainValidationError):
        DownloadJob(target_manga_id=uuid4(), target_chapter_id=chapter_id)
    with pytest.raises(DomainValidationError):
        running.with_progress(4)
    with pytest.raises(DomainValidationError):
        completed.transition_to(DownloadState.RUNNING)


def test_device_profile_freezes_preferences_without_assuming_a_device() -> None:
    preferences = {"reading_direction": "rtl", "grayscale": True}
    profile = DeviceProfile(name="Personalizado", preferences=preferences)
    preferences["grayscale"] = False

    assert profile.preferences["grayscale"] is True
    with pytest.raises(TypeError):
        profile.preferences["grayscale"] = False  # type: ignore[index]
    with pytest.raises(DomainValidationError):
        DeviceProfile(name="  ")


def test_export_requires_chapters_profile_and_local_destination() -> None:
    chapter_id = uuid4()
    profile = DeviceProfile(name="Sem preset físico")
    exported = Export(
        chapter_ids=(chapter_id,),
        device_profile=profile,
        destination=Path("C:/Users/teste/Exports/manga.epub"),
    )

    assert exported.state is ExportState.REQUESTED
    assert exported.created_at.tzinfo is not None
    assert isinstance(exported.created_at, datetime)
    with pytest.raises(DomainValidationError):
        Export(chapter_ids=(), device_profile=profile, destination=Path("out.epub"))
    with pytest.raises(DomainValidationError):
        Export(
            chapter_ids=(chapter_id, chapter_id),
            device_profile=profile,
            destination=Path("C:/out.epub"),
        )


def test_domain_timestamps_are_timezone_aware() -> None:
    job = DownloadJob(target_manga_id=uuid4())

    assert job.created_at.utcoffset() == UTC.utcoffset(None)
