# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2012-2013 Canonical
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


from __future__ import absolute_import

import dbus
import logging
from PyQt4 import QtGui, QtCore
import six

from autopilot.introspection import (
    _get_dbus_address_object,
    _make_proxy_object_async
)
from autopilot.introspection.constants import AP_INTROSPECTION_IFACE
from autopilot.introspection.dbus import StateNotFoundError
from autopilot.introspection.qt import QtObjectProxyMixin
from autopilot.vis.objectproperties import TreeNodeDetailWidget
from autopilot.vis.resources import get_qt_icon

logger = logging.getLogger(__name__)


class MainWindow(QtGui.QMainWindow):
    def __init__(self, dbus_bus):
        super(MainWindow, self).__init__()
        self.selectable_interfaces = {}
        self.initUI()
        self.readSettings()
        self._dbus_bus = dbus_bus

    def readSettings(self):
        settings = QtCore.QSettings()
        if six.PY3:
            self.restoreGeometry(settings.value("geometry").data())
            self.restoreState(settings.value("windowState").data())
        else:
            self.restoreGeometry(settings.value("geometry").toByteArray())
            self.restoreState(settings.value("windowState").toByteArray())

    def closeEvent(self, event):
        settings = QtCore.QSettings()
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())

    def initUI(self):
        self.statusBar().showMessage('Waiting for first valid dbus connection')

        self.splitter = QtGui.QSplitter(self)
        self.tree_view = QtGui.QTreeView(self.splitter)
        self.detail_widget = TreeNodeDetailWidget(self.splitter)

        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 100)
        self.setCentralWidget(self.splitter)

        self.connection_list = ConnectionList()
        self.connection_list.currentIndexChanged.connect(
            self.conn_list_activated
        )

        self.toolbar = self.addToolBar('Connection')
        self.toolbar.setObjectName('Connection Toolbar')
        self.toolbar.addWidget(self.connection_list)

    def on_interface_found(self, conn, obj, iface):
        if iface == AP_INTROSPECTION_IFACE:
            self.statusBar().showMessage('Updating connection list')
            try:
                dbus_address_instance = _get_dbus_address_object(
                    str(conn), str(obj), self._dbus_bus)
                _make_proxy_object_async(
                    dbus_address_instance,
                    None,
                    self.on_proxy_object_built,
                    self.on_dbus_error
                )
            except (dbus.DBusException, RuntimeError) as e:
                logger.warning("Invalid introspection interface: %s" % str(e))

            if self.connection_list.count() == 0:
                self.statusBar().showMessage('No valid connections exist.')

    def on_proxy_object_built(self, proxy_object):
        cls_name = proxy_object.__class__.__name__
        if not cls_name in self.selectable_interfaces:
            self.selectable_interfaces[cls_name] = proxy_object
            self.update_selectable_interfaces()
        self.statusBar().clearMessage()

    def on_dbus_error(*args):
        print(args)

    def update_selectable_interfaces(self):
        selected_text = self.connection_list.currentText()
        self.connection_list.clear()
        self.connection_list.addItem("Please select a connection", None)
        for name, proxy_obj in self.selectable_interfaces.items():
            if isinstance(proxy_obj, QtObjectProxyMixin):
                self.connection_list.addItem(
                    get_qt_icon(),
                    name,
                    proxy_obj
                )
            else:
                self.connection_list.addItem(name, proxy_obj)

        prev_selected = self.connection_list.findText(selected_text,
                                                      QtCore.Qt.MatchExactly)
        if prev_selected == -1:
            prev_selected = 0
        self.connection_list.setCurrentIndex(prev_selected)

    def conn_list_activated(self, index):
        dbus_details = self.connection_list.itemData(index)
        if not six.PY3:
            dbus_details = dbus_details.toPyObject()
        if dbus_details:
            self.tree_model = VisTreeModel(dbus_details)
            self.tree_view.setModel(self.tree_model)
            self.tree_view.selectionModel().currentChanged.connect(
                self.tree_item_changed)

    def tree_item_changed(self, current, previous):
        proxy = current.internalPointer().dbus_object
        self.detail_widget.tree_node_changed(proxy)


class ConnectionList(QtGui.QComboBox):
    """Used to show a list of applications we can connect to."""

    def __init__(self):
        super(ConnectionList, self).__init__()
        self.setObjectName("ConnectionList")
        self.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToContents)

    @QtCore.pyqtSlot(str)
    def trySetSelectedItem(self, desired_text):
        index = self.findText(desired_text)
        if index != -1:
            self.setCurrentIndex(index)


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
        self._children = None

    @property
    def children(self):
        if self._children is None:
            self._children = []
            try:
                for child in self.dbus_object.get_children():
                    name = child.__class__.__name__
                    self._children.append(TreeNode(self, name, child))
            except StateNotFoundError:
                pass
        return self._children

    @property
    def num_children(self):
        """An optimisation that allows us to get the number of children without
        actually retrieving them all. This is useful since Qt needs to know if
        there are children (to draw the drop-down triangle thingie), but
        doesn't need to know about the details.

        """
        num_children = 0
        with self.dbus_object.no_automatic_refreshing():
            if hasattr(self.dbus_object, 'Children'):
                num_children = len(self.dbus_object.Children)
        return num_children


class VisTreeModel(QtCore.QAbstractItemModel):
    def __init__(self, introspectable_obj):
        super(VisTreeModel, self).__init__()
        name = introspectable_obj.__class__.__name__
        self.tree_root = TreeNode(name=name, dbus_object=introspectable_obj)

    def index(self, row, col, parent):
        if not self.hasIndex(row, col, parent):
            return QtCore.QModelIndex()

        # If there's no parent, return the root of our tree:
        if not parent.isValid():
            return self.createIndex(row, col, self.tree_root)
        else:
            parentItem = parent.internalPointer()

        try:
            childItem = parentItem.children[row]
            return self.createIndex(row, col, childItem)
        except IndexError:
            return QtCore.QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()

        childItem = index.internalPointer()
        if not childItem:
            return QtCore.QModelIndex()

        parentItem = childItem.parent

        if parentItem is None:
            return QtCore.QModelIndex()

        row = parentItem.children.index(childItem)
        return self.createIndex(row, 0, parentItem)

    def rowCount(self, parent):
        if not parent.isValid():
            return 1
        else:
            p_Item = parent.internalPointer()
        return p_Item.num_children

    def columnCount(self, parent):
        return 1

    def data(self, index, role):
        if not index.isValid():
            return None
        if role == QtCore.Qt.DisplayRole:
            return index.internalPointer().name

    def headerData(self, column, orientation, role):
        if (orientation == QtCore.Qt.Horizontal and
                role == QtCore.Qt.DisplayRole):
                return "Tree Node"

        return None
