"""Atalhos de navegação da janela desktop."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QWidget


def bind_navigation_shortcuts(
    window: QWidget,
    actions: Sequence[Callable[[], None]],
) -> tuple[QShortcut, ...]:
    """Associa Ctrl+1…Ctrl+5 a ações da navegação principal."""

    shortcuts: list[QShortcut] = []
    for index, action in enumerate(actions, start=1):
        shortcut = QShortcut(QKeySequence(f"Ctrl+{index}"), window)
        shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        shortcut.setWhatsThis(f"Abre a área número {index} da navegação principal.")
        shortcut.activated.connect(action)
        shortcuts.append(shortcut)
    return tuple(shortcuts)

