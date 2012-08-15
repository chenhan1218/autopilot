from __future__ import absolute_import

import sys
from PyQt4 import QtGui, QtCore
from autopilot.introspection.dbus import (
    DBusIntrospectionObject,
    StateNotFoundError,
    )


class MainWindow(QtGui.QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.initUI()

    def initUI(self):
        self.splitter = QtGui.QSplitter(self)
        self.treeview = QtGui.QTreeView(self.splitter)
        self.table_view = QtGui.QTableWidget(self.splitter)
        self.table_view.setColumnCount(2)
        self.table_view.setAlternatingRowColors(True)
        header_titles = QtCore.QStringList(["Name", "Value"])
        self.table_view.setHorizontalHeaderLabels(header_titles)
        self.table_view.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 100)
        self.setCentralWidget(self.splitter)
        unity_object = type("Unity",
                            (DBusIntrospectionObject,),
                            dict(DBUS_SERVICE="com.canonical.Unity",
                                 DBUS_OBJECT="/com/canonical/Unity/Debug"))
        name, state = unity_object.get_state_by_path('/')[0]
        unity_root = unity_object(state)

        self.tree_model = VisTreeModel(unity_root)
        self.treeview.setModel(self.tree_model)
        self.treeview.clicked.connect(self.tree_item_clicked)

    def tree_item_clicked(self, model_index):
        object_details = model_index.internalPointer().dbus_object._DBusIntrospectionObject__state
        self.table_view.setSortingEnabled(False)
        self.table_view.clearContents()

        object_details = dict(filter(lambda i: i[0] != "Children", object_details.iteritems()))
        self.table_view.setRowCount(len(object_details))
        for i, key in enumerate(object_details):
            if key == "Children":
                continue
            if key == "id":
                details_string = str(model_index.internalPointer().dbus_object.id)
            else:
                details_string = dbus_string_rep(object_details[key])
            item_name = QtGui.QTableWidgetItem(key)
            item_details = QtGui.QTableWidgetItem(details_string)
            self.table_view.setItem(i, 0, item_name)
            self.table_view.setItem(i, 1, item_details)
        self.table_view.setSortingEnabled(True)
        self.table_view.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.table_view.resizeColumnsToContents()


def dbus_string_rep(dbus_type):
    """Get a string representation of various dbus types."""
    import dbus
    if isinstance(dbus_type, dbus.Boolean):
        return repr(bool(dbus_type))
    if isinstance(dbus_type, dbus.String):
        return dbus_type.encode('ascii', errors='ignore')
    if (isinstance(dbus_type, dbus.Int16)
        or isinstance(dbus_type, dbus.UInt16)
        or isinstance(dbus_type, dbus.Int32)
        or isinstance(dbus_type, dbus.UInt32)
        or isinstance(dbus_type,dbus.Int64)
        or isinstance(dbus_type, dbus.UInt64)):
        return repr(int(dbus_type))
    if isinstance(dbus_type, dbus.Double):
        return repr(float(dbus_type))
    if isinstance(dbus_type, dbus.Array):
        return ', '.join([dbus_string_rep(i) for i in dbus_type])
    else:
        return repr(dbus_type)

class TreeNode(object):
    def __init__(self, parent=None, name='', dbus_object=None):
        self.parent=parent
        self.name=name
        self.dbus_object=dbus_object
        self._children = []

    @property
    def children(self):
        if not self._children:
            try:
                for child in self.dbus_object.get_children():
                    name = child.__class__.__name__
                    self._children.append(TreeNode(self, name, child))
            except StateNotFoundError:
                pass
        return self._children


def generate_tree(root_object):
    name = root_object.__class__.__name__
    node = TreeNode(name=name, dbus_object=root_object)
    return node

class VisTreeModel(QtCore.QAbstractItemModel):

    def __init__(self, introspectable_obj):
        super(VisTreeModel, self).__init__()
        self.introspectable_obj = introspectable_obj
        print "Generating tree"
        self.tree_root = generate_tree(self.introspectable_obj)
        print "Done"

    def index(self, row, col, parent):
        if not self.hasIndex(row, col, parent):
            return QtCore.QModelIndex()

        if not parent.isValid():
            parentItem = self.tree_root
        else:
            parentItem = parent.internalPointer()

        try:
            childItem = parentItem.children[row]
            return self.createIndex(row, col, childItem)
        except:
            return QtCore.QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()

        childItem = index.internalPointer()
        if not childItem:
            return QtCore.QModelIndex()

        parentItem = childItem.parent

        if parentItem == self.tree_root:
            return QtCore.QModelIndex()

        row = parentItem.children.index(childItem)
        return self.createIndex(row, 0, parentItem)

    def rowCount(self, parent):
        if not parent.isValid():
            p_Item = self.tree_root
        else:
            p_Item = parent.internalPointer()
        return len(p_Item.children)

    def columnCount(self, parent):
        return 1

    def data(self, index, role):
        if not index.isValid():
            return QtCore.QVariant()
        if role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant(index.internalPointer().name)

    def headerData(self, column, orientation, role):
        if (orientation == QtCore.Qt.Horizontal and
            role == QtCore.Qt.DisplayRole):
            try:
                return QtCore.QVariant("Tree Node")
            except IndexError:
                pass

        return QtCore.QVariant()
