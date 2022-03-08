import chainladder as cl
import csv
import io
import numpy as np
import pandas as pd

from chainladder import (
    Triangle
)

from pandas import DataFrame

from PyQt5.QtCore import (
    QAbstractTableModel,
    QEvent,
    QModelIndex,
    Qt,
    QSize,
    QVariant
)

from PyQt5.QtGui import (
    QFont,
    QKeyEvent,
    QKeySequence
)

from PyQt5.QtWidgets import (
    QAbstractButton,
    QAction,
    QApplication,
    qApp,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QProxyStyle,
    QSpinBox,
    QStyle,
    QStylePainter,
    QStyleOptionHeader,
    QTableView,
    QVBoxLayout,
)

from style.triangle import (
    BLANK_TEXT,
    EXCL_FACTOR_COLOR,
    LOWER_DIAG_COLOR,
    MAIN_TRIANGLE_COLOR,
    RATIO_STYLE,
    VALUE_STYLE
)

from typing import Any


class FactorModel(QAbstractTableModel):

    def __init__(
            self,
            triangle: Triangle,
            value_type: str = "ratio"
    ):
        super(
            FactorModel,
            self
        ).__init__()

        self.triangle = triangle
        self.link_frame = triangle.link_ratio.to_frame()
        self.factor_frame = None

        ldf_blanks = [np.nan] * len(self.link_frame.columns)

        selected_data = {"Selected LDF": ldf_blanks}
        cdf_data = {"CDF to Ultimate": ldf_blanks}

        self.selected_row = pd.DataFrame.from_dict(
            selected_data,
            orient="index",
            columns=self.link_frame.columns
        )

        self.cdf_row = pd.DataFrame.from_dict(
            cdf_data,
            orient="index",
            columns=self.link_frame.columns
        )

        # self.cdf_row["To Ult"] = np.nan

        # Get number of rows in triangle portion of tab.
        self.n_triangle_rows = self.triangle.shape[2] - 1

        self.n_triangle_columns = self.triangle.shape[3] - 1

        # Extract data from the triangle that gets displayed in the tab.
        self._data = self.get_display_data()

        self.value_type = value_type

        # excl_frame is a dataframe that is the same size of the triangle which uses
        # boolean values to indicate which factors in the corresponding triangle should be excluded
        # it is first initialized to be all False, indicating no factors excluded initially
        self.excl_frame = self.link_frame.copy()
        self.excl_frame.loc[:] = False

        # Get the position of a blank row to be inserted between the end of the triangle
        # and before the development factors
        self.triangle_spacer_row = self.n_triangle_rows + 2
        self.ldf_row = self.triangle_spacer_row

        self.selected_spacer_row = self.triangle_spacer_row + 1

        self.selected_row_num = self.selected_spacer_row + 1
        self.cdf_row_num = self.selected_row_num + 1

    def data(
            self,
            index,
            role=None
    ):

        if role == Qt.DisplayRole:

            value = self._data.iloc[index.row(), index.column()]
            col = self._data.columns[index.column()]

            if col == "Ultimate Loss":
                if index.row() > self.n_triangle_rows:
                    display_value = BLANK_TEXT
                else:
                    display_value = VALUE_STYLE.format(value)
            else:
                if (index.row() == self.cdf_row_num) and self.selected_row.isnull().all().all():
                    display_value = BLANK_TEXT

                # Display blank when there are nans in the lower-right hand of the triangle.
                elif str(value) == "nan":

                    display_value = BLANK_TEXT
                else:
                    # "value" means stuff like losses and premiums, should have 2 decimal places.
                    if self.value_type == "value":

                        display_value = VALUE_STYLE.format(value)

                    # for "ratio", want to display 3 decimal places.
                    else:

                        display_value = RATIO_STYLE.format(value)

            display_value = str(display_value)

            self.setData(
                self.index(
                    index.row(),
                    index.column()
                ),
                QVariant(Qt.AlignRight),
                Qt.TextAlignmentRole
            )

            return display_value

        if role == Qt.TextAlignmentRole:
            return Qt.AlignRight

        if role == Qt.BackgroundRole:
            if self._data.columns[index.column()] != "Ultimate Loss":
                # Case when the index is on the lower diagonal
                if (index.column() >= self.n_triangle_rows - index.row()) and \
                        (index.row() < self.triangle_spacer_row):
                    return LOWER_DIAG_COLOR
                # Case when the index is on the triangle
                elif index.row() < self.triangle_spacer_row:
                    exclude = self.excl_frame.iloc[[index.row()], [index.column()]].squeeze()
                    # Change color if factor is excluded
                    if exclude:
                        return EXCL_FACTOR_COLOR
                    else:
                        return MAIN_TRIANGLE_COLOR
                elif (index.row() == self.selected_spacer_row) | (index.column() > self.n_triangle_columns - 1):
                    return LOWER_DIAG_COLOR
            else:
                if index.row() < self.triangle_spacer_row - 1:
                    return MAIN_TRIANGLE_COLOR
                else:
                    return LOWER_DIAG_COLOR

        # Strike out the link ratios if double-clicked, but not the averaged factors at the bottom
        if (role == Qt.FontRole) and \
                (self.value_type == "ratio") and \
                (index.row() < self.triangle_spacer_row - 2) and \
                (index.column() < self.n_triangle_columns):

            font = QFont()
            exclude = self.excl_frame.iloc[[index.row()], [index.column()]].squeeze()
            if exclude:
                font.setStrikeOut(True)
            else:
                font.setStrikeOut(False)
            return font

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if index.row() == self.selected_row_num:
            return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def rowCount(
            self,
            parent=None,
            *args,
            **kwargs
    ):

        return self._data.shape[0]

    def columnCount(
            self,
            parent=None,
            *args,
            **kwargs
    ):

        return self._data.shape[1]

    def headerData(
            self,
            p_int,
            qt_orientation,
            role=None
    ):

        # section is the index of the column/row.
        if role == Qt.DisplayRole:
            if qt_orientation == Qt.Horizontal:
                return str(self._data.columns[p_int])

            if qt_orientation == Qt.Vertical:
                return str(self._data.index[p_int])

    def toggle_exclude(self, index):
        """
        Sets values of the exclusion frame to True or False to indicate whether a link ratio should be excluded.
        """
        exclude = self.excl_frame.iloc[[index.row()], [index.column()]].squeeze()

        if exclude:
            self.excl_frame.iloc[[index.row()], [index.column()]] = False
        else:
            self.excl_frame.iloc[[index.row()], [index.column()]] = True

    def select_factor(self, index):

        self.selected_row.iloc[[0], [index.column()]] = self.factor_frame.iloc[[0], [index.column()]].copy()

        self.recalculate_factors(index=index)

    def select_ldf_row(self, index):

        self.selected_row.iloc[[0]] = self.factor_frame.iloc[[0]]
        self.recalculate_factors(index=index)

    def clear_selected_ldfs(self, index):

        self.selected_row.iloc[[0]] = np.nan
        self.recalculate_factors(index=index)

    def delete_ldf(self, index):
        self.selected_row.iloc[[0], [index.column()]] = np.nan
        self.recalculate_factors(index=index)

    def recalculate_factors(self, index):
        """
        Method to update the view and LDFs as the user strikes out link ratios.
        """
        drop_list = []
        for i in range(self.link_frame.shape[0]):
            for j in range(self.link_frame.shape[1]):

                exclude = self.excl_frame.iloc[[i], [j]].squeeze()

                if exclude:

                    row_drop = str(self.link_frame.iloc[i].name)
                    col_drop = int(str(self.link_frame.columns[j]).split('-')[0])

                    drop_list.append((row_drop, col_drop))

                else:

                    pass

        self._data = self.get_display_data(drop_list=drop_list)

        # noinspection PyUnresolvedReferences
        self.dataChanged.emit(
            index,
            index
        )
        # noinspection PyUnresolvedReferences
        self.layoutChanged.emit()

    def get_display_data(
            self,
            drop_list=None
    ) -> DataFrame:
        """
        Concatenates the link ratio triangle and LDFs below it to be displayed in the GUI.
        """
        ratios = self.link_frame.copy()

        development = cl.Development(drop=drop_list, average="volume")

        factors = development.fit(self.triangle)

        blank_data = {"": [np.nan] * len(ratios.columns)}

        blank_row = pd.DataFrame.from_dict(
            blank_data,
            orient="index",
            columns=ratios.columns
        )

        # noinspection PyUnresolvedReferences
        factor_frame = factors.ldf_.to_frame()
        factor_frame = factor_frame.rename(index={'(All)': 'Volume-Weighted LDF'})
        self.factor_frame = factor_frame

        # fit factors
        patterns = {}
        for i in range(ratios.shape[1]):
            col = int(str(self.link_frame.columns[i]).split('-')[0])
            patterns[col] = self.selected_row.iloc[[0], [i]].squeeze().copy()

        selected_dev = cl.DevelopmentConstant(
            patterns=patterns,
            style="ldf"
        ).fit_transform(self.triangle)

        selected_model = cl.Chainladder().fit(selected_dev)
        # noinspection PyUnresolvedReferences
        ultimate_frame = selected_model.ultimate_.to_frame()

        self.cdf_row.iloc[[0]] = selected_dev.cdf_.to_frame().iloc[[0]]

        # ratios["To Ult"] = np.nan
        ratios[""] = np.nan

        ratios = pd.concat([ratios, ultimate_frame], axis=1)
        ratios.columns = [*ratios.columns[:-1], "Ultimate Loss"]

        return pd.concat([
            ratios,
            blank_row,
            factor_frame,
            blank_row,
            self.selected_row,
            self.cdf_row
        ])

    def setData(self, index: QModelIndex, value: Any, role=None) -> bool:
        if value is not None and role == Qt.EditRole:

            try:
                value = float(value)
            except ValueError:
                value = np.nan
                # return False

            self.selected_row.iloc[0, index.column()] = value
            self.recalculate_factors(index=index)
            self.get_display_data()
            self.dataChanged.emit(index, index)
            # noinspection PyUnresolvedReferences
            self.layoutChanged.emit()
            return True


class FactorView(QTableView):
    def __init__(self):
        super().__init__()

        self.copy_action = QAction("&Copy", self)
        self.copy_action.setShortcut(QKeySequence("Ctrl+c"))
        self.copy_action.setStatusTip("Copy selection to clipboard.")
        # noinspection PyUnresolvedReferences
        self.copy_action.triggered.connect(self.copy_selection)

        self.delete_action = QAction("&Delete Selected LDF(s)", self)
        self.delete_action.setShortcut(QKeySequence("Del"))
        self.delete_action.setStatusTip("Delete the selected LDF(s).")
        self.delete_action.triggered.connect(self.delete_selection)

        self.installEventFilter(self)

        # self.delete_action = QAction("&Delete", self)
        # self.delete_action.setShortcut(QKeySequence("Del"))
        # self.delete_action.triggered.connect(self.delete_selection)

        btn = self.findChild(QAbstractButton)
        btn.installEventFilter(self)
        btn_label = QLabel("AY")
        btn_label.setAlignment(Qt.AlignCenter)
        btn_layout = QVBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addWidget(btn_label)
        btn.setLayout(btn_layout)
        opt = QStyleOptionHeader()

        h_headers = self.horizontalHeader()
        v_headers = self.verticalHeader()

        h_headers.setContextMenuPolicy(Qt.CustomContextMenu)
        v_headers.setContextMenuPolicy(Qt.CustomContextMenu)

        h_headers.customContextMenuRequested.connect(
            lambda *args: self.custom_menu_event(*args, header_type="horizontal"))
        v_headers.customContextMenuRequested.connect(
            lambda *args: self.custom_menu_event(*args, header_type="vertical"))

        # Set the styling for the table corner so that it matches the rest of the headers.
        self.setStyleSheet(
            """
            QTableCornerButton::section{
                border-width: 1px; 
                border-style: solid; 
                border-color:none darkgrey darkgrey none;
            }
            """
        )

        s = QSize(btn.style().sizeFromContents(
            QStyle.CT_HeaderSection,
            opt,
            QSize(),
            btn
        ).expandedTo(QApplication.globalStrut()))

        if s.isValid():
            self.verticalHeader().setMinimumWidth(s.width())

        self.verticalHeader().setDefaultAlignment(Qt.AlignCenter)

        # noinspection PyUnresolvedReferences
        self.verticalHeader().sectionDoubleClicked.connect(self.vertical_header_double_click)

        # noinspection PyUnresolvedReferences
        self.doubleClicked.connect(self.process_double_click)

        self.setTabKeyNavigation(True)

    def keyPressEvent(self, e: QKeyEvent) -> None:

        if e.key() == Qt.Key_Delete:
            self.delete_selection()
        else:
            super().keyPressEvent(e)

    def vertical_header_double_click(self):
        selection = self.selectedIndexes()

        index = selection[0]
        row_num = index.row()

        if row_num == self.model().triangle_spacer_row:
            self.model().select_ldf_row(index=index)
        elif row_num == self.model().selected_row_num:
            self.model().clear_selected_ldfs(index=index)

    def process_double_click(self):
        """
        Respond to when the user double-clicks on the table. Route methods depends on where in the table the user
        clicks.
        """

        selection = self.selectedIndexes()

        for index in selection:
            # Case when user double-clicks on the link ratios in the triangle, toggle exclude
            if index.row() < index.model().triangle_spacer_row - 2 and \
                    index.column() <= index.model().n_triangle_columns:
                index.model().toggle_exclude(index=index)
                index.model().recalculate_factors(index=index)
            # Case when the user clicks on an LDF average, select it.
            elif (index.model().selected_spacer_row > index.row() > index.model().triangle_spacer_row - 1) and \
                    (index.column() < index.model().n_triangle_columns):
                index.model().select_factor(index=index)
            # elif index.row() == index.model().selected_row_num and index.column() < index.model().n_triangle_columns:
            #     index.model().clear_selected_ldf(index=index)

    def exclude_ratio(self):
        selection = self.selectedIndexes()

        for index in selection:
            index.model().toggle_exclude(index=index)
            index.model().recalculate_factors(index=index)

    def eventFilter(self, obj, event):
        if event.type() != QEvent.Paint or not isinstance(
                obj, QAbstractButton):
            return False

        # Paint by hand (borrowed from QTableCornerButton)
        opt = QStyleOptionHeader()
        opt.initFrom(obj)
        style_state = QStyle.State_None
        if obj.isEnabled():
            style_state |= QStyle.State_Enabled
        if obj.isActiveWindow():
            style_state |= QStyle.State_Active
        if obj.isDown():
            style_state |= QStyle.State_Sunken
        opt.state = style_state
        opt.rect = obj.rect()
        # This line is the only difference to QTableCornerButton
        opt.text = obj.text()
        opt.position = QStyleOptionHeader.OnlyOneSection
        painter = QStylePainter(obj)
        painter.drawControl(QStyle.CE_Header, opt)

        return True

    def custom_menu_event(
            self,
            pos,
            event=None,
            header_type=None
    ):
        """
        When right-clicking a cell, activate context menu.

        :param: event
        :return:
        """

        rows = [index.row() for index in self.selectedIndexes()]

        menu = QMenu()
        menu.addAction(self.copy_action)

        # only add the delete option if the selection contains the row of selected LDFs
        if self.model().selected_row_num in rows:
            menu.addAction(self.delete_action)
        else:
            pass

        if event is None:
            if header_type == "horizontal":
                position = self.horizontalHeader().mapToGlobal(pos)
            elif header_type == "vertical":
                position = self.verticalHeader().mapToGlobal(pos)
            else:
                raise ValueError("Invalid header type specified.")
        else:
            position = event.globalPos()

        menu.exec(position)

    def contextMenuEvent(self, event):

        self.custom_menu_event(pos=None, event=event)

    def copy_selection(self):
        """Method to copy selected values to clipboard, so they can be pasted elsewhere, like Excel."""
        selection = self.selectedIndexes()
        if selection:
            rows = sorted(index.row() for index in selection)
            columns = sorted(index.column() for index in selection)
            rowcount = rows[-1] - rows[0] + 1
            colcount = columns[-1] - columns[0] + 1
            table = [[''] * colcount for _ in range(rowcount)]
            for index in selection:
                row = index.row() - rows[0]
                column = index.column() - columns[0]
                table[row][column] = index.data()
            stream = io.StringIO()
            csv.writer(stream, delimiter='\t').writerows(table)
            qApp.clipboard().setText(stream.getvalue())
        return

    def delete_selection(self):
        selection = self.selectedIndexes()

        for index in selection:
            if index.row() == self.model().selected_row_num and index.column() < self.model().selected_row.shape[1]:
                self.model().delete_ldf(index=index)
            else:
                pass


class LDFAverageModel(QAbstractTableModel):
    def __init__(self, data, checkable_columns=None):
        super(LDFAverageModel, self).__init__()

        self._data = data
        if checkable_columns is None:
            checkable_columns = []
        elif isinstance(checkable_columns, int):
            checkable_columns = [checkable_columns]
        self.checkable_columns = set(checkable_columns)

    def set_column_checkable(self, column, checkable=True):
        if checkable:
            self.checkable_columns.add(column)
        else:
            self.checkable_columns.discard(column)
        self.dataChanged.emit(
            self.index(0, column), self.index(self.rowCount() - 1, column)
        )

    def data(
            self,
            index,
            role=None
    ):
        value = self._data.iloc[index.row(), index.column()]

        if role == Qt.CheckStateRole and index.column() in self.checkable_columns:
            return Qt.Checked if value else Qt.Unchecked
        elif index.column() not in self.checkable_columns and role in (Qt.DisplayRole, Qt.EditRole):
            return value
        else:
            return None

    def flags(self, index):
        flags = Qt.ItemIsEnabled
        if index.column() in self.checkable_columns:
            flags |= Qt.ItemIsUserCheckable
        return flags

    def headerData(
            self,
            p_int,
            qt_orientation,
            role=None
    ):

        # section is the index of the column/row.
        if role == Qt.DisplayRole:
            if qt_orientation == Qt.Horizontal:
                return str(self._data.columns[p_int])

            if qt_orientation == Qt.Vertical:
                return str(self._data.index[p_int])

    def rowCount(
            self,
            parent=None,
            *args,
            **kwargs
    ):

        return self._data.shape[0]

    def columnCount(
            self,
            parent=None,
            *args,
            **kwargs
    ):

        return self._data.shape[1]

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.CheckStateRole and index.column() in self.checkable_columns:
            self._data.iloc[index.row(), index.column()] = bool(value)
            self.dataChanged.emit(index, index)
            return True

        if value is not None and role == Qt.EditRole:
            self._data.iloc[index.row(), index.column()] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def add_average(self, avg_type: str, years: int, label: str):
        """
        Adds a custom LDF average type to the list of current averages.
        """

        data = {"": [None, label, avg_type, str(years)]}

        df = pd.DataFrame.from_dict(
            data,
            orient="index",
            columns=self._data.columns
        )

        index = QModelIndex()

        self._data = pd.concat([self._data, df])
        self.dataChanged.emit(index, index)
        # noinspection PyUnresolvedReferences
        self.layoutChanged.emit()

        print(self._data.head())


class LDFAverageView(QTableView):
    def __init__(self):
        super().__init__()

        self.verticalHeader().hide()


class LDFAverageBox(QDialog):
    """
    Contains the view which houses a list of LDF averages that the user can choose to display in the factor view.
    """

    def __init__(self):
        super().__init__()

        data = {"blah 1": [None, "3-year volume-weighted", "volume-weighted", "3"],
                "blah 2": [None, "5-year volume-weighted", "volume-weighted", "5"],
                "blah 3": [None, "5-year volume-weighted", "volume-weighted", "5"]
        }

        self.data = pd.DataFrame.from_dict(
            data,
            orient="index",
            columns=["Selected", "Label", "Type", "Number of Years"]
        )

        self.layout = QVBoxLayout()
        self.model = LDFAverageModel(self.data, checkable_columns=0)
        self.view = LDFAverageView()
        self.view.setModel(self.model)
        self.layout.addWidget(self.view)

        self.view.resizeColumnsToContents()

        self.button_box = QDialogButtonBox()

        self.button_box.addButton("Add Average", QDialogButtonBox.ActionRole)
        self.button_box.addButton(QDialogButtonBox.Ok)

        self.button_box.clicked.connect(self.add_ldf_average)
        self.button_box.accepted.connect(self.accept_changes)

        self.layout.addWidget(self.button_box)

        self.setLayout(self.layout)

        self.set_dimensions()

    def set_dimensions(self):
        """
        Automatically size the dialog box.
        """

        width = self.view.horizontalHeader().length() + \
            self.view.verticalHeader().width() + \
            self.layout.getContentsMargins()[0] * 3

        height = self.view.verticalHeader().length() + self.view.horizontalHeader().height() + \
            self.layout.getContentsMargins()[0] * 5

        print(self.layout.sizeHint())

        self.resize(width, height)
        # self.resize(self.layout.sizeHint())
        return width, height

    def add_ldf_average(self, btn):

        if btn.text() == "&OK":
            return
        else:
            ldf_dialog = AddLDFDialog(parent=self)
            ldf_dialog.exec_()

    def accept_changes(self):
        self.close()


class AddLDFDialog(QDialog):
    """
    Dialog box that pops up to allow the user to enter a custom LDF average type. Can select type of average,
    number of most recent years calculated, and a label to identify it.
    """
    def __init__(self, parent=None):
        super().__init__()

        self.parent = parent

        self.layout = QFormLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(['Geometric', 'Medial', 'Straight', 'Volume'])
        self.year_spin = QSpinBox()
        self.year_spin.setMinimum(1)
        self.year_spin.setValue(1)
        self.avg_label = QLineEdit()
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        self.layout.addRow("Type: ", self.type_combo)
        self.layout.addRow("Years: ", self.year_spin)
        self.layout.addRow("Label: ", self.avg_label)
        self.layout.addWidget(button_box)
        self.setLayout(self.layout)

        button_box.rejected.connect(self.cancel_close)
        button_box.accepted.connect(self.add_average)

    def cancel_close(self):
        self.close()

    def add_average(self):
        label = self.avg_label.text()
        avg_type = self.type_combo.currentText()
        years = self.year_spin.value()

        self.parent.model.add_average(
            label=label,
            avg_type=avg_type,
            years=years
        )

        self.parent.set_dimensions()
        self.close()


class CheckBoxStyle(QProxyStyle):
    """
    Proxy style is used to center the checkboxes in the LDF Average dialog box.
    """

    def subElementRect(self, element, opt, widget=None):
        if element == self.SE_ItemViewItemCheckIndicator and not opt.text:
            rect = super().subElementRect(element, opt, widget)
            rect.moveCenter(opt.rect.center())
            return rect
        return super().subElementRect(element, opt, widget)
