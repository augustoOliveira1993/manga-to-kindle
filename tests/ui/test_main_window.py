from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest


def test_five_areas_are_navigable_and_library_starts_empty(main_window) -> None:
    expected = {
        "library": "Biblioteca",
        "add": "Adicionar mangá",
        "downloads": "Downloads",
        "conversion": "Conversão",
        "settings": "Configurações",
    }

    assert main_window.page_stack.count() == 5
    assert main_window.library_view.empty_state.isVisible()
    main_window.set_current_page("downloads")
    assert main_window.downloads_view.empty_state.isVisible()
    for index, (key, title) in enumerate(expected.items()):
        button = main_window.navigation_buttons[key]
        assert button.accessibleName() == title
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        assert main_window.page_title.text() == title
        assert button.isChecked()
        assert main_window.page_stack.currentIndex() == index


def test_library_demo_is_clearly_marked(main_window) -> None:
    main_window.library_view.show_demo()

    assert main_window.library_view.demo_list.count() == 1
    assert "demonstração" in main_window.library_view.state_label.text().lower()
    assert "A Biblioteca das Estrelas" in main_window.library_view.demo_list.item(0).text()
    assert "DADOS SIMULADOS" in main_window.simulation_banner.text()

