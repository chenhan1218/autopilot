from __future__ import absolute_import

import sys
from PyQt4 import QtGui, QtCore
from autopilot.introspection.dbus import DBusIntrospectionObject

class MainWindow(QtGui.QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.initUI()

    def initUI(self):
        self.splitter = QtGui.QSplitter(self)
        self.treeview = QtGui.QTreeView(self.splitter)
        self.table_view = QtGui.QTableView(self.splitter)
        self.setCentralWidget(self.splitter)
        unity_object = type("Unity",
                            (DBusIntrospectionObject,),
                            dict(DBUS_SERVICE="com.canonical.Unity",
                                 DBUS_OBJECT="/com/canonical/Unity/Debug"))
        name, state = unity_object.get_state_by_path('/')[0]
        unity_root = unity_object(state)

        self.model = VisTreeModel(unity_root)
        self.treeview.setModel(self.model)

class VisTreeModel(QtCore.QAbstractItemModel):

    def __init__(self, introspectable_obj):
        super(VisTreeModel, self).__init__()
        self.introspectable_obj = introspectable_obj

    def index(self, row, col, parent):
        return self.createIndex(row, col, None)

    def parent(self, index):
        return QtCore.QModelIndex()

    def rowCount(self, index):
        return len(self.introspectable_obj.get_children())

    def columnCount(self, parent):
        return 1

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            row = index.row()
            return QtCore.QVariant(self.introspectable_obj.get_children()[row].__class__.__name__)
        return QtCore.QVariant()
