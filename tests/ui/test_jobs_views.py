from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtTest import QTest

from manga_to_kindle.presentation.qt.fixtures import build_demo_catalog
from manga_to_kindle.presentation.qt.view_models import DemoOutcome


def _wait_for_operation(view, qt_core_app) -> None:
    loop = QEventLoop()
    operation_id = view.job_panel.operation_id
    view.job_panel.operation_runner.finished.connect(
        lambda finished_id: loop.quit() if finished_id == operation_id else None
    )
    QTimer.singleShot(3000, loop.quit)
    loop.exec()
    qt_core_app.processEvents()


def test_download_demo_shows_success_error_and_cancellation(main_window, qt_core_app) -> None:
    main_window.set_current_page("downloads")
    panel = main_window.downloads_view.job_panel
    QTest.mouseClick(panel.start_button, Qt.MouseButton.LeftButton)
    _wait_for_operation(main_window.downloads_view, qt_core_app)
    assert "demonstração concluído" in panel.status_label.text().lower()
    assert "nenhum arquivo" in panel.status_label.text().lower()

    panel.outcome_combo.setCurrentIndex(panel.outcome_combo.findData(DemoOutcome.ERROR))
    QTest.mouseClick(panel.start_button, Qt.MouseButton.LeftButton)
    _wait_for_operation(main_window.downloads_view, qt_core_app)
    assert "falha simulada" in panel.status_label.text().lower()

    panel.outcome_combo.setCurrentIndex(panel.outcome_combo.findData(DemoOutcome.SUCCESS))
    QTest.mouseClick(panel.start_button, Qt.MouseButton.LeftButton)
    QTimer.singleShot(40, panel.cancel_demo)
    loop = QEventLoop()
    operation_id = panel.operation_id
    panel.operation_runner.finished.connect(
        lambda finished_id: loop.quit() if finished_id == operation_id else None
    )
    QTimer.singleShot(3000, loop.quit)
    loop.exec()
    qt_core_app.processEvents()
    assert "cancelada" in panel.status_label.text().lower()


def test_conversion_validates_inputs_and_writes_no_files(
    main_window, qt_core_app, monkeypatch, tmp_path: Path
) -> None:
    main_window.set_current_page("conversion")
    view = main_window.conversion_view
    view.set_selected_chapters(build_demo_catalog().chapters[:2][0:1])
    monkeypatch.setattr(
        "manga_to_kindle.presentation.qt.views.conversion_view.QFileDialog.getExistingDirectory",
        lambda *_args: str(tmp_path),
    )
    QTest.mouseClick(view.choose_folder_button, Qt.MouseButton.LeftButton)
    view.profile_combo.setCurrentIndex(1)
    view.format_combo.setCurrentIndex(1)

    assert view.job_panel.start_button.isEnabled()
    QTest.mouseClick(view.job_panel.start_button, Qt.MouseButton.LeftButton)
    _wait_for_operation(view, qt_core_app)

    assert "prévia simulada concluída" in view.job_panel.status_label.text().lower()
    assert list(tmp_path.iterdir()) == []


def test_missing_output_folder_fails_in_worker_without_blocking_ui(
    main_window, qt_core_app, monkeypatch, tmp_path: Path
) -> None:
    main_window.set_current_page("conversion")
    view = main_window.conversion_view
    view.set_selected_chapters(build_demo_catalog().chapters[:1])
    missing_directory = tmp_path / "ausente"
    monkeypatch.setattr(
        "manga_to_kindle.presentation.qt.views.conversion_view.QFileDialog.getExistingDirectory",
        lambda *_args: str(missing_directory),
    )
    QTest.mouseClick(view.choose_folder_button, Qt.MouseButton.LeftButton)
    view.profile_combo.setCurrentIndex(1)
    view.format_combo.setCurrentIndex(1)
    QTest.mouseClick(view.job_panel.start_button, Qt.MouseButton.LeftButton)
    _wait_for_operation(view, qt_core_app)

    assert "pasta escolhida não está disponível" in view.job_panel.status_label.text().lower()
    assert not missing_directory.exists()

