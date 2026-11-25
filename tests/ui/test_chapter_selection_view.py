from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from manga_to_kindle.presentation.qt.fixtures import build_demo_catalog


def test_range_selects_visible_inclusive_rows_by_stable_identity(
    main_window, qt_core_app
) -> None:
    view = main_window.add_manga_view
    catalog = build_demo_catalog()
    view.chapter_list.set_chapters(catalog.chapters)
    view._chapters = catalog.chapters  # noqa: SLF001 - set the application selection boundary
    for combo in (view.range_start_combo, view.range_end_combo):
        combo.clear()
        for chapter in catalog.chapters:
            combo.addItem(chapter.title, chapter.id)
    view.selection_widget.show()
    view.chapter_list.show()
    view.range_start_combo.setCurrentIndex(1)
    view.range_end_combo.setCurrentIndex(3)

    QTest.mouseClick(view.select_range_button, Qt.MouseButton.LeftButton)
    qt_core_app.processEvents()

    expected = tuple(chapter.id for chapter in catalog.chapters[1:4])
    assert view.selected_chapter_ids == expected
    assert view.selection_summary.text() == "3 capítulos selecionados"


def test_chapter_row_exposes_optional_volume_and_availability(main_window) -> None:
    view = main_window.add_manga_view
    chapter = build_demo_catalog().chapters[0]
    chapter = replace(chapter, volume=chapter.number, available=False)

    view.chapter_list.set_chapters((chapter,))

    assert "Volume 1" in view.chapter_list.item(0).text()
    assert "Indisponível" in view.chapter_list.item(0).text()
