from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel
from tests.image_support import FIXTURES, make_image_stack, make_new_target

from manga_to_kindle.application.exports.create_export import CreateExport
from manga_to_kindle.application.transfers.open_manual_flow import OpenManualSend
from manga_to_kindle.infrastructure.exports.cbz_validator import ValidateCbz
from manga_to_kindle.infrastructure.exports.cbz_writer import NativeCbzWriter
from manga_to_kindle.infrastructure.exports.epub_validator import ValidateEpub
from manga_to_kindle.infrastructure.exports.epub_writer import NativeEpubWriter
from manga_to_kindle.infrastructure.exports.output_store import ExportOutputStore
from manga_to_kindle.infrastructure.persistence.export_repository import ExportRepository


def _wait_for_operation(window, operation_id: str, qt_core_app) -> None:
    loop = QEventLoop()
    window.operation_runner.finished.connect(
        lambda finished_id: loop.quit() if finished_id == operation_id else None
    )
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    qt_core_app.processEvents()


def test_conversion_view_creates_real_epub_from_processed_local_pages(
    main_window,
    qt_core_app,
    tmp_path: Path,
) -> None:
    database, _image_root, _store, _image_repository, _reader, _decoder, importer = (
        make_image_stack(tmp_path)
    )
    target = make_new_target("Coleção de teste", "Capítulo 1")
    plan = importer.preview_source(FIXTURES / "valid")
    importer.execute(plan, target, confirmed_authorization=True)
    repository = ExportRepository(database)
    workflow = CreateExport(
        repository,
        ExportOutputStore,
        NativeEpubWriter(),
        NativeCbzWriter(),
        ValidateEpub(),
        ValidateCbz(),
    )
    view = main_window.conversion_view
    main_window.set_current_page("conversion")
    view.bind_services(repository, workflow)

    load_id = view._load_operation_id
    assert load_id is not None
    _wait_for_operation(main_window, load_id, qt_core_app)

    class RecordingOpener:
        def __init__(self) -> None:
            self.directories: list[Path] = []
            self.urls: list[str] = []

        def open_directory(self, path: Path) -> bool:
            self.directories.append(path)
            return True

        def open_url(self, url: str) -> bool:
            self.urls.append(url)
            return True

    opener = RecordingOpener()
    main_window.manual_send_view.bind_services(
        repository,
        OpenManualSend(repository, opener),
    )
    load_id = main_window.manual_send_view._load_operation_id
    assert load_id is not None
    _wait_for_operation(main_window, load_id, qt_core_app)

    assert view.chapter_list.count() == 1
    item = view.chapter_list.item(0)
    item.setCheckState(Qt.CheckState.Checked)
    view.profile_combo.setCurrentIndex(1)
    view.language_input.setText("pt-BR")
    output_directory = tmp_path / "epub-output"
    output_directory.mkdir()
    view.output_path.setText(str(output_directory))

    assert view.start_button.isEnabled()
    clicks: list[bool] = []
    view.start_button.clicked.connect(lambda: clicks.append(True))
    view.content_scroll_area.ensureWidgetVisible(view.start_button)
    view.content_scroll_area.verticalScrollBar().setValue(
        view.content_scroll_area.verticalScrollBar().maximum()
    )
    qt_core_app.processEvents()
    QTest.mouseClick(view.start_button, Qt.MouseButton.LeftButton)
    export_id = view._export_operation_id
    if export_id is not None:
        _wait_for_operation(main_window, export_id, qt_core_app)
    else:
        qt_core_app.processEvents()

    output_files = tuple(output_directory.glob("*.epub"))
    assert len(output_files) == 1, (
        f"{view.status_label.text()} clicks={clicks} "
        f"visible={view.start_button.isVisible()} "
        f"scroll={view.content_scroll_area.verticalScrollBar().value()}"
    )
    report = ValidateEpub().execute(output_files[0])
    assert report.page_count == 3
    assert "Exportação concluída" in view.status_label.text()
    assert "simulad" not in view.status_label.text().lower()
    assert view.send_to_kindle_button.isVisible()
    assert view.send_to_kindle_button.isEnabled()
    assert len(repository.list_transfer_artifacts()) == 1
    QTest.mouseClick(view.send_to_kindle_button, Qt.MouseButton.LeftButton)
    assert main_window.page_stack.currentWidget() is main_window.manual_send_view
    refresh_id = main_window.manual_send_view._load_operation_id
    assert refresh_id is not None
    _wait_for_operation(main_window, refresh_id, qt_core_app)
    manual_view = main_window.manual_send_view
    assert manual_view.artifact_combo.count() == 2
    manual_view.artifact_combo.setCurrentIndex(1)
    assert manual_view.open_button.isEnabled()
    QTest.mouseClick(manual_view.open_button, Qt.MouseButton.LeftButton)
    send_id = manual_view._open_operation_id
    assert send_id is not None
    _wait_for_operation(main_window, send_id, qt_core_app)
    assert opener.directories == [output_directory]
    assert opener.urls == ["https://www.amazon.com/sendtokindle"]
    assert "conclua o envio manualmente" in manual_view.status_label.text().lower()
    database.close()


def test_conversion_requires_explicit_language_and_has_no_simulated_formats(
    main_window,
) -> None:
    view = main_window.conversion_view

    formats = [
        view.format_combo.itemText(index).lower()
        for index in range(view.format_combo.count())
    ]
    view.set_selected_chapters(())

    assert len(formats) == 3
    assert all("simulad" not in label for label in formats)
    assert not any("azw3" in label for label in formats)
    assert not view.start_button.isEnabled()
    intro = view.findChild(QLabel, "conversionIntro")
    assert intro is not None and "nada é enviado" in intro.text().lower()


def test_conversion_shows_external_kcc_controls_only_for_mobi(main_window) -> None:
    view = main_window.conversion_view

    assert view.kcc_executable_path.isHidden()
    assert view.choose_kcc_button.isHidden()
    view.format_combo.setCurrentIndex(view.format_combo.findData("mobi"))

    assert not view.kcc_executable_path.isHidden()
    assert not view.choose_kcc_button.isHidden()
    assert view.language_input.isEnabled()
    assert view.direction_combo.isEnabled()

    view.format_combo.setCurrentIndex(view.format_combo.findData("cbz"))
    assert view.kcc_executable_path.isHidden()
    assert view.choose_kcc_button.isHidden()
