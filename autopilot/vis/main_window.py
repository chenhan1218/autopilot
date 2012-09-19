# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
from __future__ import absolute_import

import dbus
from PyQt4 import QtGui, QtCore

from autopilot.introspection.constants import AP_INTROSPECTION_IFACE
from autopilot.introspection.dbus import StateNotFoundError
from autopilot.introspection.qt import QtObjectProxyMixin
from autopilot.introspection import make_proxy_object_from_service_name

from autopilot.vis.objectproperties import TreeNodeDetailWidget
from autopilot.vis.resources import get_qt_icon


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.selectable_interfaces = {}
        self.initUI()
        self.readSettings()

    def readSettings(self):
        settings = QtCore.QSettings()
        self.restoreGeometry(settings.value("geometry").toByteArray());
        self.restoreState(settings.value("windowState").toByteArray());

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

        self.connection_list = QtGui.QComboBox()
        self.connection_list.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToContents)
        self.connection_list.activated.connect(self.conn_list_activated)

        self.toolbar = self.addToolBar('Connection')
        self.toolbar.setObjectName('Connection Toolbar')
        self.toolbar.addWidget(self.connection_list)

    def on_interface_found(self, conn, obj, iface):
        if iface == AP_INTROSPECTION_IFACE:
            self.statusBar().showMessage('Updating connection list')
            try:
                proxy_object = make_proxy_object_from_service_name(conn, obj)
                cls_name = proxy_object.__class__.__name__
                if not self.selectable_interfaces.has_key(cls_name):
                    self.selectable_interfaces[cls_name] = proxy_object
                    self.update_selectable_interfaces()
            except (dbus.DBusException, RuntimeError):
                pass
            self.statusBar().clearMessage()

    def update_selectable_interfaces(self):
        selected_text = self.connection_list.currentText()
        self.connection_list.clear()
        self.connection_list.addItem("Please select a connection",
                                     QtCore.QVariant(None))
        for name, proxy_obj in self.selectable_interfaces.iteritems():
            if isinstance(proxy_obj, QtObjectProxyMixin):
                self.connection_list.addItem(
                    get_qt_icon(),
                    name,
                    QtCore.QVariant(proxy_obj)
                    )
            else:
                self.connection_list.addItem(name, QtCore.QVariant(proxy_obj))

        prev_selected = self.connection_list.findText(selected_text,
                                                      QtCore.Qt.MatchExactly)
        if prev_selected == -1:
            prev_selected = 0
        self.connection_list.setCurrentIndex(prev_selected)

    def conn_list_activated(self, index):
        dbus_details = self.connection_list.itemData(index).toPyObject()
        if dbus_details:
            self.tree_model = VisTreeModel(dbus_details)
            self.tree_view.setModel(self.tree_model)
            self.tree_view.selectionModel().currentChanged.connect(self.tree_item_changed)

    def tree_item_changed(self, current, previous):
        proxy = current.internalPointer().dbus_object
        self.detail_widget.tree_node_changed(proxy)


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
        except IndexError:
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
