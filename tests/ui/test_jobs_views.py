from __future__ import annotations

from PySide6.QtWidgets import QLabel


def test_downloads_view_does_not_present_a_simulated_download(main_window) -> None:
    main_window.set_current_page("downloads")
    view = main_window.downloads_view

    labels = [label.text().lower() for label in view.empty_state.findChildren(QLabel)]
    assert any("nenhuma fonte autorizada" in label for label in labels)
    assert not view.empty_state.action_button.isEnabled()
    assert any("não permite baixar" in label for label in labels)
    assert not view.pause_button.isEnabled()
    assert not view.resume_button.isEnabled()
    assert not view.cancel_button.isEnabled()

