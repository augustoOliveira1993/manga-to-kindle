"""Lista local de trabalhos demonstrativos; nenhum conteúdo é baixado."""

from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from manga_to_kindle.presentation.qt.views.components import DemoJobPanel, EmptyState
from manga_to_kindle.presentation.qt.workers.adapter import OperationRunner


class DownloadsView(QWidget):
    def __init__(self, runner: OperationRunner, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        self.empty_state = EmptyState(
            "Nenhum download ativo",
            "Os controles abaixo simulam progresso, falha e cancelamento sem acessar uma fonte.",
            "Iniciar demonstração de download",
        )
        self.job_panel = DemoJobPanel(
            runner,
            action_text="Simular download",
            summary="Download de demonstração concluído.",
        )
        self.empty_state.action_requested.connect(self.job_panel.start_demo)
        layout.addWidget(self.empty_state)
        layout.addWidget(self.job_panel)
        layout.addStretch(1)

