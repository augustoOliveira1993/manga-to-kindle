from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest


def test_navigation_buttons_work_with_keyboard(main_window) -> None:
    button = main_window.navigation_buttons["downloads"]
    main_window.activateWindow()
    button.setFocus(Qt.FocusReason.OtherFocusReason)
    QTest.keyClick(button, Qt.Key.Key_Space)

    assert button.focusPolicy() != Qt.FocusPolicy.NoFocus
    assert main_window.page_title.text() == "Downloads"
    assert "EXEMPLOS OFFLINE" in main_window.simulation_banner.text()


def test_chapter_list_has_keyboard_selection_instructions(main_window) -> None:
    main_window.set_current_page("add")

    assert "Espaço" in main_window.add_manga_view.chapter_list.accessibleName()
    assert main_window.add_manga_view.url_input.accessibleName()
    assert main_window.navigation_buttons["add"].accessibleName() == "Adicionar mangá"


def test_shortcuts_switch_areas_without_mouse(main_window) -> None:
    main_window.activateWindow()
    assert QTest.qWaitForWindowActive(main_window, 1000)
    main_window.navigation_buttons["library"].setFocus()
    QTest.keyClick(
        main_window,
        Qt.Key.Key_3,
        Qt.KeyboardModifier.ControlModifier,
    )

    assert main_window.page_title.text() == "Downloads"


def test_tab_order_moves_between_navigation_actions(main_window) -> None:
    first = main_window.navigation_buttons["library"]
    following = main_window.navigation_buttons["add"]

    assert first.nextInFocusChain() is following
    assert first.focusPolicy() != Qt.FocusPolicy.NoFocus
    assert following.focusPolicy() != Qt.FocusPolicy.NoFocus

