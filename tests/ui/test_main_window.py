from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest


def test_eight_areas_are_navigable_and_library_starts_empty(main_window) -> None:
    expected = {
        "library": "Biblioteca",
        "add": "Adicionar mangá",
        "downloads": "Downloads",
        "conversion": "Conversão",
        "send": "Enviar ao Kindle",
        "settings": "Configurações",
        "images": "Importar imagens",
        "updates": "Atualizações",
    }

    assert main_window.page_stack.count() == 8
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


def test_library_does_not_insert_demo_records_and_empty_action_navigates(main_window) -> None:
    assert main_window.library_view.results_list.count() == 0
    assert main_window.library_view.empty_state.isVisible()
    assert "EXEMPLOS OFFLINE" in main_window.simulation_banner.text()
    QTest.mouseClick(
        main_window.library_view.empty_state.action_button,
        Qt.MouseButton.LeftButton,
    )
    assert main_window.page_title.text() == "Adicionar mangá"
