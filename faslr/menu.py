"""
Contains the menu bar of the main window i.e., the horizontal bar that has stuff like File, Edit, Tools, About, etc.
"""
from __future__ import annotations

from faslr.about import AboutDialog

from faslr.connection import ConnectionDialog

from faslr.constants import CONFIG_PATH

from faslr.project import ProjectDialog

from faslr.settings import SettingsDialog

from PyQt6.QtGui import (
    QAction,
    QKeySequence
)

from PyQt6.QtWidgets import (
    QMenu,
    QMenuBar
)

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from faslr.main import MainWindow


class MainMenuBar(QMenuBar):
    def __init__(
            self,
            parent: MainWindow = None
    ):
        super().__init__(parent)

        self.parent = parent

        self.connection_action = QAction("&Connection", self)
        self.connection_action.setShortcut(QKeySequence("Ctrl+Shift+c"))
        self.connection_action.setStatusTip("Edit database connection.")
        # noinspection PyUnresolvedReferences
        self.connection_action.triggered.connect(self.edit_connection)

        self.new_action = QAction("&New Project", self)
        self.new_action.setShortcut(QKeySequence("Ctrl+n"))
        self.new_action.setStatusTip("Create new project.")
        # noinspection PyUnresolvedReferences
        self.new_action.triggered.connect(self.new_project)

        self.import_action = QAction("&Import Project")
        self.import_action.setShortcut(QKeySequence("Ctrl+Shift+i"))
        self.import_action.setStatusTip("Import a project from another data source.")

        self.engine_action = QAction("&Select Engine")
        self.engine_action.setShortcut("Ctrl+shift+e")
        self.engine_action.setStatusTip("Select a reserving engine.")

        self.settings_action = QAction("&Settings")
        self.settings_action.setShortcut("Ctrl+Shift+t")
        self.settings_action.setStatusTip("Open settings dialog box.")
        # noinspection PyUnresolvedReferences
        self.settings_action.triggered.connect(self.display_settings)

        self.about_action = QAction("&About", self)
        self.about_action.setStatusTip("About")
        # noinspection PyUnresolvedReferences
        self.about_action.triggered.connect(self.display_about)

        file_menu = QMenu("&File", self)
        self.addMenu(file_menu)
        self.addMenu("&Edit")
        tools_menu = self.addMenu("&Tools")
        help_menu = self.addMenu("&Help")

        file_menu.addAction(self.connection_action)
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.import_action)
        file_menu.addAction(self.settings_action)

        tools_menu.addAction(self.engine_action)

        help_menu.addAction(self.about_action)

    def edit_connection(self) -> None:
        # function triggers the connection dialog box to connect to a database
        dlg = ConnectionDialog(self)
        dlg.exec()

    def display_about(self) -> None:
        # function to display about dialog box
        dlg = AboutDialog(self)
        dlg.exec()

    def new_project(self) -> None:
        # function to display new project dialog box
        dlg = ProjectDialog(self)
        dlg.exec()

    def display_settings(self) -> None:
        # launch settings window
        dlg = SettingsDialog(
            parent=self,
            config_path=CONFIG_PATH
        )
        dlg.show()

    def toggle_project_actions(self) -> None:
        # disable project-based menu items until connection is established

        if self.parent.connection_established:
            self.new_action.setEnabled(True)

        else:
            self.new_action.setEnabled(False)
