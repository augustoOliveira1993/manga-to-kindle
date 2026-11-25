from pathlib import Path
from threading import Event, Thread

import pytest

from manga_to_kindle.application.bootstrap import bootstrap_application
from manga_to_kindle.infrastructure.paths import AppPaths
from manga_to_kindle.infrastructure.persistence.database import DatabaseClosedError


def test_shutdown_waits_for_active_local_transaction(tmp_path: Path) -> None:
    runtime = bootstrap_application(AppPaths.from_root(tmp_path))
    shutdown_finished = Event()

    with runtime.database.unit_of_work():
        thread = Thread(target=lambda: (runtime.shutdown(), shutdown_finished.set()))
        thread.start()
        assert not shutdown_finished.wait(0.05)

    thread.join(timeout=2)

    assert shutdown_finished.is_set()
    with pytest.raises(DatabaseClosedError):
        with runtime.database.unit_of_work():
            pass


def test_shutdown_is_idempotent_and_closes_log_handlers(tmp_path: Path) -> None:
    runtime = bootstrap_application(AppPaths.from_root(tmp_path))
    logger = runtime.logging.logger

    runtime.shutdown()
    runtime.shutdown()

    assert not logger.handlers
