import chainladder as cl
import sys

from connection import (
    connect_db,
    ConnectionDialog
)

from constants import (
    BUILD_VERSION
)

from project import (
    ProjectItem
)

from PyQt5.Qt import (
    QStandardItem,
    QStandardItemModel
)

from PyQt5.QtCore import (
    Qt,
)

from PyQt5.QtGui import (
    QColor,
    QKeySequence
)

from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QTableView,
    QTreeView,
    QHBoxLayout,
    QWidget
)

from schema import (
    CountryTable,
    LOBTable,
    ProjectTable,
    StateTable
)

from triangle_model import TriangleModel

from uuid import uuid4


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Flag to determine whether there is an active database connection. Most project-related functions
        # should be disabled unless a connection is established.
        self.connection_established = False
        self.db = None

        self.resize(500, 700)

        self.setWindowTitle("FASLR - Free Actuarial System for Loss Reserving")

        self.layout = QHBoxLayout()

        menu_bar = self.menuBar()

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

        self.about_action = QAction("&About", self)
        self.about_action.setStatusTip("About")
        # noinspection PyUnresolvedReferences
        self.about_action.triggered.connect(self.display_about)

        file_menu = QMenu("&File", self)
        menu_bar.addMenu(file_menu)
        menu_bar.addMenu("&Edit")
        tools_menu = menu_bar.addMenu("&Tools")
        help_menu = menu_bar.addMenu("&Help")

        file_menu.addAction(self.connection_action)
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.import_action)
        file_menu.addAction(self.settings_action)

        tools_menu.addAction(self.engine_action)

        help_menu.addAction(self.about_action)

        self.setStatusBar(QStatusBar(self))

        self.toggle_project_actions()

        # navigation pane for project hierarchy

        self.project_pane = QTreeView(self)
        self.project_pane.setHeaderHidden(False)

        # noinspection PyUnresolvedReferences
        self.project_pane.doubleClicked.connect(self.get_value)

        self.project_model = QStandardItemModel()
        self.project_model.setHorizontalHeaderLabels(["Project", "Project_UUID"])

        self.project_root = self.project_model.invisibleRootItem()

        self.project_pane.setModel(self.project_model)
        # self.project_pane.setColumnHidden(1, True)

        # self.analysis_pane = QWidget()
        # self.analysis_layout = QHBoxLayout()
        # self.analysis_pane.setLayout(self.analysis_layout)
        # self.analysis_pane.setFrameShape(QFrame.StyledPanel)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.project_pane)

        # triangle placeholder

        self.table = QTableView()

        triangle = cl.load_sample('raa')
        triangle = triangle.to_frame()

        self.tri_model = TriangleModel(triangle)
        self.table.setModel(self.tri_model)

        # self.analysis_layout.addWidget(self.table)
        splitter.addWidget(self.table)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([125, 150])

        self.layout.addWidget(splitter)
        self.container = QWidget()
        self.container.setLayout(self.layout)
        self.setCentralWidget(self.container)

    def get_value(self, val):
        print(val)
        print(val.data())
        print(val.row())
        print(val.column())
        ix_col_0 = self.project_model.sibling(val.row(), 1, val)
        print(ix_col_0.data())

    # disable project-based menu items until connection is established
    def toggle_project_actions(self):
        if self.connection_established:
            self.new_action.setEnabled(True)
        else:
            self.new_action.setEnabled(False)

    def edit_connection(self):

        dlg = ConnectionDialog(self)
        dlg.exec_()

    def display_about(self):

        dlg = AboutDialog(self)
        dlg.exec_()

    def new_project(self):

        dlg = ProjectDialog(self)
        dlg.exec_()


class ProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.country_edit = QLineEdit()
        self.state_edit = QLineEdit()
        self.lob_edit = QLineEdit()

        self.setWindowTitle("New Project")
        self.layout = QFormLayout()
        self.layout.addRow("Country:", self.country_edit)
        self.layout.addRow("State:", self.state_edit)
        self.layout.addRow("Line of Business:", self.lob_edit)

        button_layout = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

        self.button_box = QDialogButtonBox(button_layout)

        self.button_box = QDialogButtonBox(button_layout)
        # noinspection PyUnresolvedReferences
        self.button_box.accepted.connect(lambda main_window=parent: self.make_project(main_window))
        # noinspection PyUnresolvedReferences
        self.button_box.rejected.connect(self.reject)

        self.layout.addWidget(self.button_box)

        self.setLayout(self.layout)

    def make_project(self, main_window):

        # connect to the database
        print(main_window.db)
        session, connection = connect_db(db_path=main_window.db)

        country_text = self.country_edit.text()
        state_text = self.state_edit.text()
        lob_text = self.lob_edit.text()

        country = ProjectItem(
            country_text,
            set_bold=True
        )

        state = ProjectItem(
            state_text,
        )

        lob = ProjectItem(
            lob_text,
            text_color=QColor(155, 0, 0)
        )

        country_query = session.query(CountryTable).filter(CountryTable.country_name == country_text)

        new_project = ProjectTable()

        if country_query.first() is None:

            country_uuid = str(uuid4())
            state_uuid = str(uuid4())
            lob_uuid = str(uuid4())

            new_country = CountryTable(country_name=country_text, project_tree_uuid=country_uuid)
            new_state = StateTable(state_name=state_text, project_tree_uuid=state_uuid)
            new_lob = LOBTable(lob_type=lob_text, project_tree_uuid=lob_uuid)

            new_country.state = [new_state]
            new_lob.country = new_country
            new_lob.state = new_state

            new_project.lob = new_lob

            country.appendRow([state, QStandardItem(state_uuid)])
            state.appendRow([lob, QStandardItem(lob_uuid)])

            main_window.project_root.appendRow([country, QStandardItem(country_uuid)])

        else:
            existing_country = country_query.first()
            country_id = existing_country.country_id
            country_uuid = existing_country.project_tree_uuid
            state_query = session.query(StateTable).filter(
                StateTable.state_name == state_text
            ).filter(
                StateTable.country_id == country_id
            )

            if state_query.first() is None:
                state_uuid = str(uuid4())
                lob_uuid = str(uuid4())
                new_state = StateTable(state_name=state_text, project_tree_uuid=state_uuid)
                new_state.country = existing_country
                new_lob = LOBTable(lob_type=lob_text, project_tree_uuid=lob_uuid)
                new_lob.country = existing_country
                new_lob.state = new_state

                new_project.lob = new_lob

                country_tree_item = main_window.project_model.findItems(country_uuid, Qt.MatchExactly, 1)
                if country_tree_item:
                    ix = main_window.project_model.indexFromItem(country_tree_item[0])
                    ix_col_0 = main_window.project_model.sibling(ix.row(), 0, ix)
                    it_col_0 = main_window.project_model.itemFromIndex(ix_col_0)
                    it_col_0.appendRow([state, QStandardItem(state_uuid)])
                    state.appendRow([lob, QStandardItem(lob_uuid)])

            else:
                existing_state = state_query.first()
                state_uuid = existing_state.project_tree_uuid
                lob_uuid = str(uuid4())
                new_lob = LOBTable(lob_type=lob_text, project_tree_uuid=lob_uuid)
                new_lob.country = existing_country
                new_lob.state = existing_state

                new_project.lob = new_lob
                state_tree_item = main_window.project_model.findItems(state_uuid, Qt.MatchRecursive, 1)
                # state_tree_item = country_tree_item.findItems(state_uuid, Qt.MatchExactly, 1)
                if state_tree_item:
                    ix = main_window.project_model.indexFromItem(state_tree_item[0])
                    ix_col_0 = main_window.project_model.sibling(ix.row(), 0, ix)
                    it_col_0 = main_window.project_model.itemFromIndex(ix_col_0)
                    it_col_0.appendRow([lob, QStandardItem(lob_uuid)])

        session.add(new_project)

        session.commit()

        connection.close()

        # main_window.project_pane.expandAll()

        print("new project created")

        self.close()


class AboutDialog(QMessageBox):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("About")
        self.setText("FASLR v" + BUILD_VERSION + "\n\nGit Repository: https://github.com/genedan/FASLR")

        self.setStandardButtons(QMessageBox.Ok)
        self.setIcon(QMessageBox.Information)


app = QApplication(sys.argv)

window = MainWindow()

window.show()

app.exec_()
