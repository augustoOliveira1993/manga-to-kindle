"""Preferência visual persistente, sem credenciais ou dados de conteúdo."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QLabel,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from manga_to_kindle.application.ui.theme_mode import ThemeMode


class SettingsView(QWidget):
    theme_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        title = QLabel("Aparência")
        title.setStyleSheet("font-size: 17px; font-weight: 650;")
        description = QLabel("Escolha o tema da interface. O padrão do aplicativo é claro.")
        description.setObjectName("muted")
        description.setWordWrap(True)
        self.light_button = QRadioButton("Tema claro")
        self.light_button.setObjectName("themeLight")
        self.light_button.setAccessibleName("Usar tema claro")
        self.dark_button = QRadioButton("Tema escuro")
        self.dark_button.setObjectName("themeDark")
        self.dark_button.setAccessibleName("Usar tema escuro")
        group = QButtonGroup(self)
        group.addButton(self.light_button)
        group.addButton(self.dark_button)
        self.light_button.toggled.connect(
            lambda checked: self.theme_changed.emit("light") if checked else None
        )
        self.dark_button.toggled.connect(
            lambda checked: self.theme_changed.emit("dark") if checked else None
        )
        note = QLabel("Serviços reais ainda não estão conectados nesta versão.")
        note.setObjectName("muted")
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(self.light_button)
        layout.addWidget(self.dark_button)
        layout.addWidget(note)
        layout.addStretch(1)
        self.set_theme("light", emit=False)

    def set_theme(self, theme: ThemeMode, *, emit: bool = False) -> None:
        button = self.dark_button if theme == "dark" else self.light_button
        if not emit:
            self.light_button.blockSignals(True)
            self.dark_button.blockSignals(True)
        button.setChecked(True)
        if not emit:
            self.light_button.blockSignals(False)
            self.dark_button.blockSignals(False)

