from __future__ import absolute_import

from collections import defaultdict
from PyQt4 import QtGui, QtCore
from autopilot.introspection.dbus import (
    DBusIntrospectionObject,
    StateNotFoundError,
    )


class DbusConnectionDetails(object):
    """Encapsulate displaying details of and creating instances of
    DBusIntrospectionObject.

    """
    def __init__(self, name, service_str='', object_str=''):
        self.name = name
        self.service_str = service_str
        self.object_str = object_str
        # Should this perhaps be a property
        self.dbus_object = self.generate_dbus_object()

    def generate_dbus_object(self):
        if self.service_str == '' or self.object_str == '':
            return None
        else:
            return type(self.name,
                        (DBusIntrospectionObject,),
                        dict(DBUS_SERVICE=self.service_str,
                             DBUS_OBJECT=self.object_str))


class MainWindow(QtGui.QMainWindow):
    AP_DBUS_IFACE_STR = "com.canonical.Autopilot.Introspection"

    def __init__(self):
        super(MainWindow, self).__init__()
        self.selectable_interfaces = {}
        self.initUI()

    def initUI(self):
        header_titles = QtCore.QStringList(["Name", "Value"])

        self.splitter = QtGui.QSplitter(self)
        self.tree_view = QtGui.QTreeView(self.splitter)
        self.tree_view.clicked.connect(self.tree_item_clicked)

        self.table_view = QtGui.QTableWidget(self.splitter)
        self.table_view.setColumnCount(2)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setHorizontalHeaderLabels(header_titles)
        self.table_view.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)

        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 100)
        self.setCentralWidget(self.splitter)

        self.connection_list = QtGui.QComboBox()
        self.connection_list.activated.connect(self.conn_list_activated)

        self.toolbar = self.addToolBar('Connection')
        self.toolbar.addWidget(self.connection_list)

    def on_interface_found(self, conn, obj, iface):
        if iface == self.AP_DBUS_IFACE_STR:
            #print "Updating interface list: %s, %s, %s" % (conn, obj, iface)
            self.selectable_interfaces[conn] = (obj, conn)
            self.update_selectable_interfaces()

    def update_selectable_interfaces(self):
        selected_text = self.connection_list.currentText()
        self.connection_list.clear()
        self.connection_list.addItem("Please select a connection",
                                     QtCore.QVariant(None))
        for name, details in self.selectable_interfaces.iteritems():
            self.connection_list.addItem(name, QtCore.QVariant(details))

        prev_selected = self.connection_list.findText(selected_text,
                                                      QtCore.Qt.MatchExactly)
        if prev_selected == -1:
            prev_selected = 0
        self.connection_list.setCurrentIndex(prev_selected)

    def conn_list_activated(self, index):
        """itemData will return a tuple with (obj, iface) details pair."""
        dbus_details = self.connection_list.itemData(index).toPyObject()
        if dbus_details:
            dbus_obj = type("Unity",
                            (DBusIntrospectionObject,),
                            dict(DBUS_SERVICE=str(dbus_details[1]),
                                 DBUS_OBJECT=str(dbus_details[0])))
            name, state = dbus_obj.get_state_by_path('/')[0]
            dbus_obj_root = dbus_obj(state)
            self.tree_model = VisTreeModel(dbus_obj_root)
            self.tree_view.setModel(self.tree_model)

    def tree_item_clicked(self, model_index):
        object_details = model_index.internalPointer().dbus_object._DBusIntrospectionObject__state
        self.table_view.setSortingEnabled(False)
        self.table_view.clearContents()

        object_details = dict(filter(lambda i: i[0] != "Children",
                                     object_details.iteritems()))
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
        or isinstance(dbus_type, dbus.Int64)
        or isinstance(dbus_type, dbus.UInt64)):
        return repr(int(dbus_type))
    if isinstance(dbus_type, dbus.Double):
        return repr(float(dbus_type))
    if isinstance(dbus_type, dbus.Array):
        return ', '.join([dbus_string_rep(i) for i in dbus_type])
    else:
        return repr(dbus_type)


class TreeNode(object):
    """Used to represent the tree data structure that is the backend of the
    treeview.

    Lazy loads a nodes children instead of waiting to load and store a static
    snapshot of the apps whole state.

    """
    def __init__(self, parent=None, name='', dbus_object=None):
        self.parent = parent
        self.name = name
        self.dbus_object = dbus_object
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


class VisTreeModel(QtCore.QAbstractItemModel):
    def __init__(self, introspectable_obj):
        super(VisTreeModel, self).__init__()
        name = introspectable_obj.__class__.__name__
        self.tree_root = TreeNode(name=name, dbus_object=introspectable_obj)

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
