from __future__ import annotations

from PySide6.QtWidgets import QLabel


def test_downloads_view_requires_an_explicit_real_item_selection(main_window) -> None:
    main_window.set_current_page("downloads")
    view = main_window.downloads_view

    labels = [label.text().lower() for label in view.empty_state.findChildren(QLabel)]
    assert any("item individual ndl" in label for label in labels)
    assert not view.empty_state.action_button.isEnabled()
    assert any("fixture offline não autoriza downloads" in label for label in labels)
    assert not view.pause_button.isEnabled()
    assert not view.resume_button.isEnabled()
    assert not view.cancel_button.isEnabled()

