"""Janela principal com navegação, estados vazios e dados de demonstração."""

from __future__ import annotations

from collections.abc import Mapping

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from manga_to_kindle.application.ui.theme_mode import ThemeMode
from manga_to_kindle.presentation.qt.shortcuts import bind_navigation_shortcuts
from manga_to_kindle.presentation.qt.theme import stylesheet_for
from manga_to_kindle.presentation.qt.views.add_manga_view import AddMangaView
from manga_to_kindle.presentation.qt.views.components import SimulationBanner
from manga_to_kindle.presentation.qt.views.conversion_view import ConversionView
from manga_to_kindle.presentation.qt.views.downloads_view import DownloadsView
from manga_to_kindle.presentation.qt.views.image_import_view import ImageImportView
from manga_to_kindle.presentation.qt.views.library_view import LibraryView
from manga_to_kindle.presentation.qt.views.manual_send_view import ManualSendView
from manga_to_kindle.presentation.qt.views.settings_view import SettingsView
from manga_to_kindle.presentation.qt.views.update_settings_view import UpdateSettingsView
from manga_to_kindle.presentation.qt.workers.adapter import OperationRunner
from manga_to_kindle.presentation.qt.workers.demo import CatalogQuery


class MainWindow(QMainWindow):
    close_requested = Signal()
    theme_change_requested = Signal(str)
    page_changed = Signal(str)

    _PAGES: tuple[tuple[str, str, str, str], ...] = (
        ("library", "▤  Biblioteca", "Biblioteca", "Sua coleção local"),
        ("add", "＋  Adicionar mangá", "Adicionar mangá", "Catálogo local de demonstração"),
        ("downloads", "↓  Downloads", "Downloads", "Fila local; fonte autorizada indisponível"),
        ("conversion", "▣  Conversão", "Conversão", "EPUB e CBZ locais; sem envio"),
        ("send", "↗  Enviar ao Kindle", "Enviar ao Kindle", "Fluxo manual oficial"),
        ("settings", "⚙  Configurações", "Configurações", "Aparência e preferências"),
        ("images", "▧  Importar imagens", "Importar imagens", "Origem local autorizada"),
        (
            "updates",
            "◷  Atualizações",
            "Atualizações",
            "Monitoramento opt-in; sem download automático",
        ),
    )

    def __init__(
        self,
        parent: QWidget | None = None,
        catalog_query: CatalogQuery | None = None,
    ) -> None:
        super().__init__(parent)
        self._allow_close = False
        self._theme: ThemeMode = "light"
        self.operation_runner = OperationRunner(self)
        self.setWindowTitle("Manga to Kindle")
        self.setMinimumSize(900, 600)

        root = QWidget(self)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(225)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 22, 18, 18)
        sidebar_layout.setSpacing(10)
        brand_row = QHBoxLayout()
        brand_mark = QLabel("MK")
        brand_mark.setObjectName("brandMark")
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_mark.setFixedSize(42, 42)
        brand_label = QLabel("Manga to Kindle")
        brand_label.setStyleSheet("font-size: 15px; font-weight: 700;")
        brand_row.addWidget(brand_mark)
        brand_row.addWidget(brand_label, 1)
        sidebar_layout.addLayout(brand_row)
        sidebar_layout.addSpacing(20)
        nav_caption = QLabel("ESPAÇO LOCAL")
        nav_caption.setObjectName("eyebrow")
        sidebar_layout.addWidget(nav_caption)
        self.navigation_group = QButtonGroup(self)
        self.navigation_group.setExclusive(True)
        self.navigation_buttons: dict[str, QPushButton] = {}
        for key, text, _, _ in self._PAGES:
            button = QPushButton(text)
            button.setObjectName(f"nav_{key}")
            button.setAccessibleName(text.split("  ", maxsplit=1)[-1])
            button.setCheckable(True)
            button.setAutoDefault(False)
            self.navigation_group.addButton(button)
            self.navigation_buttons[key] = button
            sidebar_layout.addWidget(button)
            button.clicked.connect(lambda _checked=False, page=key: self.set_current_page(page))
        navigation_order = tuple(self.navigation_buttons.values())
        for previous, following in zip(navigation_order, navigation_order[1:], strict=False):
            QWidget.setTabOrder(previous, following)
        sidebar_layout.addStretch(1)
        local_note = QLabel("LOCAL • sem sincronização\nDados sob seu controle")
        local_note.setObjectName("muted")
        local_note.setWordWrap(True)
        local_note.setAccessibleName("Aplicativo local, sem sincronização externa")
        sidebar_layout.addWidget(local_note)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(30, 24, 30, 24)
        content_layout.setSpacing(18)

        header = QHBoxLayout()
        heading_text = QVBoxLayout()
        heading_text.setSpacing(3)
        self.page_title = QLabel("Biblioteca")
        self.page_title.setObjectName("pageTitle")
        self.page_subtitle = QLabel("Sua coleção local")
        self.page_subtitle.setObjectName("subtitle")
        heading_text.addWidget(self.page_title)
        heading_text.addWidget(self.page_subtitle)
        header.addLayout(heading_text, 1)
        self.startup_status = QLabel("Preparando os dados locais…")
        self.startup_status.setObjectName("startupStatus")
        self.startup_status.setAccessibleName("Status da inicialização")
        self.startup_status.setWordWrap(True)
        header.addWidget(self.startup_status, 0)
        content_layout.addLayout(header)

        self.simulation_banner = SimulationBanner()
        content_layout.addWidget(self.simulation_banner)
        self.page_stack = QStackedWidget()
        self.page_stack.setObjectName("pageStack")
        self.library_view = LibraryView(self.operation_runner)
        self.add_manga_view = AddMangaView(self.operation_runner, catalog_query)
        self.downloads_view = DownloadsView(self.operation_runner)
        self.image_import_view = ImageImportView(self.operation_runner)
        self.conversion_view = ConversionView(self.operation_runner)
        self.manual_send_view = ManualSendView(self.operation_runner)
        self.settings_view = SettingsView(self.operation_runner)
        self.update_settings_view = UpdateSettingsView(self.operation_runner)
        self.add_manga_view.chapter_list.selection_changed.connect(
            self.conversion_view.set_selected_chapters
        )
        self.library_view.add_manga_requested.connect(lambda: self.set_current_page("add"))
        self.conversion_view.manual_send_requested.connect(self._open_manual_send)
        self._page_widgets: Mapping[str, QWidget] = {
            "library": self.library_view,
            "add": self.add_manga_view,
            "downloads": self.downloads_view,
            "conversion": self.conversion_view,
            "send": self.manual_send_view,
            "settings": self.settings_view,
            "images": self.image_import_view,
            "updates": self.update_settings_view,
        }
        for key, _, _, _ in self._PAGES:
            self.page_stack.addWidget(self._page_widgets[key])
        self.settings_view.theme_changed.connect(self._on_theme_selected)
        content_layout.addWidget(self.page_stack, 1)

        root_layout.addWidget(sidebar)
        root_layout.addWidget(content, 1)
        self.setCentralWidget(root)
        navigation_actions = tuple(
            lambda page=key: self.set_current_page(page) for key, _, _, _ in self._PAGES
        )
        self._navigation_shortcuts = bind_navigation_shortcuts(self, navigation_actions)
        self._apply_theme_stylesheet()
        self.set_current_page("library")

    @property
    def theme(self) -> ThemeMode:
        return self._theme

    def set_status(self, message: str) -> None:
        self.startup_status.setText(message)

    def set_current_page(self, page: str) -> None:
        index = next(
            (i for i, (key, _, _, _) in enumerate(self._PAGES) if key == page),
            None,
        )
        if index is None:
            return
        if page != "add" and self.page_stack.currentWidget() is self.add_manga_view:
            self.add_manga_view.cancel_query()
        key, _, title, subtitle = self._PAGES[index]
        self.page_stack.setCurrentIndex(index)
        self.page_title.setText(title)
        self.page_subtitle.setText(subtitle)
        self.navigation_buttons[key].setChecked(True)
        self.page_changed.emit(key)

    def _open_manual_send(self) -> None:
        self.set_current_page("send")
        self.manual_send_view.refresh()

    def set_theme(self, theme: ThemeMode, *, emit: bool = False) -> None:
        self._theme = theme
        self.settings_view.set_theme(theme, emit=False)
        self._apply_theme_stylesheet()
        if emit:
            self.theme_change_requested.emit(theme)

    def allow_close(self) -> None:
        self._allow_close = True

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt override
        self.update_settings_view.stop_scheduler()
        if self._allow_close:
            event.accept()
            return
        event.ignore()
        self.close_requested.emit()

    def _on_theme_selected(self, theme_value: str) -> None:
        theme: ThemeMode = "dark" if theme_value == "dark" else "light"
        if theme == self._theme:
            return
        self.set_theme(theme, emit=True)

    def _apply_theme_stylesheet(self) -> None:
        self.setStyleSheet(stylesheet_for(self._theme))
