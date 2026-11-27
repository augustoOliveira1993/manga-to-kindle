from __future__ import annotations

import json
import socket
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from threading import Event

import pytest
from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtTest import QTest
from tests.download_support import make_repository

from manga_to_kindle.application.catalog.errors import CatalogRefreshCancelled
from manga_to_kindle.application.catalog.get_catalog import GetCatalog
from manga_to_kindle.application.downloads.enqueue import EnqueueDownload, PreparedDownload
from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.domain.catalog import CatalogSnapshot
from manga_to_kindle.domain.providers import ProviderUnavailable
from manga_to_kindle.infrastructure.network.url_policy import ExternalUrlPolicy
from manga_to_kindle.infrastructure.providers.ndl_provider import NdlProvider
from manga_to_kindle.presentation.qt.fixtures import build_demo_catalog


def _wait_for_operation(view, qt_core_app) -> None:
    loop = QEventLoop()
    operation_id = view.operation_id
    view.operation_runner.finished.connect(
        lambda finished_id: loop.quit() if finished_id == operation_id else None
    )
    QTimer.singleShot(3000, loop.quit)
    loop.exec()
    qt_core_app.processEvents()


class _CatalogResponse:
    status_code = 200
    headers = {"Content-Type": "application/json"}

    def __init__(self) -> None:
        self.body = json.dumps(
            {"id": "851650", "title": "北斎漫画", "page": 1},
            ensure_ascii=False,
        ).encode("utf-8")

    def read_limited(self, maximum_bytes: int) -> bytes:
        assert len(self.body) <= maximum_bytes
        return self.body

    def close(self) -> None:
        return None


class _CatalogTransport:
    def get(self, _url, **_kwargs) -> _CatalogResponse:
        return _CatalogResponse()


def test_fixture_url_loads_authorized_offline_catalog_without_network(
    main_window, qt_core_app, monkeypatch
) -> None:
    def reject_network(*_args, **_kwargs) -> None:
        raise AssertionError("F002 tentou acessar a rede")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    main_window.set_current_page("add")
    view = main_window.add_manga_view
    view.url_input.setText("https://fixture.invalid/manga/demo")
    QTest.mouseClick(view.query_button, Qt.MouseButton.LeftButton)
    _wait_for_operation(view, qt_core_app)

    assert view.chapter_list.count() == 7
    assert view.selection_widget.isVisible()
    assert "demonstração" in view.status_label.text().lower()
    assert view.selected_chapter_ids == ()
    assert view.catalog_title.text() == "A Biblioteca das Estrelas"
    assert "Não informado" in view.catalog_metadata.text()


def test_ndl_download_requires_confirmation_and_enqueues_selected_item(
    main_window,
    qt_core_app,
    tmp_path: Path,
    monkeypatch,
) -> None:
    from PySide6.QtWidgets import QMessageBox

    policy = ExternalUrlPolicy(lambda _host: ("93.184.216.34",))
    provider = NdlProvider(_CatalogTransport(), policy)
    providers = ProviderRegistry((provider,))
    catalog = GetCatalog(providers).execute("https://lab.ndl.go.jp/dl/book/851650")
    database, repository = make_repository(tmp_path, catalog)
    preparer = EnqueueDownload(repository, policy)
    main_window.set_current_page("add")
    view = main_window.add_manga_view
    view.set_catalog_query(lambda _url, *, is_cancelled=None: catalog)
    view.set_download_preparer(
        lambda snapshot, selected: preparer.prepare(
            provider=provider,
            catalog=snapshot,
            selected_chapter_ids=selected,
        )
    )
    emitted: list[PreparedDownload] = []
    view.download_enqueued.connect(emitted.append)

    try:
        view.url_input.setText("https://lab.ndl.go.jp/dl/book/851650")
        QTest.mouseClick(view.query_button, Qt.MouseButton.LeftButton)
        _wait_for_operation(view, qt_core_app)
        assert view.download_button.isVisible()
        assert not view.download_button.isEnabled()

        view.chapter_list.item(0).setCheckState(Qt.CheckState.Checked)
        qt_core_app.processEvents()
        assert view.download_button.isEnabled()

        answers = iter((QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes))
        monkeypatch.setattr(QMessageBox, "question", lambda *_args, **_kwargs: next(answers))
        QTest.mouseClick(view.download_button, Qt.MouseButton.LeftButton)
        qt_core_app.processEvents()
        assert emitted == []
        assert repository.list_jobs() == ()

        QTest.mouseClick(view.download_button, Qt.MouseButton.LeftButton)
        operation_id = view._download_operation_id
        assert operation_id is not None
        loop = QEventLoop()
        view.operation_runner.finished.connect(
            lambda finished_id: loop.quit() if finished_id == operation_id else None
        )
        QTimer.singleShot(3000, loop.quit)
        loop.exec()
        qt_core_app.processEvents()

        assert len(emitted) == 1
        assert emitted[0].snapshot.job.total == 1
        assert len(repository.list_jobs()) == 1
    finally:
        database.close()


def test_unsupported_external_url_does_not_fall_back_to_fixture(
    main_window, qt_core_app
) -> None:
    main_window.set_current_page("add")
    view = main_window.add_manga_view
    view.url_input.setText("https://example.test/manga")
    QTest.mouseClick(view.query_button, Qt.MouseButton.LeftButton)
    _wait_for_operation(view, qt_core_app)

    assert "não é suportada" in view.status_label.text().lower()
    assert view.chapter_list.count() == 0
    assert not view.selection_widget.isVisible()


@pytest.mark.parametrize(
    "value",
    [
        "",
        "ftp://example.test/manga",
        "https://usuario:segredo@example.test/manga",
        "https://example.test:70000/manga",
    ],
)
def test_invalid_urls_are_not_echoed(main_window, value: str) -> None:
    main_window.set_current_page("add")
    view = main_window.add_manga_view
    view.url_input.setText(value)
    QTest.mouseClick(view.query_button, Qt.MouseButton.LeftButton)

    assert "inválido" in view.status_label.text().lower()
    assert "example.test" not in view.status_label.text()
    assert "segredo" not in view.status_label.text()
    assert view.chapter_list.count() == 0


def test_keyboard_and_mouse_select_exact_chapters(main_window, qt_core_app) -> None:
    main_window.set_current_page("add")
    view = main_window.add_manga_view
    view.chapter_list.set_chapters(build_demo_catalog().chapters)
    view.selection_widget.show()
    view.chapter_list.show()
    for row in range(3):
        item = view.chapter_list.item(row)
        position = view.chapter_list.visualItemRect(item).center()
        QTest.mouseClick(
            view.chapter_list.viewport(),
            Qt.MouseButton.LeftButton,
            pos=position,
        )
    view.chapter_list.setCurrentRow(1)
    QTest.keyClick(view.chapter_list, Qt.Key.Key_Space)
    qt_core_app.processEvents()

    assert len(view.selected_chapter_ids) == 2
    assert view.selection_summary.text() == "2 capítulos selecionados"

    QTest.mouseClick(view.select_none_button, Qt.MouseButton.LeftButton)
    view.chapter_list.setCurrentRow(0)
    QTest.keyClick(view.chapter_list, Qt.Key.Key_Space)
    QTest.keyClick(view.chapter_list, Qt.Key.Key_Down)
    QTest.keyClick(view.chapter_list, Qt.Key.Key_Space)
    QTest.keyClick(view.chapter_list, Qt.Key.Key_Down)
    QTest.keyClick(view.chapter_list, Qt.Key.Key_Space)
    QTest.keyClick(view.chapter_list, Qt.Key.Key_Up)
    QTest.keyClick(view.chapter_list, Qt.Key.Key_Space)
    qt_core_app.processEvents()

    assert len(view.selected_chapter_ids) == 2
    assert view.selection_summary.text() == "2 capítulos selecionados"


def test_chapter_interval_selection_is_inclusive_and_uses_stable_ids(
    main_window, qt_core_app
) -> None:
    main_window.set_current_page("add")
    view = main_window.add_manga_view
    catalog = build_demo_catalog()
    snapshot = CatalogSnapshot(
        provider_id="fixture",
        source_id="fixture:demo",
        manga=catalog.manga,
        updated_at=datetime.now(UTC),
        simulated=True,
    )
    view.url_input.setText("https://fixture.invalid/manga/demo")
    view.set_catalog_query(lambda _url, *, is_cancelled=None: snapshot)
    QTest.mouseClick(view.query_button, Qt.MouseButton.LeftButton)
    _wait_for_operation(view, qt_core_app)
    view.range_start_combo.setCurrentIndex(1)
    view.range_end_combo.setCurrentIndex(3)
    QTest.mouseClick(view.select_range_button, Qt.MouseButton.LeftButton)
    qt_core_app.processEvents()

    assert view.selected_chapter_ids == tuple(chapter.id for chapter in catalog.chapters[1:4])
    assert view.selection_summary.text() == "3 capítulos selecionados"


def test_catalog_interval_crosses_special_chapters_and_replaces_other_selection(
    main_window, qt_core_app
) -> None:
    main_window.set_current_page("add")
    view = main_window.add_manga_view
    view.url_input.setText("https://fixture.invalid/manga/demo")
    QTest.mouseClick(view.query_button, Qt.MouseButton.LeftButton)
    _wait_for_operation(view, qt_core_app)
    view.chapter_list.item(0).setCheckState(Qt.CheckState.Checked)
    view.range_start_combo.setCurrentIndex(6)
    view.range_end_combo.setCurrentIndex(3)

    QTest.mouseClick(view.select_range_button, Qt.MouseButton.LeftButton)
    qt_core_app.processEvents()

    expected_ids = tuple(
        view.chapter_list.item(row).data(Qt.ItemDataRole.UserRole)
        for row in range(3, 7)
    )
    assert view.selected_chapter_ids == expected_ids
    assert view.selection_summary.text() == "4 capítulos selecionados"


def test_catalog_refresh_keeps_only_selection_ids_that_still_exist(
    main_window, qt_core_app
) -> None:
    main_window.set_current_page("add")
    view = main_window.add_manga_view
    view.url_input.setText("https://fixture.invalid/manga/demo")
    QTest.mouseClick(view.query_button, Qt.MouseButton.LeftButton)
    _wait_for_operation(view, qt_core_app)
    chapter_ids = view.selected_chapter_ids or tuple(
        view.chapter_list.item(row).data(Qt.ItemDataRole.UserRole)
        for row in range(view.chapter_list.count())
    )
    first_id, second_id = chapter_ids[:2]
    view.chapter_list.item(0).setCheckState(Qt.CheckState.Checked)
    qt_core_app.processEvents()

    QTest.mouseClick(view.query_button, Qt.MouseButton.LeftButton)
    _wait_for_operation(view, qt_core_app)

    assert view.selected_chapter_ids == (first_id,)
    assert second_id not in view.selected_chapter_ids

def test_empty_catalog_is_displayed_as_a_valid_result(main_window, qt_core_app) -> None:
    main_window.set_current_page("add")
    view = main_window.add_manga_view
    catalog = build_demo_catalog()
    snapshot = CatalogSnapshot(
        provider_id="fixture",
        source_id="fixture:demo",
        manga=replace(catalog.manga, chapters=()),
        updated_at=datetime.now(UTC),
        simulated=True,
    )
    view.set_catalog_query(lambda _url, *, is_cancelled=None: snapshot)
    view.url_input.setText("https://fixture.invalid/manga/demo")
    QTest.mouseClick(view.query_button, Qt.MouseButton.LeftButton)
    _wait_for_operation(view, qt_core_app)
    assert "nenhum capítulo" in view.status_label.text().lower()
    assert view.chapter_list.count() == 0
    assert view.selection_widget.isVisible()


def test_failed_refresh_keeps_last_catalog_and_selection_visible(
    main_window, qt_core_app
) -> None:
    main_window.set_current_page("add")
    view = main_window.add_manga_view
    catalog = build_demo_catalog()
    snapshot = CatalogSnapshot(
        provider_id="fixture",
        source_id="fixture:demo",
        manga=catalog.manga,
        updated_at=datetime.now(UTC),
        simulated=True,
    )
    calls = 0

    def query(_url: str, *, is_cancelled=None) -> CatalogSnapshot:
        nonlocal calls
        calls += 1
        if calls == 1:
            return snapshot
        raise ProviderUnavailable()

    view.set_catalog_query(query)
    view.url_input.setText("https://fixture.invalid/manga/demo")
    QTest.mouseClick(view.query_button, Qt.MouseButton.LeftButton)
    _wait_for_operation(view, qt_core_app)
    selected_id = catalog.chapters[0].id
    view.chapter_list.item(0).setCheckState(Qt.CheckState.Checked)
    qt_core_app.processEvents()

    QTest.mouseClick(view.query_button, Qt.MouseButton.LeftButton)
    _wait_for_operation(view, qt_core_app)

    assert view.chapter_list.isVisible()
    assert view.selected_chapter_ids == (selected_id,)
    assert "temporariamente indisponível" in view.status_label.text().lower()
    assert "mantido" in view.status_label.text().lower()
    assert view.query_button.isEnabled()


def test_navigation_cancels_catalog_query(main_window, qt_core_app) -> None:
    main_window.set_current_page("add")
    view = main_window.add_manga_view
    started = Event()
    observed_cancellation = Event()

    def query(_url: str, *, is_cancelled=None) -> CatalogSnapshot:
        started.set()
        while is_cancelled is None or not is_cancelled():
            time.sleep(0.005)
        observed_cancellation.set()
        raise CatalogRefreshCancelled("Consulta cancelada antes da gravação.")

    view.set_catalog_query(query)
    view.url_input.setText("https://fixture.invalid/manga/demo")
    QTest.mouseClick(view.query_button, Qt.MouseButton.LeftButton)
    assert started.wait(timeout=2)

    main_window.set_current_page("library")
    _wait_for_operation(view, qt_core_app)
    main_window.set_current_page("add")

    assert observed_cancellation.is_set()
    assert "cancelada" in view.status_label.text().lower()
    assert view.query_button.isEnabled()

