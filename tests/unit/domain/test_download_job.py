from __future__ import annotations

import pytest
from tests.download_support import make_catalog

from manga_to_kindle.domain.download_job import DownloadJob, DownloadState
from manga_to_kindle.domain.errors import DomainValidationError


def test_interrupted_download_requires_explicit_resume_and_keeps_terminal_states_closed() -> None:
    chapter = make_catalog().chapters[0]
    running = DownloadJob(target_chapter_id=chapter.id).transition_to(DownloadState.RUNNING)
    interrupted = running.transition_to(DownloadState.INTERRUPTED)
    resumed = interrupted.transition_to(DownloadState.RUNNING)

    assert interrupted.state is DownloadState.INTERRUPTED
    assert resumed.state is DownloadState.RUNNING
    recovered_complete = interrupted.transition_to(DownloadState.SUCCEEDED)
    assert recovered_complete.state is DownloadState.SUCCEEDED
    with pytest.raises(DomainValidationError):
        running.transition_to(DownloadState.QUEUED)


def test_download_job_can_record_provider_without_relaxing_target_invariant() -> None:
    chapter = make_catalog().chapters[0]
    job = DownloadJob(target_chapter_id=chapter.id, provider_id="provider-1")

    assert job.provider_id == "provider-1"
    with pytest.raises(DomainValidationError):
        DownloadJob(target_chapter_id=chapter.id, provider_id=" ")
