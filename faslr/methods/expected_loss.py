from __future__ import annotations

import pandas as pd

from faslr.base_table import (
    FAbstractTableModel,
    FTableView
)

from faslr.grid_header import GridTableView

from faslr.style.triangle import (
    RATIO_STYLE,
    VALUE_STYLE
)

from faslr.utilities import (
    auto_bi_olep,
    fetch_cdf,
    fetch_latest_diagonal,
    fetch_origin,
    fetch_ultimate
)

from PyQt6.QtCore import (
    QModelIndex,
    Qt
)

from PyQt6.QtWidgets import (
    QDialog,
    QTabWidget,
    QWidget,
    QVBoxLayout
)

from typing import (
    Any,
    List,
    TYPE_CHECKING
)

if TYPE_CHECKING:
    from chainladder import Chainladder

class ExpectedLossModel(FAbstractTableModel):
    def __init__(
            self,
            triangles: List[Chainladder]
    ):
        super().__init__()

        self.origin = fetch_origin(triangles[0])
        self.reported = fetch_latest_diagonal(triangles[0])
        self.paid = fetch_latest_diagonal(triangles[1])
        self.reported_cdf = fetch_cdf(triangles[0])
        self.paid_cdf = fetch_cdf(triangles[1])
        self.reported_ultimate = fetch_ultimate(triangles[0])
        self.paid_ultimate = fetch_ultimate(triangles[1])


        self._data = pd.DataFrame({
            'Accident Year': self.origin,
            'Reported Losses': self.reported,
            'Paid Losses': self.paid,
            'Reported CDF': self.reported_cdf,
            'Paid CDF': self.paid_cdf,
            'Reported Ultimate': self.reported_ultimate,
            'Paid Ultimate': self.paid_ultimate
        })

        self._data['Initial Selected'] = (self._data['Reported Ultimate'] + self._data['Paid Ultimate']) / 2

        self._data['On-Level Earned Premium'] = auto_bi_olep

    def data(self, index: QModelIndex, role: int = ...) -> Any:

        colname = self._data.columns[index.column()]

        if role == Qt.ItemDataRole.DisplayRole:

            value = self._data.iloc[index.row(), index.column()]

            if colname in [
                'Reported Losses',
                'Paid Losses',
                'Reported Ultimate',
                'Paid Ultimate',
                'Initial Selected',
                'On-Level Earned Premium'
            ]:

                display_value = VALUE_STYLE.format(value)

            elif colname in [
                    'Reported CDF',
                    'Paid CDF'
            ]:

                display_value = RATIO_STYLE.format(value)

            else:
                display_value = str(value)

            return display_value


class ExpectedLossView(GridTableView):
    def __int__(self):
        super().__init__()


class ExpectedLossWidget(QWidget):
    def __init__(
            self,
            triangles: List[Chainladder]
    ):
        super().__init__()

        self.setWindowTitle("Expected Loss Method")

        self.layout = QVBoxLayout()

        self.main_tabs = QTabWidget()

        self.indexation = QWidget()

        self.selection_tab = QWidget()

        self.main_tabs.addTab(self.indexation, "Indexation")
        self.main_tabs.addTab(self.selection_tab, "Model")

        self.selection_view = ExpectedLossView()
        self.selection_model = ExpectedLossModel(triangles=triangles)
        self.selection_view.setModel(self.selection_model)
        self.selection_view.setGridHeaderView(
            orientation=Qt.Orientation.Horizontal,
            levels=2
        )

        self.selection_view.hheader.setSpan(
            row=0,
            column=0,
            row_span_count=2,
            column_span_count=1
        )

        self.selection_view.hheader.setCellLabel(
            row=0,
            column=0,
            label="Accident\nYear"
        )

        ly_selection_tab = QVBoxLayout()
        ly_selection_tab.addWidget(self.selection_view)
        self.selection_tab.setLayout(ly_selection_tab)

        self.layout.addWidget(self.main_tabs)

        self.setLayout(self.layout)

