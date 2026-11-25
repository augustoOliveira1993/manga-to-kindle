from __future__ import annotations

import socket
from datetime import UTC, datetime

import pytest
from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtTest import QTest

from manga_to_kindle.domain.catalog import CatalogSnapshot
from manga_to_kindle.presentation.qt.fixtures import build_demo_catalog
from manga_to_kindle.presentation.qt.view_models import DemoOutcome


def _wait_for_operation(view, qt_core_app) -> None:
    loop = QEventLoop()
    operation_id = view.operation_id
    view.operation_runner.finished.connect(
        lambda finished_id: loop.quit() if finished_id == operation_id else None
    )
    QTimer.singleShot(3000, loop.quit)
    loop.exec()
    qt_core_app.processEvents()


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

    assert view.chapter_list.count() == 2
    assert view.selection_widget.isVisible()
    assert "demonstração" in view.status_label.text().lower()
    assert view.selected_chapter_ids == ()
    assert view.catalog_title.text() == "A Biblioteca das Estrelas"
    assert "Não informado" in view.catalog_metadata.text()


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
    view.set_catalog_query(lambda _url: snapshot)
    QTest.mouseClick(view.query_button, Qt.MouseButton.LeftButton)
    _wait_for_operation(view, qt_core_app)
    view.range_start_combo.setCurrentIndex(1)
    view.range_end_combo.setCurrentIndex(3)
    QTest.mouseClick(view.select_range_button, Qt.MouseButton.LeftButton)
    qt_core_app.processEvents()

    assert view.selected_chapter_ids == tuple(chapter.id for chapter in catalog.chapters[1:4])
    assert view.selection_summary.text() == "3 capítulos selecionados"


def test_catalog_refresh_keeps_only_selection_ids_that_still_exist(
    main_window, qt_core_app
) -> None:
    main_window.set_current_page("add")
    view = main_window.add_manga_view
    view.url_input.setText("https://fixture.invalid/manga/demo")
    QTest.mouseClick(view.query_button, Qt.MouseButton.LeftButton)
    _wait_for_operation(view, qt_core_app)
    first_id, second_id = view.selected_chapter_ids or tuple(
        view.chapter_list.item(row).data(Qt.ItemDataRole.UserRole)
        for row in range(view.chapter_list.count())
    )
    view.chapter_list.item(0).setCheckState(Qt.CheckState.Checked)
    qt_core_app.processEvents()

    QTest.mouseClick(view.query_button, Qt.MouseButton.LeftButton)
    _wait_for_operation(view, qt_core_app)

    assert view.selected_chapter_ids == (first_id,)
    assert second_id not in view.selected_chapter_ids

def test_empty_catalog_and_simulated_error_have_recovery_action(
    main_window, qt_core_app
) -> None:
    main_window.set_current_page("add")
    view = main_window.add_manga_view
    view.url_input.setText("https://fixture.invalid/manga/demo")
    view.outcome_combo.setCurrentIndex(view.outcome_combo.findData(DemoOutcome.EMPTY))
    QTest.mouseClick(view.query_button, Qt.MouseButton.LeftButton)
    _wait_for_operation(view, qt_core_app)
    assert "sem capítulos" in view.status_label.text().lower()
    assert not view.selection_widget.isVisible()

    view.outcome_combo.setCurrentIndex(view.outcome_combo.findData(DemoOutcome.ERROR))
    QTest.mouseClick(view.query_button, Qt.MouseButton.LeftButton)
    _wait_for_operation(view, qt_core_app)
    assert "falha simulada" in view.status_label.text().lower()
    assert view.query_button.isEnabled()

