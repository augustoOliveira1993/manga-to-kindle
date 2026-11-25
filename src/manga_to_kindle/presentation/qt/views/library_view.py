"""Página da biblioteca local vazia ou com fixture explicitamente simulada."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QListWidget, QVBoxLayout, QWidget

from manga_to_kindle.presentation.qt.fixtures import build_demo_catalog
from manga_to_kindle.presentation.qt.views.components import EmptyState


class LibraryView(QWidget):
    add_manga_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        self.state_label = QLabel("Biblioteca vazia")
        self.state_label.setObjectName("libraryState")
        self.state_label.setAccessibleName("Estado da biblioteca")
        self.empty_state = EmptyState(
            "Sua biblioteca começa aqui",
            "Adicione um mangá quando a consulta a fontes autorizadas estiver disponível.",
            "Ver mangá de demonstração",
        )
        self.empty_state.action_requested.connect(self.show_demo)
        self.demo_list = QListWidget()
        self.demo_list.setObjectName("demoLibraryList")
        self.demo_list.setAccessibleName("Mangás de demonstração")
        self.demo_list.hide()
        self.demo_list.itemDoubleClicked.connect(lambda _item: self.add_manga_requested.emit())
        layout.addWidget(self.state_label)
        layout.addWidget(self.empty_state)
        layout.addWidget(self.demo_list, 1)

    def show_demo(self) -> None:
        catalog = build_demo_catalog()
        self.demo_list.clear()
        self.demo_list.addItem(f"{catalog.manga.title}  ·  exemplo local")
        self.empty_state.hide()
        self.demo_list.show()
        self.state_label.setText("1 mangá de demonstração")

